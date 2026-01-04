"""
Главное окно преподавателя
"""

import sys
import logging
import base64
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QAction, QStatusBar, QLabel, QPushButton,
    QGridLayout, QScrollArea, QFrame, QMessageBox, QMenu, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont
from typing import Dict
from src.common.models import Student
from src.common.constants import StudentStatus, MessageType
from src.common.utils import get_app_dir
from src.network.server import TeacherServer
from src.streaming.screen_capture import ScreenCapture
from src.control.classroom_control import ClassroomControl
from src.audio.voice_stream import VoiceBroadcaster, VoiceReceiver, AUDIO_AVAILABLE
from src.streaming.webcam_capture import WebcamBroadcaster, CV2_AVAILABLE
from src.teacher.whiteboard_window import TeacherWhiteboardWindow
from src.control.web_control import WebAccessController
from src.files import FileSender
from src.control.activity_monitor import ActivityTracker
from src.recording import LessonRecorder, RecordingConfig


logger = logging.getLogger(__name__)


class StudentCard(QFrame):
    """Виджет карточки студента"""
    
    clicked = pyqtSignal(str)  # student_id
    
    def __init__(self, student: Student, parent=None):
        super().__init__(parent)
        self.student = student
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setFixedSize(150, 120)
        self.setToolTip(f"IP: {self.student.ip_address}")
        
        layout = QVBoxLayout()
        
        # Иконка статуса
        self.status_label = QLabel("📺" if self.student.status == StudentStatus.ONLINE else "⚫")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        # Имя студента
        self.name_label = QLabel(self.student.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        # Статус
        self.status_text = QLabel(self._get_status_text())
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.status_text)
        
        self.setLayout(layout)
        self._update_style()
    
    def _get_status_text(self) -> str:
        """Получить текст статуса"""
        status_map = {
            StudentStatus.ONLINE: "Онлайн",
            StudentStatus.OFFLINE: "Оффлайн",
            StudentStatus.BUSY: "Занят",
            StudentStatus.WATCHING_VIDEO: "Смотрит видео",
            StudentStatus.TAKING_EXAM: "Тест",
            StudentStatus.SCREEN_LOCKED: "Заблокирован",
            StudentStatus.HAND_RAISED: "Поднял руку"
        }
        return status_map.get(self.student.status, "Неизвестно")
    
    def _update_style(self):
        """Обновить стиль карточки"""
        if self.student.status == StudentStatus.OFFLINE:
            self.setStyleSheet("StudentCard { background-color: #f0f0f0; }")
        elif self.student.status == StudentStatus.ONLINE:
            self.setStyleSheet("StudentCard { background-color: #e0ffe0; }")
        elif self.student.status == StudentStatus.SCREEN_LOCKED:
            self.setStyleSheet("StudentCard { background-color: #ffe0e0; }")
        else:
            self.setStyleSheet("StudentCard { background-color: #e0f0ff; }")
    
    def update_student(self, student: Student):
        """Обновить данные студента"""
        self.student = student
        self.name_label.setText(student.name)
        self.status_text.setText(self._get_status_text())
        self.status_label.setText("📺" if student.status == StudentStatus.ONLINE else "⚫")
        self._update_style()
    
    def mousePressEvent(self, event):
        """Обработка клика"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.student.id)


class TeacherMainWindow(QMainWindow):
    """Главное окно преподавателя"""
    
    def __init__(self, teacher_name: str, channel: int = 1):
        super().__init__()
        self.teacher_name = teacher_name
        self.channel = channel
        
        # Сервер
        self.server: TeacherServer = None
        self.classroom_control: ClassroomControl = None

        # Трансляция экрана
        self.screen_capture: ScreenCapture = None
        self.streaming = False
        
        # Голосовая связь (преподаватель → студенты)
        self.voice_broadcaster: VoiceBroadcaster = None
        self.voice_active = False
        
        # Голосовая связь (студент → преподаватель)
        self.student_voice_receiver: VoiceReceiver = None
        
        # Веб-камера
        self.webcam_broadcaster: WebcamBroadcaster = None
        self.webcam_active = False
        
        # Интерактивная доска
        self.whiteboard_window: TeacherWhiteboardWindow = None
        
        # Веб-контроль
        self.web_controller = WebAccessController()
        
        # Передача файлов
        self.file_sender = FileSender()
        self._setup_file_sender()
        
        # Трекер активности студентов
        self.activity_tracker = ActivityTracker()
        
        # Запись урока
        self.lesson_recorder = LessonRecorder(RecordingConfig(
            record_screen=True,
            record_audio=True,
            record_webcam=False,
            record_whiteboard=True,
            record_chat=True,
            record_events=True
        ))
        self.recording_active = False
        
        # UI элементы
        self.student_cards: Dict[str, StudentCard] = {}
        self.selected_student_id: str = None
        
        self._init_ui()
        self._init_server()
        self._apply_style()
        
        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)  # Каждую секунду
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle(f"Alfarid - Преподаватель: {self.teacher_name}")
        self.setMinimumSize(1024, 768)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель инструментов
        self._create_toolbar()
        
        # Основное содержимое
        content_layout = QHBoxLayout()
        
        # Левая панель - план класса
        self._create_classroom_panel(content_layout)
        
        # Правая панель - информация и управление
        self._create_info_panel(content_layout)
        
        main_layout.addLayout(content_layout)
        
        # Статусная строка
        self._create_statusbar()

    def _apply_style(self):
        """Загрузить QSS тему"""
        try:
            qss_path = Path(get_app_dir()) / "resources" / "styles.qss"
            if qss_path.exists():
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            logger.error(f"Не удалось применить стиль: {e}")
    
    def _create_toolbar(self):
        """Создать панель инструментов"""
        toolbar = QToolBar("Основная панель")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Управление
        control_menu = QMenu("Управление", self)
        control_action = QAction("⊞ Управление", self)
        control_action.setMenu(control_menu)
        toolbar.addAction(control_action)
        
        control_menu.addAction("📊 План класса")
        control_menu.addAction("👥 Список студентов")
        control_menu.addAction("🔄 Обновить")
        
        control_menu.addSeparator()
        
        # Блокировка
        lock_screen_action = control_menu.addAction("🔒 Заблокировать экраны")
        lock_screen_action.triggered.connect(self._lock_all_screens)
        
        unlock_screen_action = control_menu.addAction("🔓 Разблокировать экраны")
        unlock_screen_action.triggered.connect(self._unlock_all_screens)
        
        control_menu.addSeparator()
        
        lock_input_action = control_menu.addAction("⌨️ Заблокировать ввод")
        lock_input_action.triggered.connect(self._lock_all_input)
        
        unlock_input_action = control_menu.addAction("⌨️ Разблокировать ввод")
        unlock_input_action.triggered.connect(self._unlock_all_input)
        
        control_menu.addSeparator()
        
        # Веб-контроль
        web_menu = control_menu.addMenu("🌐 Веб-доступ")
        
        web_full_action = web_menu.addAction("✅ Полный доступ")
        web_full_action.triggered.connect(lambda: self._set_web_access("full"))
        
        web_edu_action = web_menu.addAction("📚 Только образовательные")
        web_edu_action.triggered.connect(lambda: self._set_web_access("educational"))
        
        web_block_social_action = web_menu.addAction("🚫 Блокировать соц.сети")
        web_block_social_action.triggered.connect(lambda: self._set_web_access("block_social"))
        
        web_no_access_action = web_menu.addAction("❌ Заблокировать всё")
        web_no_access_action.triggered.connect(lambda: self._set_web_access("no_access"))
        
        control_menu.addSeparator()
        
        # Мониторинг
        screenshot_action = control_menu.addAction("📷 Скриншот всех студентов")
        screenshot_action.triggered.connect(self._request_all_screenshots)
        
        activity_action = control_menu.addAction("📊 Отчёт активности")
        activity_action.triggered.connect(self._show_activity_report)
        
        # Трансляция
        broadcast_action = QAction("📺 Трансляция экрана", self)
        broadcast_action.triggered.connect(self._start_screen_broadcast)
        toolbar.addAction(broadcast_action)
        
        # Голосовая связь
        self.voice_action = QAction("🎤 Говорить", self)
        self.voice_action.setCheckable(True)
        self.voice_action.triggered.connect(self._toggle_voice)
        self.voice_action.setEnabled(AUDIO_AVAILABLE)
        if not AUDIO_AVAILABLE:
            self.voice_action.setToolTip("sounddevice не установлен")
        toolbar.addAction(self.voice_action)
        
        # Веб-камера
        self.webcam_action = QAction("📹 Камера", self)
        self.webcam_action.setCheckable(True)
        self.webcam_action.triggered.connect(self._toggle_webcam)
        self.webcam_action.setEnabled(CV2_AVAILABLE)
        if not CV2_AVAILABLE:
            self.webcam_action.setToolTip("OpenCV не установлен")
        toolbar.addAction(self.webcam_action)
        
        # Магнитофон
        audio_action = QAction("🎙️ Магнитофон", self)
        toolbar.addAction(audio_action)
        
        # Запись урока
        self.record_action = QAction("🔴 Запись", self)
        self.record_action.setCheckable(True)
        self.record_action.triggered.connect(self._toggle_recording)
        toolbar.addAction(self.record_action)
        
        # Интерактивная доска
        whiteboard_action = QAction("📝 Доска", self)
        whiteboard_action.triggered.connect(self._open_whiteboard)
        toolbar.addAction(whiteboard_action)
        
        # Экзамен
        exam_action = QAction("📝 Экзамен", self)
        exam_action.triggered.connect(self._start_quick_exam)
        toolbar.addAction(exam_action)
        
        # Группы
        group_action = QAction("🗣️ Группы", self)
        group_action.triggered.connect(self._create_groups_quick)
        toolbar.addAction(group_action)
        
        # Файлы
        files_action = QAction("📁 Файлы", self)
        files_action.triggered.connect(self._send_file_to_students)
        toolbar.addAction(files_action)
        
        toolbar.addSeparator()
        
        # Опрос
        poll_action = QAction("📊 Опрос", self)
        poll_action.triggered.connect(self._start_quick_poll)
        toolbar.addAction(poll_action)
        
        # Файлы
        files_action = QAction("📁 Файлы", self)
        toolbar.addAction(files_action)
        
        # Наблюдение
        monitor_action = QAction("👁️ Наблюдение", self)
        toolbar.addAction(monitor_action)
        
        # Отчеты
        reports_action = QAction("📋 Отчеты", self)
        toolbar.addAction(reports_action)
        
        # Настройки
        settings_action = QAction("⚙️ Настройки", self)
        toolbar.addAction(settings_action)
    
    def _create_classroom_panel(self, parent_layout):
        """Создать панель плана класса"""
        classroom_widget = QWidget()
        classroom_layout = QVBoxLayout(classroom_widget)
        
        # Заголовок
        title = QLabel("ПЛАН КЛАССА")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        classroom_layout.addWidget(title)
        
        # Счетчик студентов
        self.student_count_label = QLabel("0 студентов")
        self.student_count_label.setAlignment(Qt.AlignCenter)
        classroom_layout.addWidget(self.student_count_label)
        
        # Прокручиваемая область для карточек студентов
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(500)
        
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        
        scroll_area.setWidget(self.cards_container)
        classroom_layout.addWidget(scroll_area)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self._refresh_students)
        buttons_layout.addWidget(refresh_btn)
        
        lock_all_btn = QPushButton("🚫 Заблокировать всех")
        lock_all_btn.clicked.connect(self._lock_all_screens)
        buttons_layout.addWidget(lock_all_btn)
        
        unlock_all_btn = QPushButton("✅ Разблокировать всех")
        unlock_all_btn.clicked.connect(self._unlock_all_screens)
        buttons_layout.addWidget(unlock_all_btn)
        
        classroom_layout.addLayout(buttons_layout)
        
        parent_layout.addWidget(classroom_widget, stretch=2)
    
    def _create_info_panel(self, parent_layout):
        """Создать информационную панель"""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Информация о выбранном студенте
        info_group = QFrame()
        info_group.setFrameStyle(QFrame.Box)
        info_group_layout = QVBoxLayout(info_group)
        
        title = QLabel("ИНФОРМАЦИЯ И УПРАВЛЕНИЕ")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        info_group_layout.addWidget(title)
        
        self.selected_student_label = QLabel("Выбран студент: -")
        info_group_layout.addWidget(self.selected_student_label)
        
        # Быстрые действия
        actions_label = QLabel("БЫСТРЫЕ ДЕЙСТВИЯ:")
        actions_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        info_group_layout.addWidget(actions_label)
        
        speak_btn = QPushButton("🎙️ Говорить со студентом")
        info_group_layout.addWidget(speak_btn)
        
        monitor_btn = QPushButton("👁️ Наблюдать экран")
        monitor_btn.clicked.connect(self._monitor_student)
        info_group_layout.addWidget(monitor_btn)
        
        send_file_btn = QPushButton("📁 Отправить файл")
        info_group_layout.addWidget(send_file_btn)
        
        broadcast_btn = QPushButton("🎬 Начать трансляцию")
        info_group_layout.addWidget(broadcast_btn)

        send_msg_btn = QPushButton("💬 Сообщение")
        send_msg_btn.clicked.connect(self._send_message_to_selected)
        info_group_layout.addWidget(send_msg_btn)
        
        info_group_layout.addStretch()
        info_layout.addWidget(info_group)
        
        # Статус класса
        status_group = QFrame()
        status_group.setFrameStyle(QFrame.Box)
        status_group_layout = QVBoxLayout(status_group)
        
        status_title = QLabel("СТАТУС КЛАССА")
        status_title.setAlignment(Qt.AlignCenter)
        status_title.setStyleSheet("font-weight: bold;")
        status_group_layout.addWidget(status_title)
        
        self.online_count_label = QLabel("Подключено: 0/0 студентов")
        status_group_layout.addWidget(self.online_count_label)
        
        self.time_label = QLabel("Время: 00:00:00")
        status_group_layout.addWidget(self.time_label)
        
        self.channel_label = QLabel(f"Канал: {self.channel}")
        status_group_layout.addWidget(self.channel_label)
        
        self.quality_label = QLabel("Качество: Хорошее")
        status_group_layout.addWidget(self.quality_label)
        
        # События
        events_label = QLabel("События:")
        events_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        status_group_layout.addWidget(events_label)
        
        self.events_text = QLabel("Нет событий")
        self.events_text.setWordWrap(True)
        self.events_text.setStyleSheet("font-size: 9pt;")
        status_group_layout.addWidget(self.events_text)
        
        status_group_layout.addStretch()
        info_layout.addWidget(status_group)
        
        parent_layout.addWidget(info_widget, stretch=1)
    
    def _create_statusbar(self):
        """Создать статусную строку"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        self.status_label = QLabel("Готов")
        statusbar.addWidget(self.status_label)
        
        statusbar.addPermanentWidget(QLabel(f"IP: {self.server.ip_address if self.server else '-'}"))
        statusbar.addPermanentWidget(QLabel(f"Порт: {self.server.port if self.server else '-'}"))
    
    def _init_server(self):
        """Инициализировать сервер"""
        try:
            self.server = TeacherServer(self.teacher_name, self.channel)
            
            # Подключаем колбэки
            self.server.on_student_connected = self._on_student_connected
            self.server.on_student_disconnected = self._on_student_disconnected
            self.server.on_message_received = self._on_message_received
            
            # Запускаем сервер
            if self.server.start():
                self.status_label.setText("Сервер запущен")
                self.classroom_control = ClassroomControl(self.server)
                logger.info("Сервер успешно запущен")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить сервер")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации сервера: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка инициализации сервера: {e}")
    
    def _on_student_connected(self, student: Student):
        """Обработка подключения студента"""
        logger.info(f"Студент подключен: {student.name}")
        
        # Запись события
        if self.recording_active:
            self.lesson_recorder.add_event("student_connected", {
                "student_name": student.name,
                "student_id": student.id
            })
        
        # Создаем карточку
        card = StudentCard(student)
        card.clicked.connect(self._on_student_card_clicked)
        
        # Добавляем в сетку
        row = len(self.student_cards) // 4
        col = len(self.student_cards) % 4
        self.cards_layout.addWidget(card, row, col)
        
        self.student_cards[student.id] = card
        self._update_student_count()
        
        # Событие
        self._add_event(f"{student.name} подключился")
    
    def _on_student_disconnected(self, student_id: str):
        """Обработка отключения студента"""
        if student_id in self.student_cards:
            card = self.student_cards[student_id]
            self._add_event(f"{card.student.name} отключился")
            
            # Удаляем карточку
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            del self.student_cards[student_id]
            
            self._update_student_count()
            self._reorganize_cards()
    
    def _on_message_received(self, student_id: str, message: Dict):
        """Обработка сообщения от студента"""
        logger.info(f"Сообщение от {student_id}: {message.get('type')}")
        msg_type = message.get("type")
        data = message.get("data", {})

        if msg_type == MessageType.CHAT_MESSAGE:
            content = data.get("content", "")
            sender = data.get("sender_name", student_id)
            self._add_event(f"Чат от {sender}: {content}")
            
            # Записываем сообщение
            if self.recording_active:
                self.lesson_recorder.add_chat_message(sender, content, is_teacher=False)

        if msg_type == MessageType.EXAM_ANSWER:
            answer = data.get("answer", "")
            exam_id = data.get("exam_id", "")
            self._add_event(f"Ответ на экзамен ({exam_id}) от {student_id}: {answer}")

        if msg_type == MessageType.POLL_ANSWER:
            answer = data.get("answer", "")
            self._add_event(f"Ответ на опрос от {student_id}: {answer}")
        
        # Голос от студента
        if msg_type == MessageType.VOICE_START:
            student_name = data.get("student_name", student_id)
            self._add_event(f"🎤 {student_name} начал говорить")
            self._start_student_voice_receiver()
        
        if msg_type == MessageType.VOICE_DATA:
            if data.get("from_student") and self.student_voice_receiver:
                encoded_data = data.get("data")
                chunk_id = data.get("chunk_id", 0)
                if encoded_data:
                    self.student_voice_receiver.add_voice_data(encoded_data, chunk_id)
        
        if msg_type == MessageType.VOICE_STOP:
            if data.get("student_name"):
                student_name = data.get("student_name", student_id)
                self._add_event(f"🎤 {student_name} закончил говорить")
                self._stop_student_voice_receiver()
        
        # Мониторинг активности
        if msg_type == MessageType.ACTIVITY_REPORT:
            self.activity_tracker.update_report(student_id, data)
        
        if msg_type == MessageType.SCREENSHOT_RESPONSE:
            screenshot_data = data.get("data")
            if screenshot_data:
                self.activity_tracker.update_screenshot(student_id, screenshot_data)
                self._add_event(f"📷 Скриншот получен от {student_id}")
    
    def _start_student_voice_receiver(self):
        """Запустить приём голоса от студента"""
        if not AUDIO_AVAILABLE:
            return
        
        if self.student_voice_receiver and self.student_voice_receiver.active:
            return  # Уже запущен
        
        try:
            self.student_voice_receiver = VoiceReceiver()
            if self.student_voice_receiver.start():
                logger.info("Приём голоса студента запущен")
            else:
                logger.error("Не удалось запустить приём голоса студента")
        except Exception as e:
            logger.error(f"Ошибка запуска приёма голоса: {e}")
    
    def _stop_student_voice_receiver(self):
        """Остановить приём голоса от студента"""
        if self.student_voice_receiver:
            self.student_voice_receiver.stop()
            self.student_voice_receiver = None
            logger.info("Приём голоса студента остановлен")
    
    def _on_student_card_clicked(self, student_id: str):
        """Обработка клика по карточке студента"""
        self.selected_student_id = student_id
        if student_id in self.student_cards:
            student = self.student_cards[student_id].student
            self.selected_student_label.setText(f"Выбран студент: {student.name} ({student.status})")
    
    def _update_student_count(self):
        """Обновить счетчик студентов"""
        total = len(self.student_cards)
        online = sum(1 for card in self.student_cards.values() 
                    if card.student.status == StudentStatus.ONLINE)
        
        self.student_count_label.setText(f"{total} студентов")
        self.online_count_label.setText(f"Подключено: {online}/{total} студентов")
    
    def _reorganize_cards(self):
        """Реорганизовать карточки в сетке"""
        for i, card in enumerate(self.student_cards.values()):
            row = i // 4
            col = i % 4
            self.cards_layout.addWidget(card, row, col)
    
    def _update_status(self):
        """Обновление статуса (вызывается таймером)"""
        from datetime import datetime
        self.time_label.setText(f"Время: {datetime.now().strftime('%H:%M:%S')}")
    
    def _add_event(self, event_text: str):
        """Добавить событие"""
        from datetime import datetime
        time_str = datetime.now().strftime('%H:%M')
        current_text = self.events_text.text()
        
        if current_text == "Нет событий":
            new_text = f"{time_str} - {event_text}"
        else:
            lines = current_text.split('\n')
            lines = lines[-4:]  # Последние 5 событий
            lines.append(f"{time_str} - {event_text}")
            new_text = '\n'.join(lines)
        
        self.events_text.setText(new_text)
    
    def _refresh_students(self):
        """Обновить список студентов"""
        self._add_event("Обновление списка студентов...")
    
    def _lock_all_screens(self):
        """Заблокировать экраны всех студентов"""
        from src.common.constants import MessageType
        self.server.broadcast_to_all(MessageType.LOCK_SCREEN, {"message": "Экран заблокирован преподавателем"})
        self._add_event("Все экраны заблокированы")
        QMessageBox.information(self, "Блокировка", "Экраны всех студентов заблокированы")
    
    def _unlock_all_screens(self):
        """Разблокировать экраны всех студентов"""
        from src.common.constants import MessageType
        self.server.broadcast_to_all(MessageType.UNLOCK_SCREEN, {})
        self._add_event("Все экраны разблокированы")
    
    def _lock_all_input(self):
        """Заблокировать ввод (клавиатура/мышь) у всех студентов"""
        from src.common.constants import MessageType
        self.server.broadcast_to_all(MessageType.LOCK_INPUT, {})
        self._add_event("⌨️ Ввод заблокирован у всех студентов")
        QMessageBox.information(self, "Блокировка", "Ввод заблокирован у всех студентов")
    
    def _unlock_all_input(self):
        """Разблокировать ввод у всех студентов"""
        from src.common.constants import MessageType
        self.server.broadcast_to_all(MessageType.UNLOCK_INPUT, {})
        self._add_event("⌨️ Ввод разблокирован у всех студентов")
    
    def _request_all_screenshots(self):
        """Запросить скриншоты у всех студентов"""
        from src.common.constants import MessageType
        self.server.broadcast_to_all(MessageType.SCREENSHOT_REQUEST, {})
        self._add_event("📷 Запрошены скриншоты у всех студентов")
    
    def _show_activity_report(self):
        """Показать отчёт об активности"""
        reports = self.activity_tracker.get_all_reports()
        
        if not reports:
            QMessageBox.information(self, "Активность", "Нет данных об активности")
            return
        
        # Формируем отчёт
        text = "📊 Отчёт активности студентов:\n\n"
        
        for student_id, report in reports.items():
            # Получаем имя студента
            student = self.server.students.get(student_id)
            name = student.name if student else student_id
            
            status = "✅" if report.is_active else "⚠️"
            text += f"{status} {name}\n"
            text += f"   Окно: {report.active_window[:40]}...\n"
            text += f"   Приложение: {report.active_process}\n"
            text += f"   Неактивен: {report.idle_time:.0f} сек\n\n"
        
        # Показываем неактивных
        inactive = self.activity_tracker.get_inactive_students()
        if inactive:
            text += f"\n⚠️ Неактивные студенты: {len(inactive)}\n"
        
        QMessageBox.information(self, "Активность студентов", text)
    
    def _set_web_access(self, mode: str):
        """Установить режим веб-доступа"""
        from src.common.constants import MessageType
        
        if mode == "full":
            self.web_controller.set_full_access()
            self._add_event("🌐 Веб-доступ: полный")
        elif mode == "educational":
            self.web_controller.set_educational_only()
            self._add_event("🌐 Веб-доступ: только образовательные")
        elif mode == "block_social":
            self.web_controller.block_social()
            self._add_event("🌐 Веб-доступ: соц.сети заблокированы")
        elif mode == "no_access":
            self.web_controller.set_no_access()
            self._add_event("🌐 Веб-доступ: заблокирован")
        
        # Отправляем конфигурацию студентам
        config = self.web_controller.get_config()
        self.server.broadcast_to_all(MessageType.WEB_CONTROL_SET, config)
        
        logger.info(f"Веб-контроль установлен: {mode}")
    
    def _start_screen_broadcast(self):
        """Начать трансляцию экрана"""
        if self.streaming:
            # Остановить
            if self.screen_capture:
                self.screen_capture.stop()
                self.screen_capture = None
            self.streaming = False
            self.server.broadcast_to_all(
                MessageType.SCREEN_STREAM_STOP,
                {"reason": "stopped_by_teacher"}
            )
            self._add_event("Трансляция остановлена")
            return

        # Запустить
        self.screen_capture = ScreenCapture()

        def on_frame(frame_bytes: bytes, frame_id: int):
            try:
                payload = base64.b64encode(frame_bytes).decode("ascii")
                self.server.broadcast_to_all(
                    MessageType.SCREEN_FRAME,
                    {"frame_id": frame_id, "payload": payload}
                )
                
                # Записываем кадр если запись активна
                if self.recording_active:
                    self.lesson_recorder.add_screen_frame(frame_bytes)
                
            except Exception as e:
                logging.error(f"Ошибка отправки кадра: {e}")

        self.screen_capture.on_frame = on_frame
        started = self.screen_capture.start()
        if not started:
            QMessageBox.warning(self, "Трансляция", "Не удалось запустить захват экрана")
            return

        self.streaming = True
        settings = self.screen_capture.settings
        self.server.broadcast_to_all(
            MessageType.SCREEN_STREAM_START,
            {
                "resolution": settings["resolution"],
                "fps": settings.get("fps"),
                "quality": settings.get("quality")
            }
        )
        self._add_event("Трансляция экрана запущена")
    
    def _monitor_student(self):
        """Наблюдать за студентом"""
        if not self.selected_student_id:
            QMessageBox.warning(self, "Наблюдение", "Выберите студента")
            return
        
        # TODO: Реализовать наблюдение за студентом
        QMessageBox.information(self, "Наблюдение", "Функция наблюдения в разработке")

    def _send_message_to_selected(self):
        """Отправить сообщение выбранному или всем студентам"""
        text, ok = QInputDialog.getText(self, "Сообщение студентам", "Введите текст сообщения:")
        if not ok or not text:
            return

        if self.selected_student_id:
            self.server.send_to_student(
                self.selected_student_id,
                MessageType.CHAT_MESSAGE,
                {"sender_id": "teacher", "sender_name": self.teacher_name, "content": text}
            )
            self._add_event(f"Сообщение отправлено {self.selected_student_id}")
        else:
            self.server.broadcast_to_all(
                MessageType.CHAT_MESSAGE,
                {"sender_id": "teacher", "sender_name": self.teacher_name, "content": text}
            )
            self._add_event("Сообщение отправлено всем студентам")
            
            # Записываем сообщение преподавателя
            if self.recording_active:
                self.lesson_recorder.add_chat_message(self.teacher_name, text, is_teacher=True)
    
    def _toggle_voice(self):
        """Включить/выключить голосовую связь"""
        if self.voice_active:
            # Выключить
            self._stop_voice()
        else:
            # Включить
            self._start_voice()
    
    def _start_voice(self):
        """Начать голосовую трансляцию"""
        if not AUDIO_AVAILABLE:
            QMessageBox.warning(self, "Голос", "Аудио библиотека не установлена.\nУстановите: pip install sounddevice")
            self.voice_action.setChecked(False)
            return
        
        try:
            self.voice_broadcaster = VoiceBroadcaster()
            
            def on_voice_data(encoded_data: str, chunk_id: int):
                """Отправка голосовых данных всем студентам"""
                try:
                    self.server.broadcast_to_all(
                        MessageType.VOICE_DATA,
                        {"data": encoded_data, "chunk_id": chunk_id}
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки голоса: {e}")
            
            self.voice_broadcaster.on_voice_data = on_voice_data
            
            if self.voice_broadcaster.start():
                self.voice_active = True
                self.voice_action.setChecked(True)
                self.voice_action.setText("🔴 Говорю...")
                
                # Уведомляем студентов
                self.server.broadcast_to_all(MessageType.VOICE_START, {
                    "teacher_name": self.teacher_name
                })
                
                self._add_event("🎤 Голосовая связь включена")
                logger.info("Голосовая трансляция запущена")
            else:
                QMessageBox.warning(
                    self, "Голос", 
                    "Не удалось запустить микрофон.\n\n"
                    "Возможные причины:\n"
                    "• Микрофон не подключен\n"
                    "• Микрофон используется другим приложением\n"
                    "• Нет разрешения на доступ к микрофону\n\n"
                    "Проверьте настройки звука Windows."
                )
                self.voice_action.setChecked(False)
                
        except Exception as e:
            logger.error(f"Ошибка запуска голоса: {e}")
            error_msg = str(e)
            if "PaErrorCode" in error_msg or "host error" in error_msg.lower():
                QMessageBox.warning(
                    self, "Ошибка микрофона",
                    "Не удалось открыть микрофон.\n\n"
                    "Попробуйте:\n"
                    "1. Проверить подключение микрофона\n"
                    "2. Закрыть другие приложения использующие микрофон\n"
                    "3. Перезапустить приложение\n"
                    "4. Проверить настройки конфиденциальности Windows"
                )
            else:
                QMessageBox.warning(self, "Голос", f"Ошибка: {e}")
            self.voice_action.setChecked(False)
    
    def _stop_voice(self):
        """Остановить голосовую трансляцию"""
        if self.voice_broadcaster:
            self.voice_broadcaster.stop()
            self.voice_broadcaster = None
        
        self.voice_active = False
        self.voice_action.setChecked(False)
        self.voice_action.setText("🎤 Говорить")
        
        # Уведомляем студентов
        if self.server:
            self.server.broadcast_to_all(MessageType.VOICE_STOP, {})
        
        self._add_event("🎤 Голосовая связь выключена")
        logger.info("Голосовая трансляция остановлена")
    
    def _toggle_webcam(self):
        """Включить/выключить веб-камеру"""
        if self.webcam_active:
            self._stop_webcam()
        else:
            self._start_webcam()
    
    def _start_webcam(self):
        """Начать трансляцию веб-камеры"""
        if not CV2_AVAILABLE:
            QMessageBox.warning(self, "Камера", "OpenCV не установлен.\nУстановите: pip install opencv-python")
            self.webcam_action.setChecked(False)
            return
        
        try:
            # Проверяем доступные камеры
            cameras = WebcamBroadcaster.list_cameras()
            logger.info(f"Найдено камер: {cameras}")
            
            if not cameras:
                QMessageBox.warning(
                    self, "Камера", 
                    "Веб-камера не найдена.\n\n"
                    "Подключите веб-камеру и попробуйте снова."
                )
                self.webcam_action.setChecked(False)
                return
            
            self.webcam_broadcaster = WebcamBroadcaster()
            
            def on_webcam_frame(encoded_data: str, frame_id: int):
                """Отправка кадров камеры всем студентам"""
                try:
                    self.server.broadcast_to_all(
                        MessageType.WEBCAM_FRAME,
                        {"data": encoded_data, "frame_id": frame_id}
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки кадра камеры: {e}")
            
            self.webcam_broadcaster.on_frame_data = on_webcam_frame
            
            if self.webcam_broadcaster.start(camera_index=cameras[0]):
                self.webcam_active = True
                self.webcam_action.setChecked(True)
                self.webcam_action.setText("🔴 Камера ON")
                
                # Уведомляем студентов
                self.server.broadcast_to_all(MessageType.WEBCAM_START, {
                    "teacher_name": self.teacher_name
                })
                
                self._add_event(f"📹 Веб-камера включена (камера {cameras[0]})")
                logger.info(f"Трансляция веб-камеры запущена (камера {cameras[0]})")
            else:
                QMessageBox.warning(
                    self, "Камера", 
                    "Не удалось запустить веб-камеру.\n\n"
                    "Камера может использоваться другим приложением."
                )
                self.webcam_action.setChecked(False)
                
        except Exception as e:
            logger.error(f"Ошибка запуска веб-камеры: {e}")
            QMessageBox.warning(self, "Камера", f"Ошибка: {e}")
            self.webcam_action.setChecked(False)
    
    def _stop_webcam(self):
        """Остановить трансляцию веб-камеры"""
        if self.webcam_broadcaster:
            self.webcam_broadcaster.stop()
            self.webcam_broadcaster = None
        
        self.webcam_active = False
        self.webcam_action.setChecked(False)
        self.webcam_action.setText("📹 Камера")
        
        # Уведомляем студентов
        if self.server:
            self.server.broadcast_to_all(MessageType.WEBCAM_STOP, {})
        
        self._add_event("📹 Веб-камера выключена")
        logger.info("Трансляция веб-камеры остановлена")
    
    def _open_whiteboard(self):
        """Открыть интерактивную доску"""
        if self.whiteboard_window and self.whiteboard_window.isVisible():
            self.whiteboard_window.raise_()
            self.whiteboard_window.activateWindow()
            return
        
        self.whiteboard_window = TeacherWhiteboardWindow(self.server, self)
        self.whiteboard_window.closed.connect(self._on_whiteboard_closed)
        self.whiteboard_window.show()
        
        self._add_event("📝 Интерактивная доска открыта")
        logger.info("Интерактивная доска открыта")
    
    def _on_whiteboard_closed(self):
        """Обработка закрытия доски"""
        self.whiteboard_window = None
        self._add_event("📝 Интерактивная доска закрыта")
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        reply = QMessageBox.question(
            self, 'Выход',
            "Вы уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Останавливаем голосовую связь
            if self.voice_active:
                self._stop_voice()
            
            # Останавливаем веб-камеру
            if self.webcam_active:
                self._stop_webcam()
            
            # Закрываем доску
            if self.whiteboard_window:
                self.whiteboard_window.close()
            
            if self.streaming and self.screen_capture:
                self.screen_capture.stop()
            if self.server:
                self.server.stop()
            event.accept()
        else:
            event.ignore()

    def _start_quick_exam(self):
        """Быстрый экзаменационный вопрос (упрощенный)"""
        question = "Напишите перевод слова 'education' на русский"
        payload = {
            "exam_id": "quick_exam",
            "title": "Быстрый вопрос",
            "question": question
        }
        self.server.broadcast_to_all(MessageType.EXAM_START, payload)
        self._add_event("Экзамен отправлен студентам")

    def _start_quick_poll(self):
        """Быстрый опрос (да/нет)"""
        question = "Всё ли понятно по материалу?"
        payload = {
            "poll_id": "quick_poll",
            "question": question,
            "options": ["Да", "Нет"]
        }
        self.server.broadcast_to_all(MessageType.POLL_START, payload)
        self._add_event("Опрос отправлен студентам")

    def _create_groups_quick(self):
        """Быстрое создание случайных групп по 2 человека"""
        if not self.classroom_control:
            QMessageBox.warning(self, "Группы", "Контроллер классов не инициализирован")
            return
        groups = self.classroom_control.create_random_groups(group_size=2)
        self._add_event(f"Создано групп: {len(groups)}")
    
    def _setup_file_sender(self):
        """Настроить отправщик файлов"""
        def on_transfer_start(info):
            self._add_event(f"📁 Начата отправка: {info.filename}")
            # Уведомляем студентов о начале
            self.server.broadcast_to_all(MessageType.FILE_TRANSFER_START, {
                'transfer_id': info.transfer_id,
                'filename': info.filename,
                'file_size': info.file_size,
                'file_hash': info.file_hash,
                'total_chunks': info.total_chunks
            })
        
        def on_chunk(transfer_id, chunk_num, data, total):
            # Отправляем чанк студентам
            self.server.broadcast_to_all(MessageType.FILE_TRANSFER_DATA, {
                'transfer_id': transfer_id,
                'chunk_num': chunk_num,
                'data': data,
                'total': total
            })
        
        def on_complete(info):
            self._add_event(f"📁 Отправка завершена: {info.filename}")
            self.server.broadcast_to_all(MessageType.FILE_TRANSFER_END, {
                'transfer_id': info.transfer_id
            })
        
        self.file_sender.on_transfer_start = on_transfer_start
        self.file_sender.on_chunk = on_chunk
        self.file_sender.on_transfer_complete = on_complete
    
    def _send_file_to_students(self):
        """Отправить файл студентам"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл для отправки",
            "",
            "Все файлы (*.*)"
        )
        
        if file_path:
            transfer_id = self.file_sender.send_file(file_path)
            if transfer_id:
                QMessageBox.information(
                    self, "Отправка файла",
                    f"Файл отправляется студентам..."
                )
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось отправить файл")
    
    def _toggle_recording(self):
        """Начать/остановить запись урока"""
        if not self.recording_active:
            # Начать запись
            lesson_name, ok = QInputDialog.getText(
                self,
                "Запись урока",
                "Введите название урока:"
            )
            
            if not ok or not lesson_name:
                self.record_action.setChecked(False)
                return
            
            # Получаем список студентов
            student_names = [s.name for s in self.server.get_students()]
            
            try:
                path = self.lesson_recorder.start_recording(
                    lesson_name=lesson_name,
                    teacher_name=self.teacher_name,
                    students=student_names
                )
                
                self.recording_active = True
                self.record_action.setText("⏹️ Стоп")
                self._add_event(f"🔴 Запись начата: {lesson_name}")
                
                logger.info(f"Запись урока начата: {path}")
                
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось начать запись: {e}")
                self.record_action.setChecked(False)
        
        else:
            # Остановить запись
            try:
                path = self.lesson_recorder.stop_recording()
                
                self.recording_active = False
                self.record_action.setText("🔴 Запись")
                self.record_action.setChecked(False)
                self._add_event(f"⏹️ Запись остановлена")
                
                if path:
                    QMessageBox.information(
                        self,
                        "Запись завершена",
                        f"Урок сохранён в:\n{path}\n\n"
                        f"Кадров: {self.lesson_recorder.metadata.frame_count}\n"
                        f"События: {self.lesson_recorder.metadata.event_count}\n"
                        f"Чат: {self.lesson_recorder.metadata.chat_messages}"
                    )
                
                logger.info(f"Запись урока остановлена: {path}")
                
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка остановки записи: {e}")

