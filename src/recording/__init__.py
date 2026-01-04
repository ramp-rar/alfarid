"""
Модуль записи уроков
"""

from .lesson_recorder import LessonRecorder, RecordingConfig
from .lesson_player import LessonPlayer
from .video_encoder import VideoEncoder

__all__ = [
    'LessonRecorder',
    'RecordingConfig',
    'LessonPlayer',
    'VideoEncoder',
]



