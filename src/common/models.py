"""
Модели данных
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


@dataclass
class Student:
    """Модель студента"""
    id: str
    name: str
    ip_address: str
    status: str = "offline"
    group_id: Optional[str] = None
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "status": self.status,
            "group_id": self.group_id,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Student':
        """Создать из словаря"""
        last_seen = None
        if data.get("last_seen"):
            last_seen = datetime.fromisoformat(data["last_seen"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            ip_address=data["ip_address"],
            status=data.get("status", "offline"),
            group_id=data.get("group_id"),
            last_seen=last_seen,
            metadata=data.get("metadata", {})
        )


@dataclass
class Teacher:
    """Модель преподавателя"""
    id: str
    name: str
    ip_address: str
    channel: int = 1
    port: int = 9999
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "channel": self.channel,
            "port": self.port
        }


@dataclass
class Group:
    """Модель группы студентов"""
    id: str
    name: str
    leader_id: Optional[str] = None
    student_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "leader_id": self.leader_id,
            "student_ids": self.student_ids,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ChatMessage:
    """Модель сообщения чата"""
    id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    recipient_id: Optional[str] = None  # None = всем
    group_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "recipient_id": self.recipient_id,
            "group_id": self.group_id
        }


class QuestionType(Enum):
    """Типы вопросов"""
    MULTIPLE_CHOICE = "multiple_choice"  # Множественный выбор
    TRUE_FALSE = "true_false"            # Верно/Неверно
    OPEN_ENDED = "open_ended"            # Открытый вопрос
    FILL_BLANK = "fill_blank"            # Заполнить пропуски


@dataclass
class Question:
    """Модель вопроса"""
    id: str
    text: str
    question_type: QuestionType
    options: List[str] = field(default_factory=list)
    correct_answers: List[str] = field(default_factory=list)
    points: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "text": self.text,
            "question_type": self.question_type.value,
            "options": self.options,
            "correct_answers": self.correct_answers,
            "points": self.points
        }


@dataclass
class Exam:
    """Модель экзамена"""
    id: str
    title: str
    questions: List[Question]
    duration_minutes: int = 60
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "questions": [q.to_dict() for q in self.questions],
            "duration_minutes": self.duration_minutes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ExamResult:
    """Модель результата экзамена"""
    id: str
    exam_id: str
    student_id: str
    answers: Dict[str, Any]
    score: float = 0.0
    max_score: float = 0.0
    submitted_at: Optional[datetime] = None
    checked: bool = False
    comments: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "answers": self.answers,
            "score": self.score,
            "max_score": self.max_score,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "checked": self.checked,
            "comments": self.comments
        }


@dataclass
class FileTransfer:
    """Модель передачи файла"""
    id: str
    filename: str
    filesize: int
    sender_id: str
    recipient_ids: List[str]
    progress: float = 0.0
    completed: bool = False
    started_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "filename": self.filename,
            "filesize": self.filesize,
            "sender_id": self.sender_id,
            "recipient_ids": self.recipient_ids,
            "progress": self.progress,
            "completed": self.completed,
            "started_at": self.started_at.isoformat()
        }


@dataclass
class AudioCourse:
    """Модель аудиокурса"""
    id: str
    title: str
    audio_file: str
    duration: float
    segments: List[Dict[str, Any]] = field(default_factory=list)
    subtitles: List[Dict[str, Any]] = field(default_factory=list)
    bookmarks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "audio_file": self.audio_file,
            "duration": self.duration,
            "segments": self.segments,
            "subtitles": self.subtitles,
            "bookmarks": self.bookmarks,
            "created_at": self.created_at.isoformat()
        }

