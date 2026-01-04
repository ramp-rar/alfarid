"""
Lesson and related models
"""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class LessonStatus(str, enum.Enum):
    """Статус урока"""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecordingStatus(str, enum.Enum):
    """Статус записи"""
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Lesson(Base):
    """Модель урока"""
    
    __tablename__ = "lessons"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    
    # References
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    
    # Info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Schedule
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Status
    status: Mapped[LessonStatus] = mapped_column(
        SQLEnum(LessonStatus),
        default=LessonStatus.SCHEDULED,
        index=True
    )
    
    # Quality settings
    quality_profile: Mapped[str] = mapped_column(String(50), default="medium")
    max_fps: Mapped[int] = mapped_column(Integer, default=24)
    
    # Stats
    student_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="lessons")
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="lessons")
    recordings: Mapped[list["LessonRecording"]] = relationship(
        "LessonRecording",
        back_populates="lesson",
        cascade="all, delete-orphan"
    )
    attendance: Mapped[list["LessonAttendance"]] = relationship(
        "LessonAttendance",
        back_populates="lesson",
        cascade="all, delete-orphan"
    )
    events: Mapped[list["LessonEvent"]] = relationship(
        "LessonEvent",
        back_populates="lesson",
        cascade="all, delete-orphan"
    )


class LessonRecording(Base):
    """Запись урока"""
    
    __tablename__ = "lesson_recordings"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    
    # Storage
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Metadata
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    file_size_mb: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2))
    frame_count: Mapped[int | None] = mapped_column(Integer)
    
    # Status
    status: Mapped[RecordingStatus] = mapped_column(
        SQLEnum(RecordingStatus),
        default=RecordingStatus.PROCESSING
    )
    is_public: Mapped[bool] = mapped_column(default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Relationships
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="recordings")


class LessonAttendance(Base):
    """Посещаемость урока"""
    
    __tablename__ = "lesson_attendance"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    
    # Timing
    joined_at: Mapped[datetime | None] = mapped_column(DateTime)
    left_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    
    # Activity
    hand_raised_count: Mapped[int] = mapped_column(Integer, default=0)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="attendance")
    student: Mapped["Student"] = relationship("Student", back_populates="attendance")


class LessonEvent(Base):
    """События урока"""
    
    __tablename__ = "lesson_events"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"))
    
    # Event
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(JSON)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="events")
    student: Mapped["Student | None"] = relationship("Student", back_populates="events")



