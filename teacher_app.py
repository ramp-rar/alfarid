"""
Главный файл запуска приложения преподавателя
"""

import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QSpinBox, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import logging

from src.common.utils import setup_logging
from src.teacher.main_window import TeacherMainWindow


class LoginDialog(QDialog):
    """Диалог входа преподавателя"""
    
    def __init__(self):
        super().__init__()
        self.teacher_name = None
        self.channel = 1
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Lingua Classroom - Вход преподавателя")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Заголовок
        title = QLabel("Вход в систему")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Имя преподавателя
        name_label = QLabel("Имя преподавателя:")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите ваше имя")
        self.name_input.setText("Иванов И.В.")  # По умолчанию для тестирования
        layout.addWidget(self.name_input)
        
        # Канал
        channel_layout = QHBoxLayout()
        channel_label = QLabel("Номер канала (1-32):")
        channel_layout.addWidget(channel_label)
        
        self.channel_input = QSpinBox()
        self.channel_input.setMinimum(1)
        self.channel_input.setMaximum(32)
        self.channel_input.setValue(1)
        channel_layout.addWidget(self.channel_input)
        
        layout.addLayout(channel_layout)
        
        layout.addStretch()
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        start_btn = QPushButton("Запустить класс")
        start_btn.clicked.connect(self._on_start)
        buttons_layout.addWidget(start_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _on_start(self):
        """Обработка нажатия кнопки Запустить"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя преподавателя")
            return
        
        self.teacher_name = name
        self.channel = self.channel_input.value()
        self.accept()


def main():
    """Главная функция"""
    # Настраиваем логирование
    setup_logging("teacher.log")
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Запуск приложения преподавателя")
    logger.info("=" * 60)
    
    # Создаем приложение
    app = QApplication(sys.argv)
    app.setApplicationName("Lingua Classroom - Teacher")
    app.setOrganizationName("Lingua Classroom")
    
    # Показываем диалог входа
    login_dialog = LoginDialog()
    if login_dialog.exec_() != QDialog.Accepted:
        logger.info("Вход отменен пользователем")
        return 0
    
    # Создаем главное окно
    logger.info(f"Запуск класса: {login_dialog.teacher_name}, канал {login_dialog.channel}")
    main_window = TeacherMainWindow(login_dialog.teacher_name, login_dialog.channel)
    main_window.show()
    
    # Запускаем цикл событий
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

