"""
Окно интерактивной доски для преподавателя
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal, QTimer
from src.whiteboard import WhiteboardWidget
from src.common.constants import MessageType


logger = logging.getLogger(__name__)


class TeacherWhiteboardWindow(QMainWindow):
    """Окно интерактивной доски преподавателя"""
    
    closed = pyqtSignal()
    
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        self._sync_timer = None
        self._init_ui()
    
    def _init_ui(self):
        """Создать UI"""
        self.setWindowTitle("📝 Интерактивная доска - Alfarid")
        self.setMinimumSize(1024, 768)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Виджет доски
        self.whiteboard = WhiteboardWidget(readonly=False)
        self.whiteboard.draw_command.connect(self._on_draw_command)
        layout.addWidget(self.whiteboard)
        
        # Нижняя панель
        bottom_layout = QHBoxLayout()
        
        sync_btn = QPushButton("🔄 Синхронизировать сейчас")
        sync_btn.clicked.connect(self._sync_canvas)
        bottom_layout.addWidget(sync_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("❌ Закрыть доску")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
        
        # Таймер автосинхронизации (каждые 5 секунд)
        self._sync_timer = QTimer()
        self._sync_timer.timeout.connect(self._sync_canvas)
        self._sync_timer.start(5000)
    
    def _on_draw_command(self, cmd: dict):
        """Отправить команду рисования студентам"""
        if self.server:
            self.server.broadcast_to_all(MessageType.WHITEBOARD_COMMAND, cmd)
    
    def _sync_canvas(self):
        """Синхронизировать весь холст"""
        if self.server:
            image_data = self.whiteboard.get_image_data()
            self.server.broadcast_to_all(MessageType.WHITEBOARD_SYNC, {
                'image': image_data
            })
            logger.debug("Холст синхронизирован")
    
    def showEvent(self, event):
        """При показе окна"""
        super().showEvent(event)
        
        # Уведомляем студентов о начале
        if self.server:
            self.server.broadcast_to_all(MessageType.WHITEBOARD_START, {})
            logger.info("Доска открыта, студенты уведомлены")
    
    def closeEvent(self, event):
        """При закрытии"""
        if self._sync_timer:
            self._sync_timer.stop()
        
        # Уведомляем студентов о закрытии
        if self.server:
            self.server.broadcast_to_all(MessageType.WHITEBOARD_STOP, {})
        
        self.closed.emit()
        logger.info("Доска закрыта")
        event.accept()

