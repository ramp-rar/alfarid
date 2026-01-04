"""
Интерактивная доска (Whiteboard)
Версия 1.0

Позволяет преподавателю рисовать, писать текст, вставлять изображения
и транслировать содержимое студентам.
"""

import logging
import time
import base64
import json
from typing import Optional, Callable, List, Dict, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QColorDialog, QSlider, QLabel, QFrame, QFileDialog,
    QToolButton, QButtonGroup, QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QImage, 
    QPainterPath, QFont, QCursor
)


logger = logging.getLogger(__name__)


class Tool(Enum):
    """Инструменты доски"""
    PEN = "pen"
    ERASER = "eraser"
    HIGHLIGHTER = "highlighter"
    LINE = "line"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    ARROW = "arrow"
    TEXT = "text"
    SELECT = "select"


@dataclass
class DrawCommand:
    """Команда рисования для синхронизации"""
    tool: str
    color: str  # hex
    width: int
    points: List[Tuple[int, int]]  # Список точек
    text: str = ""  # Для текстовых команд
    font_size: int = 12
    fill: bool = False
    timestamp: float = field(default_factory=time.time)
    command_id: int = 0


class WhiteboardCanvas(QWidget):
    """Холст интерактивной доски"""
    
    # Сигналы
    draw_command = pyqtSignal(dict)  # Команда рисования для синхронизации
    canvas_updated = pyqtSignal()  # Холст обновлен
    
    def __init__(self, parent=None, readonly: bool = False):
        super().__init__(parent)
        
        self.readonly = readonly
        self._command_id = 0
        
        # Настройки инструмента
        self.current_tool = Tool.PEN
        self.current_color = QColor(0, 0, 0)  # Черный
        self.pen_width = 3
        self.eraser_width = 20
        self.font_size = 16
        
        # Состояние рисования
        self.drawing = False
        self.last_point = QPoint()
        self.current_points: List[QPoint] = []
        
        # История для отмены (ВАЖНО: инициализировать ДО _init_canvas!)
        self.history: List[QPixmap] = []
        self.max_history = 50
        
        # Буфер холста
        self.canvas_pixmap: QPixmap = None
        self._init_canvas()
        
        # Колбэк для отправки команд
        self.on_command: Optional[Callable[[dict], None]] = None
        
        # Настройка виджета
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        
        logger.info(f"WhiteboardCanvas создан (readonly={readonly})")
    
    def _init_canvas(self, width: int = 1920, height: int = 1080):
        """Инициализировать холст"""
        self.canvas_pixmap = QPixmap(width, height)
        self.canvas_pixmap.fill(Qt.white)
        self._save_history()
    
    def _save_history(self):
        """Сохранить текущее состояние в историю"""
        if len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append(self.canvas_pixmap.copy())
    
    def undo(self):
        """Отменить последнее действие"""
        if len(self.history) > 1:
            self.history.pop()  # Убираем текущее
            self.canvas_pixmap = self.history[-1].copy()
            self.update()
            self.canvas_updated.emit()
    
    def clear(self):
        """Очистить холст"""
        self._save_history()
        self.canvas_pixmap.fill(Qt.white)
        self.update()
        self.canvas_updated.emit()
        
        # Отправляем команду очистки
        if self.on_command:
            self.on_command({'action': 'clear'})
    
    def set_tool(self, tool: Tool):
        """Установить инструмент"""
        self.current_tool = tool
        
        # Обновляем курсор
        if tool == Tool.ERASER:
            self.setCursor(Qt.OpenHandCursor)
        elif tool == Tool.TEXT:
            self.setCursor(Qt.IBeamCursor)
        elif tool == Tool.SELECT:
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)
    
    def set_color(self, color: QColor):
        """Установить цвет"""
        self.current_color = color
    
    def set_pen_width(self, width: int):
        """Установить толщину пера"""
        self.pen_width = max(1, min(50, width))
    
    def paintEvent(self, event):
        """Отрисовка"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Масштабируем холст под размер виджета
        if self.canvas_pixmap:
            scaled = self.canvas_pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # Центрируем
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            
            # Сохраняем смещение для пересчета координат
            self._offset_x = x
            self._offset_y = y
            self._scale = scaled.width() / self.canvas_pixmap.width()
    
    def _widget_to_canvas(self, point: QPoint) -> QPoint:
        """Преобразовать координаты виджета в координаты холста"""
        if not hasattr(self, '_scale') or self._scale == 0:
            return point
        
        x = int((point.x() - self._offset_x) / self._scale)
        y = int((point.y() - self._offset_y) / self._scale)
        
        # Ограничиваем размерами холста
        x = max(0, min(x, self.canvas_pixmap.width() - 1))
        y = max(0, min(y, self.canvas_pixmap.height() - 1))
        
        return QPoint(x, y)
    
    def mousePressEvent(self, event):
        """Начало рисования"""
        if self.readonly or event.button() != Qt.LeftButton:
            return
        
        self.drawing = True
        canvas_point = self._widget_to_canvas(event.pos())
        self.last_point = canvas_point
        self.current_points = [canvas_point]
        
        self._save_history()
    
    def mouseMoveEvent(self, event):
        """Продолжение рисования"""
        if not self.drawing or self.readonly:
            return
        
        canvas_point = self._widget_to_canvas(event.pos())
        self.current_points.append(canvas_point)
        
        # Рисуем на холсте
        painter = QPainter(self.canvas_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_tool == Tool.PEN:
            self._draw_pen(painter, self.last_point, canvas_point)
        elif self.current_tool == Tool.ERASER:
            self._draw_eraser(painter, canvas_point)
        elif self.current_tool == Tool.HIGHLIGHTER:
            self._draw_highlighter(painter, self.last_point, canvas_point)
        
        painter.end()
        
        self.last_point = canvas_point
        self.update()
    
    def mouseReleaseEvent(self, event):
        """Завершение рисования"""
        if not self.drawing or event.button() != Qt.LeftButton:
            return
        
        self.drawing = False
        
        # Для фигур рисуем при отпускании
        if self.current_tool in [Tool.LINE, Tool.RECTANGLE, Tool.ELLIPSE, Tool.ARROW]:
            # Восстанавливаем состояние до начала
            if self.history:
                self.canvas_pixmap = self.history[-1].copy()
            
            painter = QPainter(self.canvas_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            start = self.current_points[0] if self.current_points else self.last_point
            end = self._widget_to_canvas(event.pos())
            
            self._draw_shape(painter, start, end)
            painter.end()
        
        # Отправляем команду
        self._send_draw_command()
        
        self.current_points = []
        self.canvas_updated.emit()
        self.update()
    
    def _draw_pen(self, painter: QPainter, start: QPoint, end: QPoint):
        """Рисование пером"""
        pen = QPen(self.current_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
    
    def _draw_eraser(self, painter: QPainter, point: QPoint):
        """Ластик"""
        pen = QPen(Qt.white, self.eraser_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(point, self.eraser_width // 2, self.eraser_width // 2)
    
    def _draw_highlighter(self, painter: QPainter, start: QPoint, end: QPoint):
        """Маркер (полупрозрачный)"""
        color = QColor(self.current_color)
        color.setAlpha(80)
        pen = QPen(color, self.pen_width * 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
    
    def _draw_shape(self, painter: QPainter, start: QPoint, end: QPoint):
        """Рисование фигур"""
        pen = QPen(self.current_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        
        if self.current_tool == Tool.LINE:
            painter.drawLine(start, end)
        
        elif self.current_tool == Tool.RECTANGLE:
            rect = QRect(start, end).normalized()
            painter.drawRect(rect)
        
        elif self.current_tool == Tool.ELLIPSE:
            rect = QRect(start, end).normalized()
            painter.drawEllipse(rect)
        
        elif self.current_tool == Tool.ARROW:
            self._draw_arrow(painter, start, end)
    
    def _draw_arrow(self, painter: QPainter, start: QPoint, end: QPoint):
        """Рисование стрелки"""
        import math
        
        # Линия
        painter.drawLine(start, end)
        
        # Наконечник
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 15
        
        p1 = QPoint(
            int(end.x() - arrow_size * math.cos(angle - math.pi / 6)),
            int(end.y() - arrow_size * math.sin(angle - math.pi / 6))
        )
        p2 = QPoint(
            int(end.x() - arrow_size * math.cos(angle + math.pi / 6)),
            int(end.y() - arrow_size * math.sin(angle + math.pi / 6))
        )
        
        painter.drawLine(end, p1)
        painter.drawLine(end, p2)
    
    def _send_draw_command(self):
        """Отправить команду рисования"""
        if not self.current_points or not self.on_command:
            return
        
        self._command_id += 1
        
        cmd = DrawCommand(
            tool=self.current_tool.value,
            color=self.current_color.name(),
            width=self.pen_width if self.current_tool != Tool.ERASER else self.eraser_width,
            points=[(p.x(), p.y()) for p in self.current_points],
            command_id=self._command_id
        )
        
        self.on_command(asdict(cmd))
    
    def apply_command(self, cmd_data: dict):
        """Применить полученную команду (для readonly режима)"""
        try:
            if cmd_data.get('action') == 'clear':
                self.canvas_pixmap.fill(Qt.white)
                self.update()
                return
            
            tool_name = cmd_data.get('tool', 'pen')
            color = QColor(cmd_data.get('color', '#000000'))
            width = cmd_data.get('width', 3)
            points = cmd_data.get('points', [])
            
            if len(points) < 1:
                return
            
            painter = QPainter(self.canvas_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            
            if tool_name == 'eraser':
                painter.setPen(QPen(Qt.white, width))
                painter.setBrush(QBrush(Qt.white))
                for x, y in points:
                    painter.drawEllipse(QPoint(x, y), width // 2, width // 2)
            
            elif tool_name == 'highlighter':
                hl_color = QColor(color)
                hl_color.setAlpha(80)
                painter.setPen(QPen(hl_color, width * 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                for i in range(1, len(points)):
                    painter.drawLine(QPoint(*points[i-1]), QPoint(*points[i]))
            
            elif tool_name in ['line', 'rectangle', 'ellipse', 'arrow']:
                if len(points) >= 2:
                    start = QPoint(*points[0])
                    end = QPoint(*points[-1])
                    
                    if tool_name == 'line':
                        painter.drawLine(start, end)
                    elif tool_name == 'rectangle':
                        painter.drawRect(QRect(start, end).normalized())
                    elif tool_name == 'ellipse':
                        painter.drawEllipse(QRect(start, end).normalized())
                    elif tool_name == 'arrow':
                        self._draw_arrow(painter, start, end)
            
            else:  # pen
                for i in range(1, len(points)):
                    painter.drawLine(QPoint(*points[i-1]), QPoint(*points[i]))
            
            painter.end()
            self.update()
            
        except Exception as e:
            logger.error(f"Ошибка применения команды: {e}")
    
    def get_image_data(self) -> str:
        """Получить данные изображения в base64"""
        buffer = self.canvas_pixmap.toImage()
        
        # Конвертируем в PNG
        from PyQt5.QtCore import QBuffer, QIODevice
        byte_array = QBuffer()
        byte_array.open(QIODevice.WriteOnly)
        buffer.save(byte_array, 'PNG')
        
        return base64.b64encode(byte_array.data()).decode('ascii')
    
    def load_image_data(self, data: str):
        """Загрузить изображение из base64"""
        try:
            image_bytes = base64.b64decode(data)
            image = QImage()
            image.loadFromData(image_bytes)
            
            if not image.isNull():
                self.canvas_pixmap = QPixmap.fromImage(image)
                self.update()
                
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")


class WhiteboardToolbar(QFrame):
    """Панель инструментов доски"""
    
    tool_changed = pyqtSignal(Tool)
    color_changed = pyqtSignal(QColor)
    width_changed = pyqtSignal(int)
    clear_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Создать UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Группа инструментов
        self.tool_group = QButtonGroup(self)
        
        tools = [
            (Tool.PEN, "✏️", "Карандаш"),
            (Tool.HIGHLIGHTER, "🖍️", "Маркер"),
            (Tool.ERASER, "🧹", "Ластик"),
            (Tool.LINE, "📏", "Линия"),
            (Tool.RECTANGLE, "⬜", "Прямоугольник"),
            (Tool.ELLIPSE, "⭕", "Овал"),
            (Tool.ARROW, "➡️", "Стрелка"),
        ]
        
        for tool, icon, tooltip in tools:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet("QToolButton { font-size: 16pt; }")
            btn.clicked.connect(lambda checked, t=tool: self._on_tool_selected(t))
            self.tool_group.addButton(btn)
            layout.addWidget(btn)
            
            if tool == Tool.PEN:
                btn.setChecked(True)
        
        layout.addSpacing(16)
        
        # Выбор цвета
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(36, 36)
        self.color_btn.setToolTip("Цвет")
        self._set_button_color(QColor(0, 0, 0))
        self.color_btn.clicked.connect(self._choose_color)
        layout.addWidget(self.color_btn)
        
        # Быстрые цвета
        quick_colors = ["#000000", "#FF0000", "#00AA00", "#0000FF", "#FF8800", "#8800FF"]
        for color_hex in quick_colors:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background: {color_hex}; border: 1px solid #888; border-radius: 4px;")
            btn.clicked.connect(lambda checked, c=color_hex: self._set_color(QColor(c)))
            layout.addWidget(btn)
        
        layout.addSpacing(16)
        
        # Толщина линии
        layout.addWidget(QLabel("Толщина:"))
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 20)
        self.width_slider.setValue(3)
        self.width_slider.setFixedWidth(80)
        self.width_slider.valueChanged.connect(lambda v: self.width_changed.emit(v))
        layout.addWidget(self.width_slider)
        
        self.width_label = QLabel("3")
        self.width_slider.valueChanged.connect(lambda v: self.width_label.setText(str(v)))
        layout.addWidget(self.width_label)
        
        layout.addStretch()
        
        # Отмена
        undo_btn = QPushButton("↩️ Отменить")
        undo_btn.clicked.connect(self.undo_requested.emit)
        layout.addWidget(undo_btn)
        
        # Очистка
        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(self.clear_requested.emit)
        layout.addWidget(clear_btn)
    
    def _on_tool_selected(self, tool: Tool):
        """Выбран инструмент"""
        self.tool_changed.emit(tool)
    
    def _choose_color(self):
        """Открыть диалог выбора цвета"""
        color = QColorDialog.getColor()
        if color.isValid():
            self._set_color(color)
    
    def _set_color(self, color: QColor):
        """Установить цвет"""
        self._set_button_color(color)
        self.color_changed.emit(color)
    
    def _set_button_color(self, color: QColor):
        """Обновить цвет кнопки"""
        self.color_btn.setStyleSheet(
            f"background: {color.name()}; border: 2px solid #666; border-radius: 4px;"
        )


class WhiteboardWidget(QWidget):
    """Полный виджет интерактивной доски"""
    
    draw_command = pyqtSignal(dict)
    
    def __init__(self, readonly: bool = False, parent=None):
        super().__init__(parent)
        self.readonly = readonly
        self._init_ui()
    
    def _init_ui(self):
        """Создать UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Панель инструментов (только для редактирования)
        if not self.readonly:
            self.toolbar = WhiteboardToolbar()
            self.toolbar.tool_changed.connect(self._on_tool_changed)
            self.toolbar.color_changed.connect(self._on_color_changed)
            self.toolbar.width_changed.connect(self._on_width_changed)
            self.toolbar.clear_requested.connect(self._on_clear)
            self.toolbar.undo_requested.connect(self._on_undo)
            layout.addWidget(self.toolbar)
        
        # Холст
        self.canvas = WhiteboardCanvas(readonly=self.readonly)
        self.canvas.on_command = self._on_canvas_command
        layout.addWidget(self.canvas)
    
    def _on_tool_changed(self, tool: Tool):
        self.canvas.set_tool(tool)
    
    def _on_color_changed(self, color: QColor):
        self.canvas.set_color(color)
    
    def _on_width_changed(self, width: int):
        self.canvas.set_pen_width(width)
    
    def _on_clear(self):
        self.canvas.clear()
    
    def _on_undo(self):
        self.canvas.undo()
    
    def _on_canvas_command(self, cmd: dict):
        """Команда с холста"""
        self.draw_command.emit(cmd)
    
    def apply_command(self, cmd: dict):
        """Применить команду (для readonly)"""
        self.canvas.apply_command(cmd)
    
    def get_image_data(self) -> str:
        """Получить изображение"""
        return self.canvas.get_image_data()
    
    def load_image_data(self, data: str):
        """Загрузить изображение"""
        self.canvas.load_image_data(data)


# Для тестирования
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    logging.basicConfig(level=logging.DEBUG)
    
    app = QApplication(sys.argv)
    
    # Тест виджета доски
    whiteboard = WhiteboardWidget(readonly=False)
    whiteboard.setWindowTitle("Интерактивная доска - Тест")
    whiteboard.resize(1024, 768)
    
    def on_command(cmd):
        print(f"Команда: {cmd}")
    
    whiteboard.draw_command.connect(on_command)
    
    whiteboard.show()
    sys.exit(app.exec_())

