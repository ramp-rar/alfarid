"""
Models package
Экспортируем все модели для удобного импорта
"""

from app.models.teacher import Teacher
from app.models.student import Student
from app.models.class_ import Class
from app.models.lesson import (
    Lesson,
    LessonRecording,
    LessonAttendance,
    LessonEvent,
    LessonStatus,
    RecordingStatus,
)

__all__ = [
    "Teacher",
    "Student",
    "Class",
    "Lesson",
    "LessonRecording",
    "LessonAttendance",
    "LessonEvent",
    "LessonStatus",
    "RecordingStatus",
]



