"""
Главное окно студента
Версия 2.0 - с адаптивным отображением трансляции
"""

import logging
import base64
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QMessageBox,
    QSystemTrayIcon, QMenu, QTextEdit, QFrame, QLineEdit, 
    QSpinBox, QInputDialog, QSizePolicy, QApplication, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap, QKeySequence
from typing import List, Optional
from src.common.utils import validate_ip, get_app_dir
from src.common.models import Teacher
from src.network.client import StudentClient
from src.common.constants import MessageType
from src.streaming.screen_capture import ScreenReceiver
from src.audio.voice_stream import VoiceReceiver, VoiceBroadcaster, AUDIO_AVAILABLE
from src.streaming.webcam_capture import WebcamReceiver, CV2_AVAILABLE
from src.student.whiteboard_window import StudentWhiteboardWindow
from src.control.input_blocker import ScreenLocker, INPUT_BLOCKER_AVAILABLE
from src.control.web_control import WebControlClient
from src.files import FileReceiver
from src.control.activity_monitor import ActivityMonitor, ScreenshotCapture, ACTIVITY_MONITOR_AVAILABLE


logger = logging.getLogger(__name__)


class FullscreenStreamWindow(QWidget):
    """Полноэкранное окно для просмотра трансляции"""
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Трансляция экрана")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        
        # Черный фон
        self.setStyleSheet("background-color: #000000;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Область отображения
        self.stream_label = QLabel()
        self.stream_label.setAlignment(Qt.AlignCenter)
        self.stream_label.setStyleSheet("background-color: #000000;")
        self.stream_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.stream_label)
        
        # Подсказка внизу
        self.hint_label = QLabel("Нажмите ESC или двойной клик для выхода")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: #666666; font-size: 10pt; padding: 5px;")
        layout.addWidget(self.hint_label)
        
        # Таймер скрытия подсказки
        self.hint_timer = QTimer()
        self.hint_timer.timeout.connect(self._hide_hint)
        self.hint_timer.setSingleShot(True)
    
    def showFullScreen(self):
        """Показать на весь экран"""
        super().showFullScreen()
        self.hint_label.show()
        self.hint_timer.start(3000)  # Скрыть через 3 секунды
    
    def _hide_hint(self):
        """Скрыть подсказку"""
        self.hint_label.hide()
    
    def update_frame(self, pixmap: QPixmap):
        """Обновить кадр с сохранением пропорций"""
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                self.stream_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.stream_label.setPixmap(scaled)
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Двойной клик — выход"""
        self.close()
    
    def closeEvent(self, event):
        """Закрытие окна"""
        self.closed.emit()
        event.accept()


class StreamWidget(QFrame):
    """Виджет для отображения трансляции с адаптивным размером"""
    
    fullscreen_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setStyleSheet("""
            StreamWidget {
                background-color: #1a1a2e;
                border: 2px solid #16213e;
                border-radius: 8px;
            }
        """)
        
        # Минимальные размеры для правильного соотношения 16:9
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        
        # Область отображения кадра
        self.frame_label = QLabel("Трансляция не запущена")
        self.frame_label.setAlignment(Qt.AlignCenter)
        self.frame_label.setStyleSheet("""
            QLabel {
                background-color: #0f0f23;
                color: #4a4a6a;
                font-size: 14pt;
                border-radius: 4px;
            }
        """)
        self.frame_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.frame_label)
        
        # Панель управления (внизу)
        control_panel = QWidget()
        control_panel.setFixedHeight(32)
        control_panel.setStyleSheet("background: transparent;")
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(4, 2, 4, 2)
        
        # Статус
        self.status_label = QLabel("⚫ Ожидание")
        self.status_label.setStyleSheet("color: #888; font-size: 9pt;")
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        # FPS
        self.fps_label = QLabel("")
        self.fps_label.setStyleSheet("color: #888; font-size: 9pt;")
        control_layout.addWidget(self.fps_label)
        
        # Кнопка полноэкранного режима
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(28, 28)
        self.fullscreen_btn.setToolTip("Полный экран (F11)")
        self.fullscreen_btn.setStyleSheet("""
            QPushButton {
                background: #2d2d44;
                border: 1px solid #3d3d5c;
                border-radius: 4px;
                color: #aaa;
                font-size: 14pt;
            }
            QPushButton:hover {
                background: #3d3d5c;
                color: #fff;
            }
        """)
        self.fullscreen_btn.clicked.connect(self.fullscreen_requested.emit)
        control_layout.addWidget(self.fullscreen_btn)
        
        layout.addWidget(control_panel)
        
        # Текущий pixmap
        self._current_pixmap: Optional[QPixmap] = None
        self._frames_count = 0
        self._last_fps_update = 0
    
    def update_frame(self, pixmap: QPixmap):
        """Обновить кадр"""
        if pixmap and not pixmap.isNull():
            self._current_pixmap = pixmap
            self._frames_count += 1
            self._display_scaled_frame()
            
            # Обновляем статус
            self.status_label.setText("🟢 Трансляция")
            self.status_label.setStyleSheet("color: #4ade80; font-size: 9pt;")
    
    def _display_scaled_frame(self):
        """Отобразить масштабированный кадр"""
        if self._current_pixmap:
            # Масштабируем с сохранением пропорций
            scaled = self._current_pixmap.scaled(
                self.frame_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.frame_label.setPixmap(scaled)
    
    def resizeEvent(self, event):
        """При изменении размера окна — перемасштабировать кадр"""
        super().resizeEvent(event)
        if self._current_pixmap:
            self._display_scaled_frame()
    
    def set_status(self, status: str, color: str = "#888"):
        """Установить статус"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 9pt;")
    
    def set_fps(self, fps: float):
        """Установить FPS"""
        self.fps_label.setText(f"{fps:.1f} fps")
    
    def clear(self):
        """Очистить область"""
        self._current_pixmap = None
        self.frame_label.clear()
        self.frame_label.setText("Трансляция остановлена")
        self.set_status("⚫ Остановлено", "#888")
        self.fps_label.setText("")
    
    def mouseDoubleClickEvent(self, event):
        """Двойной клик — полноэкранный режим"""
        self.fullscreen_requested.emit()


class StudentMainWindow(QMainWindow):
    """Главное окно студента"""
    
    # Сигналы
    teacher_found = pyqtSignal(Teacher)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    
    def __init__(self, student_name: str):
        super().__init__()
        self.student_name = student_name
        self.screen_receiver = ScreenReceiver()
        self.stream_active = False
        self.lock_overlay = None
        
        # Голосовая связь (прием от преподавателя)
        self.voice_receiver: Optional[VoiceReceiver] = None
        self.voice_active = False
        
        # Голосовая связь (отправка преподавателю)
        self.voice_broadcaster: Optional[VoiceBroadcaster] = None
        self.speaking = False
        
        # Веб-камера
        self.webcam_receiver: Optional[WebcamReceiver] = None
        self.webcam_active = False
        
        # Интерактивная доска
        self.whiteboard_window: Optional[StudentWhiteboardWindow] = None
        
        # Блокировка экрана
        self.screen_locker = ScreenLocker()
        
        # Веб-контроль
        self.web_control = WebControlClient()
        
        # Приём файлов
        self.file_receiver = FileReceiver(save_dir="downloads")
        self._setup_file_receiver()
        
        # Мониторинг активности
        self.activity_monitor = ActivityMonitor(report_interval=15)
        self._setup_activity_monitor()
        
        # Полноэкранное окно трансляции
        self.fullscreen_window: Optional[FullscreenStreamWindow] = None
        
        # Клиент
        self.client: StudentClient = None
        
        # Системный трей
        self.tray_icon: QSystemTrayIcon = None
        
        # FPS счетчик
        self._frame_count = 0
        self._last_fps_time = 0
        
        self._init_ui()
        self._init_client()
        self._init_tray()
        self._init_shortcuts()
        self._apply_style()
        
        # Подключаем сигналы
        self.teacher_found.connect(self._on_teacher_found)
        self.connected.connect(self._on_connected)
        self.disconnected.connect(self._on_disconnected)
        self.message_received.connect(self._on_message_received)
        
        # Таймер для FPS
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps)
        self.fps_timer.start(1000)
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle(f"Alfarid - Студент: {self.student_name}")
        self.setMinimumSize(600, 700)
        self.resize(800, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(8)
        
        # Заголовок
        header_layout = QHBoxLayout()
        
        title = QLabel(f"👤 {self.student_name}")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Статус подключения
        self.status_label = QLabel("⚫ Не подключен")
        self.status_label.setStyleSheet("font-size: 12pt; padding: 5px 10px; background: #f0f0f0; border-radius: 4px;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)

        # Область трансляции экрана (адаптивная!)
        self.stream_widget = StreamWidget()
        self.stream_widget.fullscreen_requested.connect(self._toggle_fullscreen)
        layout.addWidget(self.stream_widget, stretch=3)  # Занимает больше места
        
        # Виджет веб-камеры преподавателя (Picture-in-Picture)
        self.webcam_widget = QLabel()
        self.webcam_widget.setFixedSize(160, 120)
        self.webcam_widget.setAlignment(Qt.AlignCenter)
        self.webcam_widget.setStyleSheet("""
            QLabel {
                background: #1a1a2e;
                border: 2px solid #4a4a6a;
                border-radius: 8px;
                color: #888;
            }
        """)
        self.webcam_widget.setText("📹")
        self.webcam_widget.setToolTip("Камера преподавателя")
        self.webcam_widget.hide()  # Скрыт по умолчанию
        
        # Информация о преподавателе
        teacher_frame = QFrame()
        teacher_frame.setFrameStyle(QFrame.Box)
        teacher_frame.setMaximumHeight(80)
        teacher_layout = QVBoxLayout(teacher_frame)
        teacher_layout.setContentsMargins(8, 4, 8, 4)
        
        teacher_header = QHBoxLayout()
        teacher_title = QLabel("📚 Преподаватель:")
        teacher_title.setStyleSheet("font-weight: bold;")
        teacher_header.addWidget(teacher_title)
        
        self.teacher_label = QLabel("Поиск...")
        teacher_header.addWidget(self.teacher_label)
        teacher_header.addStretch()
        
        self.teacher_ip_label = QLabel("IP: -")
        self.teacher_ip_label.setStyleSheet("color: #666;")
        teacher_header.addWidget(self.teacher_ip_label)
        
        teacher_layout.addLayout(teacher_header)
        layout.addWidget(teacher_frame)
        
        # Список доступных преподавателей (свернутый по умолчанию)
        self.teachers_frame = QFrame()
        self.teachers_frame.setMaximumHeight(120)
        teachers_layout = QVBoxLayout(self.teachers_frame)
        teachers_layout.setContentsMargins(0, 0, 0, 0)
        
        available_label = QLabel("🔍 Доступные преподаватели:")
        available_label.setStyleSheet("font-weight: bold;")
        teachers_layout.addWidget(available_label)
        
        self.teachers_list = QListWidget()
        self.teachers_list.setMaximumHeight(60)
        self.teachers_list.itemDoubleClicked.connect(self._on_teacher_selected)
        teachers_layout.addWidget(self.teachers_list)
        
        layout.addWidget(self.teachers_frame)
        
        # Кнопки управления подключением
        buttons_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("🔌 Подключиться")
        self.connect_btn.clicked.connect(self._connect_to_teacher)
        self.connect_btn.setEnabled(False)
        buttons_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("❌ Отключиться")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.disconnect_btn.setEnabled(False)
        buttons_layout.addWidget(self.disconnect_btn)
        
        layout.addLayout(buttons_layout)

        # Ручное подключение
        manual_layout = QHBoxLayout()
        self.manual_ip = QLineEdit()
        self.manual_ip.setPlaceholderText("IP преподавателя")
        self.manual_ip.setText("192.168.1.100")
        manual_layout.addWidget(self.manual_ip)

        self.manual_port = QSpinBox()
        self.manual_port.setRange(1, 65535)
        self.manual_port.setValue(9999)
        self.manual_port.setFixedWidth(80)
        manual_layout.addWidget(self.manual_port)

        manual_btn = QPushButton("Подключиться по IP")
        manual_btn.clicked.connect(self._manual_connect)
        manual_layout.addWidget(manual_btn)

        layout.addLayout(manual_layout)
        
        # Кнопки действий
        actions_layout = QHBoxLayout()
        
        # Кнопка "Поднять руку"
        self.raise_hand_btn = QPushButton("🖐️ Рука")
        self.raise_hand_btn.clicked.connect(self._raise_hand)
        self.raise_hand_btn.setEnabled(False)
        self.raise_hand_btn.setToolTip("Поднять руку (запросить внимание)")
        self.raise_hand_btn.setStyleSheet("""
            QPushButton {
                background: #fef3c7;
                border: 2px solid #f59e0b;
                padding: 8px;
                font-size: 11pt;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #fde68a;
            }
            QPushButton:disabled {
                background: #e5e5e5;
                border-color: #ccc;
            }
        """)
        actions_layout.addWidget(self.raise_hand_btn)
        
        # Кнопка "Говорить с преподавателем"
        self.speak_btn = QPushButton("🎤 Говорить")
        self.speak_btn.setCheckable(True)
        self.speak_btn.clicked.connect(self._toggle_speak)
        self.speak_btn.setEnabled(False)
        self.speak_btn.setToolTip("Говорить с преподавателем (зажмите для разговора)")
        if not AUDIO_AVAILABLE:
            self.speak_btn.setToolTip("sounddevice не установлен")
            self.speak_btn.setEnabled(False)
        self.speak_btn.setStyleSheet("""
            QPushButton {
                background: #dbeafe;
                border: 2px solid #3b82f6;
                padding: 8px;
                font-size: 11pt;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #bfdbfe;
            }
            QPushButton:checked {
                background: #ef4444;
                border-color: #dc2626;
                color: white;
            }
            QPushButton:disabled {
                background: #e5e5e5;
                border-color: #ccc;
            }
        """)
        actions_layout.addWidget(self.speak_btn)
        
        layout.addLayout(actions_layout)
        
        # Область сообщений (компактная)
        messages_frame = QFrame()
        messages_frame.setMaximumHeight(150)
        messages_layout = QVBoxLayout(messages_frame)
        messages_layout.setContentsMargins(0, 0, 0, 0)
        
        messages_label = QLabel("💬 Сообщения:")
        messages_label.setStyleSheet("font-weight: bold;")
        messages_layout.addWidget(messages_label)
        
        self.messages_text = QTextEdit()
        self.messages_text.setReadOnly(True)
        self.messages_text.setMaximumHeight(60)
        messages_layout.addWidget(self.messages_text)
        
        # Отправка сообщения
        message_input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Введите сообщение...")
        self.message_input.returnPressed.connect(self._send_message)
        message_input_layout.addWidget(self.message_input)
        
        send_btn = QPushButton("➤")
        send_btn.setFixedWidth(40)
        send_btn.clicked.connect(self._send_message)
        send_btn.setEnabled(False)
        self.send_message_btn = send_btn
        message_input_layout.addWidget(send_btn)
        
        messages_layout.addLayout(message_input_layout)
        layout.addWidget(messages_frame)

    def _init_shortcuts(self):
        """Инициализация горячих клавиш"""
        # F11 — полноэкранный режим
        self.shortcut_fullscreen = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.shortcut_fullscreen.activated.connect(self._toggle_fullscreen)
        
        # Escape — выход из полноэкранного
        self.shortcut_escape = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_escape.activated.connect(self._exit_fullscreen)

    def _apply_style(self):
        """Загрузить QSS тему"""
        try:
            qss_path = Path(get_app_dir()) / "resources" / "styles.qss"
            if qss_path.exists():
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            logger.error(f"Не удалось применить стиль: {e}")
    
    def _init_client(self):
        """Инициализировать клиент"""
        try:
            self.client = StudentClient(self.student_name)
            
            # Подключаем колбэки
            self.client.on_teacher_found = lambda t: self.teacher_found.emit(t)
            self.client.on_connected = lambda: self.connected.emit()
            self.client.on_disconnected = lambda: self.disconnected.emit()
            self.client.on_message_received = lambda m: self.message_received.emit(m)
            
            # Запускаем поиск преподавателей
            if self.client.start_discovery():
                logger.info("Поиск преподавателей запущен")
                self._add_message("Поиск преподавателей...")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить поиск преподавателей")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации клиента: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка инициализации: {e}")
    
    def _init_tray(self):
        """Инициализировать системный трей"""
        self.tray_icon = QSystemTrayIcon(self)
        # TODO: Установить иконку
        # self.tray_icon.setIcon(QIcon("resources/icon.png"))
        
        # Меню трея
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Показать")
        show_action.triggered.connect(self.show)
        
        hide_action = tray_menu.addAction("Скрыть")
        hide_action.triggered.connect(self.hide)
        
        tray_menu.addSeparator()
        
        fullscreen_action = tray_menu.addAction("⛶ Полный экран (F11)")
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        
        raise_hand_action = tray_menu.addAction("🖐️ Поднять руку")
        raise_hand_action.triggered.connect(self._raise_hand)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Выход")
        quit_action.triggered.connect(self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Обработка двойного клика
        self.tray_icon.activated.connect(self._on_tray_activated)
    
    def _on_tray_activated(self, reason):
        """Обработка активации иконки трея"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
    
    def _toggle_fullscreen(self):
        """Переключить полноэкранный режим"""
        if not self.stream_active:
            return
        
        if self.fullscreen_window and self.fullscreen_window.isVisible():
            self.fullscreen_window.close()
        else:
            self._enter_fullscreen()
    
    def _enter_fullscreen(self):
        """Войти в полноэкранный режим"""
        if not self.fullscreen_window:
            self.fullscreen_window = FullscreenStreamWindow()
            self.fullscreen_window.closed.connect(self._on_fullscreen_closed)
        
        # Копируем текущий кадр
        pixmap = self.screen_receiver.get_current_frame_as_pixmap()
        if pixmap:
            self.fullscreen_window.update_frame(pixmap)
        
        self.fullscreen_window.showFullScreen()
    
    def _exit_fullscreen(self):
        """Выйти из полноэкранного режима"""
        if self.fullscreen_window and self.fullscreen_window.isVisible():
            self.fullscreen_window.close()
    
    def _on_fullscreen_closed(self):
        """Обработка закрытия полноэкранного окна"""
        pass
    
    def _update_fps(self):
        """Обновить счетчик FPS"""
        if self.stream_active and self._frame_count > 0:
            self.stream_widget.set_fps(self._frame_count)
            self._frame_count = 0
    
    def _on_teacher_found(self, teacher: Teacher):
        """Обработка обнаружения преподавателя"""
        logger.info(f"Найден преподаватель: {teacher.name}")
        
        # Добавляем в список
        item_text = f"{teacher.name} ({teacher.ip_address}:{teacher.port}, канал {teacher.channel})"
        
        # Проверяем, не добавлен ли уже
        for i in range(self.teachers_list.count()):
            if self.teachers_list.item(i).data(Qt.UserRole).id == teacher.id:
                return  # Уже есть
        
        from PyQt5.QtWidgets import QListWidgetItem
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, teacher)
        self.teachers_list.addItem(item)
        
        self.connect_btn.setEnabled(True)
        
        self._add_message(f"Найден преподаватель: {teacher.name}")
    
    def _on_teacher_selected(self, item):
        """Обработка выбора преподавателя"""
        teacher = item.data(Qt.UserRole)
        self.teacher_label.setText(teacher.name)
        self.teacher_ip_label.setText(f"IP: {teacher.ip_address}:{teacher.port}")
    
    def _connect_to_teacher(self):
        """Подключиться к выбранному преподавателю"""
        current_item = self.teachers_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя или используйте подключение по IP")
            return
        
        teacher = current_item.data(Qt.UserRole)
        
        self._add_message(f"Подключение к {teacher.name}...")
        self.connect_btn.setEnabled(False)
        
        if self.client.connect_to_teacher(teacher):
            logger.info(f"Успешно подключен к {teacher.name}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось подключиться к преподавателю")
            self.connect_btn.setEnabled(True)

    def _manual_connect(self):
        """Подключение по IP/Порту (фолбэк, если multicast не работает)"""
        ip = self.manual_ip.text().strip()
        port = self.manual_port.value()

        if not ip or not validate_ip(ip):
            QMessageBox.warning(self, "Ошибка", "Введите корректный IP")
            return

        from src.common.models import Teacher
        teacher = Teacher(
            id=f"{ip}:{port}",
            name=f"Преподаватель ({ip})",
            ip_address=ip,
            channel=1,
            port=port
        )

        self._add_message(f"Подключение к {teacher.name} по IP...")
        self.connect_btn.setEnabled(False)

        if self.client.connect_to_teacher(teacher):
            logger.info(f"Успешно подключен к {teacher.name}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось подключиться по IP")
            self.connect_btn.setEnabled(True)
    
    def _disconnect(self):
        """Отключиться от преподавателя"""
        if self.client:
            self.client.disconnect()
    
    def _on_connected(self):
        """Обработка подключения"""
        self.status_label.setText("🟢 Подключен")
        self.status_label.setStyleSheet("font-size: 12pt; padding: 5px 10px; background: #dcfce7; color: #166534; border-radius: 4px;")
        
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.raise_hand_btn.setEnabled(True)
        self.send_message_btn.setEnabled(True)
        if AUDIO_AVAILABLE:
            self.speak_btn.setEnabled(True)
        
        # Скрываем список преподавателей после подключения
        self.teachers_frame.hide()
        
        self._add_message("Успешно подключено!")
        
        # Уведомление в трее
        self.tray_icon.showMessage(
            "Alfarid",
            f"Подключен к преподавателю: {self.client.teacher.name}",
            QSystemTrayIcon.Information,
            3000
        )
        
        # Запускаем мониторинг активности
        if ACTIVITY_MONITOR_AVAILABLE:
            self.activity_monitor.start()
    
    def _on_disconnected(self):
        """Обработка отключения"""
        self.status_label.setText("⚫ Не подключен")
        self.status_label.setStyleSheet("font-size: 12pt; padding: 5px 10px; background: #fee2e2; color: #991b1b; border-radius: 4px;")
        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.raise_hand_btn.setEnabled(False)
        self.send_message_btn.setEnabled(False)
        self.speak_btn.setEnabled(False)
        
        # Останавливаем разговор если активен
        if self.speaking:
            self._stop_speaking()
        
        # Показываем список преподавателей
        self.teachers_frame.show()
        
        # Очищаем область трансляции
        self.stream_active = False
        self.stream_widget.clear()
        
        # Закрываем полноэкранное окно
        self._exit_fullscreen()
        
        # Останавливаем мониторинг активности
        self.activity_monitor.stop()
        
        self._add_message("Отключено от преподавателя")
    
    def _on_message_received(self, message: dict):
        """Обработка полученного сообщения"""
        msg_type = message.get("type")
        msg_data = message.get("data", {})
        
        logger.info(f"Получено сообщение: {msg_type}")
        
        if msg_type == MessageType.CHAT_MESSAGE:
            sender = msg_data.get("sender_name", "Unknown")
            content = msg_data.get("content", "")
            self._add_message(f"{sender}: {content}")
        
        elif msg_type == MessageType.SCREEN_STREAM_START:
            self.stream_active = True
            self._add_message("Началась трансляция экрана")
            self.stream_widget.set_status("🟢 Трансляция", "#4ade80")
        
        elif msg_type == MessageType.SCREEN_FRAME:
            if not self.stream_active:
                self.stream_active = True
            payload = msg_data.get("payload")
            if payload:
                try:
                    frame_bytes = base64.b64decode(payload)
                    frame_id = msg_data.get("frame_id", 0)
                    self.screen_receiver.process_frame(frame_bytes, frame_id)
                    pixmap = self.screen_receiver.get_current_frame_as_pixmap()
                    if pixmap:
                        # Обновляем виджет трансляции
                        self.stream_widget.update_frame(pixmap)
                        
                        # Обновляем полноэкранное окно если открыто
                        if self.fullscreen_window and self.fullscreen_window.isVisible():
                            self.fullscreen_window.update_frame(pixmap)
                        
                        self._frame_count += 1
                except Exception as e:
                    logger.error(f"Ошибка обработки кадра: {e}")
        
        elif msg_type == MessageType.SCREEN_STREAM_STOP:
            self.stream_active = False
            self.stream_widget.clear()
            self._exit_fullscreen()

        elif msg_type == MessageType.EXAM_START:
            question = msg_data.get("question", "Вопрос")
            exam_id = msg_data.get("exam_id", "exam")
            answer, ok = QInputDialog.getText(self, "📝 Экзамен", question)
            if ok and self.client:
                self.client.send_message(MessageType.EXAM_ANSWER, {
                    "exam_id": exam_id,
                    "answer": answer
                })
                self._add_message("Ответ отправлен")

        elif msg_type == MessageType.POLL_START:
            question = msg_data.get("question", "Опрос")
            options = msg_data.get("options", ["Да", "Нет"])
            selected, ok = QInputDialog.getItem(self, "📊 Опрос", question, options, editable=False)
            if ok and self.client:
                self.client.send_message(MessageType.POLL_ANSWER, {
                    "answer": selected
                })
                self._add_message("Ответ на опрос отправлен")
        
        elif msg_type == MessageType.LOCK_SCREEN:
            lock_message = msg_data.get("message", "Экран заблокирован")
            self._show_lock_screen(lock_message)
        
        elif msg_type == MessageType.UNLOCK_SCREEN:
            self._hide_lock_screen()
        
        elif msg_type == MessageType.LOCK_INPUT:
            # Только блокировка ввода без оверлея
            if INPUT_BLOCKER_AVAILABLE:
                self.screen_locker.input_blocker.block()
                self._add_message("⌨️ Ввод заблокирован")
        
        elif msg_type == MessageType.UNLOCK_INPUT:
            if INPUT_BLOCKER_AVAILABLE:
                self.screen_locker.input_blocker.unblock()
                self._add_message("⌨️ Ввод разблокирован")
        
        # Веб-контроль
        elif msg_type == MessageType.WEB_CONTROL_SET:
            self.web_control.apply_config(msg_data)
            mode_desc = self.web_control.get_mode_description()
            self._add_message(f"🌐 {mode_desc}")
        
        # Передача файлов
        elif msg_type == MessageType.FILE_TRANSFER_START:
            self.file_receiver.start_transfer(
                msg_data.get('transfer_id'),
                msg_data.get('filename'),
                msg_data.get('file_size'),
                msg_data.get('file_hash'),
                msg_data.get('total_chunks')
            )
            self._add_message(f"📁 Получение файла: {msg_data.get('filename')}")
        
        elif msg_type == MessageType.FILE_TRANSFER_DATA:
            self.file_receiver.add_chunk(
                msg_data.get('transfer_id'),
                msg_data.get('chunk_num'),
                msg_data.get('data')
            )
        
        elif msg_type == MessageType.FILE_TRANSFER_END:
            transfer_id = msg_data.get('transfer_id')
            info = self.file_receiver.get_transfer_info(transfer_id)
            if info and info.local_path:
                self._add_message(f"📁 Файл получен: {info.filename}")
        
        # Мониторинг активности
        elif msg_type == MessageType.ACTIVITY_REQUEST:
            # Запрос отчёта о активности
            report = self.activity_monitor.get_current_report()
            if self.client:
                self.client.send_message(MessageType.ACTIVITY_REPORT, report.to_dict())
        
        elif msg_type == MessageType.SCREENSHOT_REQUEST:
            # Запрос скриншота
            screenshot = ScreenshotCapture.capture()
            if screenshot and self.client:
                self.client.send_message(MessageType.SCREENSHOT_RESPONSE, {
                    'data': screenshot
                })
        
        # Голосовая связь
        elif msg_type == MessageType.VOICE_START:
            self._start_voice_playback()
            teacher_name = msg_data.get("teacher_name", "Преподаватель")
            self._add_message(f"🎤 {teacher_name} начал говорить")
        
        elif msg_type == MessageType.VOICE_DATA:
            if self.voice_active and self.voice_receiver:
                encoded_data = msg_data.get("data")
                chunk_id = msg_data.get("chunk_id", 0)
                if encoded_data:
                    self.voice_receiver.add_voice_data(encoded_data, chunk_id)
        
        elif msg_type == MessageType.VOICE_STOP:
            self._stop_voice_playback()
            self._add_message("🎤 Голосовая связь завершена")
        
        # Веб-камера
        elif msg_type == MessageType.WEBCAM_START:
            self._start_webcam_display()
            teacher_name = msg_data.get("teacher_name", "Преподаватель")
            self._add_message(f"📹 {teacher_name} включил камеру")
        
        elif msg_type == MessageType.WEBCAM_FRAME:
            if self.webcam_active and self.webcam_receiver:
                encoded_data = msg_data.get("data")
                frame_id = msg_data.get("frame_id", 0)
                if encoded_data:
                    try:
                        frame_bytes = base64.b64decode(encoded_data)
                        self.webcam_receiver.process_frame(frame_bytes, frame_id)
                        
                        # Обновляем виджет камеры
                        pixmap = self.webcam_receiver.get_current_frame_as_pixmap()
                        if pixmap and hasattr(self, 'webcam_widget'):
                            scaled = pixmap.scaled(
                                self.webcam_widget.size(),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation
                            )
                            self.webcam_widget.setPixmap(scaled)
                    except Exception as e:
                        logger.error(f"Ошибка обработки кадра камеры: {e}")
        
        elif msg_type == MessageType.WEBCAM_STOP:
            self._stop_webcam_display()
            self._add_message("📹 Камера выключена")
        
        # Интерактивная доска
        elif msg_type == MessageType.WHITEBOARD_START:
            self._open_whiteboard()
            self._add_message("📝 Преподаватель открыл интерактивную доску")
        
        elif msg_type == MessageType.WHITEBOARD_COMMAND:
            if self.whiteboard_window and self.whiteboard_window.isVisible():
                self.whiteboard_window.apply_command(msg_data)
        
        elif msg_type == MessageType.WHITEBOARD_SYNC:
            if self.whiteboard_window and self.whiteboard_window.isVisible():
                image_data = msg_data.get('image')
                if image_data:
                    self.whiteboard_window.sync_canvas(image_data)
        
        elif msg_type == MessageType.WHITEBOARD_STOP:
            self._close_whiteboard()
            self._add_message("📝 Интерактивная доска закрыта")
        
        # Другие типы сообщений обрабатываются здесь
    
    def _show_lock_screen(self, message: str, block_input: bool = True):
        """Показать экран блокировки"""
        # Закрываем полноэкранную трансляцию
        self._exit_fullscreen()
        
        # Используем ScreenLocker с блокировкой ввода
        self.screen_locker.lock(message, block_input=block_input)
        
        logger.info(f"Экран заблокирован: {message}")
    
    def _hide_lock_screen(self):
        """Скрыть экран блокировки"""
        self.screen_locker.unlock()
        logger.info("Экран разблокирован")
    
    def _start_voice_playback(self):
        """Запустить воспроизведение голоса преподавателя"""
        if not AUDIO_AVAILABLE:
            logger.warning("sounddevice не установлен, голос недоступен")
            return
        
        if self.voice_active:
            return
        
        try:
            self.voice_receiver = VoiceReceiver()
            if self.voice_receiver.start():
                self.voice_active = True
                logger.info("Воспроизведение голоса запущено")
            else:
                logger.error("Не удалось запустить воспроизведение голоса")
                self.voice_receiver = None
        except Exception as e:
            logger.error(f"Ошибка запуска воспроизведения голоса: {e}")
    
    def _stop_voice_playback(self):
        """Остановить воспроизведение голоса"""
        if self.voice_receiver:
            self.voice_receiver.stop()
            self.voice_receiver = None
        self.voice_active = False
        logger.info("Воспроизведение голоса остановлено")
    
    def _start_webcam_display(self):
        """Запустить отображение веб-камеры преподавателя"""
        if not CV2_AVAILABLE:
            logger.warning("OpenCV не установлен, камера недоступна")
            return
        
        if self.webcam_active:
            return
        
        try:
            self.webcam_receiver = WebcamReceiver()
            self.webcam_active = True
            self.webcam_widget.show()
            logger.info("Отображение веб-камеры запущено")
        except Exception as e:
            logger.error(f"Ошибка запуска отображения камеры: {e}")
    
    def _stop_webcam_display(self):
        """Остановить отображение веб-камеры"""
        self.webcam_receiver = None
        self.webcam_active = False
        self.webcam_widget.hide()
        self.webcam_widget.setText("📹")
        logger.info("Отображение веб-камеры остановлено")
    
    def _open_whiteboard(self):
        """Открыть интерактивную доску"""
        if self.whiteboard_window and self.whiteboard_window.isVisible():
            self.whiteboard_window.raise_()
            self.whiteboard_window.activateWindow()
            return
        
        self.whiteboard_window = StudentWhiteboardWindow(self)
        self.whiteboard_window.show()
        logger.info("Интерактивная доска открыта")
    
    def _close_whiteboard(self):
        """Закрыть интерактивную доску"""
        if self.whiteboard_window:
            self.whiteboard_window.close()
            self.whiteboard_window = None
        logger.info("Интерактивная доска закрыта")
    
    def _toggle_speak(self):
        """Включить/выключить режим разговора"""
        if self.speaking:
            self._stop_speaking()
        else:
            self._start_speaking()
    
    def _start_speaking(self):
        """Начать говорить с преподавателем"""
        if not AUDIO_AVAILABLE:
            QMessageBox.warning(self, "Микрофон", "Аудио библиотека не установлена")
            self.speak_btn.setChecked(False)
            return
        
        if not self.client or not self.client.connected:
            QMessageBox.warning(self, "Микрофон", "Нет подключения к преподавателю")
            self.speak_btn.setChecked(False)
            return
        
        try:
            self.voice_broadcaster = VoiceBroadcaster()
            
            def on_voice_data(encoded_data: str, chunk_id: int):
                """Отправка голоса преподавателю"""
                if self.client and self.client.connected:
                    self.client.send_message(MessageType.VOICE_DATA, {
                        "data": encoded_data,
                        "chunk_id": chunk_id,
                        "from_student": True,
                        "student_name": self.student_name
                    })
            
            self.voice_broadcaster.on_voice_data = on_voice_data
            
            if self.voice_broadcaster.start():
                self.speaking = True
                self.speak_btn.setChecked(True)
                self.speak_btn.setText("🔴 Говорю...")
                
                # Уведомляем преподавателя
                self.client.send_message(MessageType.VOICE_START, {
                    "student_name": self.student_name
                })
                
                self._add_message("🎤 Вы начали говорить")
                logger.info("Голосовая связь студента запущена")
            else:
                QMessageBox.warning(
                    self, "Микрофон",
                    "Не удалось запустить микрофон.\n\n"
                    "Проверьте подключение и настройки."
                )
                self.speak_btn.setChecked(False)
                
        except Exception as e:
            logger.error(f"Ошибка запуска микрофона студента: {e}")
            QMessageBox.warning(self, "Микрофон", f"Ошибка: {e}")
            self.speak_btn.setChecked(False)
    
    def _stop_speaking(self):
        """Остановить разговор"""
        if self.voice_broadcaster:
            self.voice_broadcaster.stop()
            self.voice_broadcaster = None
        
        self.speaking = False
        self.speak_btn.setChecked(False)
        self.speak_btn.setText("🎤 Говорить")
        
        # Уведомляем преподавателя
        if self.client and self.client.connected:
            self.client.send_message(MessageType.VOICE_STOP, {
                "student_name": self.student_name
            })
        
        self._add_message("🎤 Разговор завершен")
        logger.info("Голосовая связь студента остановлена")
    
    def _raise_hand(self):
        """Поднять руку"""
        if self.client and self.client.connected:
            self.client.send_message(MessageType.CHAT_MESSAGE, {
                "sender_id": self.client.student_id,
                "sender_name": self.student_name,
                "content": "🖐️ Поднял руку - нужна помощь!"
            })
            self._add_message("✋ Рука поднята")
            
            self.tray_icon.showMessage(
                "Alfarid",
                "Вы подняли руку",
                QSystemTrayIcon.Information,
                2000
            )
    
    def _send_message(self):
        """Отправить сообщение преподавателю"""
        text = self.message_input.text().strip()
        if not text:
            return
        
        if self.client and self.client.connected:
            self.client.send_message(MessageType.CHAT_MESSAGE, {
                "sender_id": self.client.student_id,
                "sender_name": self.student_name,
                "content": text
            })
            self._add_message(f"Вы: {text}")
            self.message_input.clear()
    
    def _setup_file_receiver(self):
        """Настроить приёмник файлов"""
        def on_complete(info):
            self._add_message(f"✅ Файл сохранён: {info.local_path}")
            
            # Показываем уведомление
            self.tray_icon.showMessage(
                "Alfarid",
                f"Файл получен: {info.filename}",
                QSystemTrayIcon.Information,
                3000
            )
        
        def on_error(transfer_id, error):
            self._add_message(f"❌ Ошибка получения файла: {error}")
        
        self.file_receiver.on_complete = on_complete
        self.file_receiver.on_error = on_error
    
    def _setup_activity_monitor(self):
        """Настроить мониторинг активности"""
        def on_report(report):
            if self.client and self.client.connected:
                try:
                    self.client.send_message(
                        MessageType.ACTIVITY_REPORT,
                        report.to_dict()
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчёта: {e}")
        
        self.activity_monitor.on_report = on_report
    
    def _add_message(self, message: str):
        """Добавить сообщение в лог"""
        from datetime import datetime
        time_str = datetime.now().strftime('%H:%M:%S')
        self.messages_text.append(f"[{time_str}] {message}")
    
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
            self._stop_voice_playback()
            
            # Останавливаем разговор
            if self.speaking:
                self._stop_speaking()
            
            # Останавливаем камеру
            self._stop_webcam_display()
            
            # Разблокируем экран если заблокирован
            if self.screen_locker.locked:
                self.screen_locker.unlock()
            
            # Закрываем доску
            self._close_whiteboard()
            
            # Закрываем полноэкранное окно
            if self.fullscreen_window:
                self.fullscreen_window.close()
            
            if self.client:
                self.client.stop()
            if self.tray_icon:
                self.tray_icon.hide()
            event.accept()
        else:
            event.ignore()
