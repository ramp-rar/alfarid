"""
Окно интерактивной доски для студента (только просмотр)
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal, Qt
from src.whiteboard import WhiteboardWidget


logger = logging.getLogger(__name__)


class StudentWhiteboardWindow(QMainWindow):
    """Окно интерактивной доски студента (readonly)"""
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Создать UI"""
        self.setWindowTitle("📝 Интерактивная доска - Alfarid")
        self.setMinimumSize(800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        header = QLabel("📝 Интерактивная доска преподавателя")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                background: #2d2d44;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                padding: 8px;
            }
        """)
        layout.addWidget(header)
        
        # Виджет доски (readonly)
        self.whiteboard = WhiteboardWidget(readonly=True)
        layout.addWidget(self.whiteboard)
        
        # Нижняя панель
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def apply_command(self, cmd: dict):
        """Применить команду рисования"""
        self.whiteboard.apply_command(cmd)
    
    def sync_canvas(self, image_data: str):
        """Синхронизировать холст с изображением"""
        self.whiteboard.load_image_data(image_data)
    
    def closeEvent(self, event):
        """При закрытии"""
        self.closed.emit()
        event.accept()

