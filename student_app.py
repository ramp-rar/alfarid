"""
Главный файл запуска приложения студента
"""

import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
import logging

from src.common.utils import setup_logging
from src.student.main_window import StudentMainWindow


class StudentLoginDialog(QDialog):
    """Диалог входа студента"""
    
    def __init__(self):
        super().__init__()
        self.student_name = None
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Lingua Classroom - Вход студента")
        self.setModal(True)
        self.setFixedSize(400, 180)
        
        layout = QVBoxLayout()
        
        # Заголовок
        title = QLabel("Вход в класс")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Имя студента
        name_label = QLabel("Введите ваше имя:")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Иван Иванов")
        self.name_input.setText("Иван")  # По умолчанию для тестирования
        layout.addWidget(self.name_input)
        
        layout.addStretch()
        
        # Кнопки
        from PyQt5.QtWidgets import QHBoxLayout
        buttons_layout = QHBoxLayout()
        
        connect_btn = QPushButton("Подключиться")
        connect_btn.clicked.connect(self._on_connect)
        buttons_layout.addWidget(connect_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _on_connect(self):
        """Обработка нажатия кнопки Подключиться"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ваше имя")
            return
        
        self.student_name = name
        self.accept()


def main():
    """Главная функция"""
    # Настраиваем логирование
    setup_logging("student.log")
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Запуск приложения студента")
    logger.info("=" * 60)
    
    # Создаем приложение
    app = QApplication(sys.argv)
    app.setApplicationName("Lingua Classroom - Student")
    app.setOrganizationName("Lingua Classroom")
    
    # Показываем диалог входа
    login_dialog = StudentLoginDialog()
    if login_dialog.exec_() != QDialog.Accepted:
        logger.info("Вход отменен пользователем")
        return 0
    
    # Создаем главное окно
    logger.info(f"Вход студента: {login_dialog.student_name}")
    main_window = StudentMainWindow(login_dialog.student_name)
    main_window.show()
    
    # Запускаем цикл событий
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

