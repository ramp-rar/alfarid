"""
Модуль интерактивной доски (Whiteboard)
"""

from .whiteboard import (
    WhiteboardWidget,
    WhiteboardCanvas,
    WhiteboardToolbar,
    Tool,
    DrawCommand
)

__all__ = [
    'WhiteboardWidget',
    'WhiteboardCanvas',
    'WhiteboardToolbar',
    'Tool',
    'DrawCommand'
]

