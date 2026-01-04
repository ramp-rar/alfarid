"""
Student model
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Student(Base):
    """Модель студента"""
    
    __tablename__ = "students"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Уникальный ID студента (как в desktop app)
    student_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Profile
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    
    # Class assignment
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id", ondelete="SET NULL"))
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    class_: Mapped["Class | None"] = relationship("Class", back_populates="students")
    attendance: Mapped[list["LessonAttendance"]] = relationship(
        "LessonAttendance",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    events: Mapped[list["LessonEvent"]] = relationship(
        "LessonEvent",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Student {self.full_name} ({self.student_id})>"



