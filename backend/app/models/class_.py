"""
Class model (группа/класс студентов)
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Class(Base):
    """Модель класса/группы"""
    
    __tablename__ = "classes"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    
    # Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Teacher
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    
    # Limits
    max_students: Mapped[int] = mapped_column(Integer, default=50)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="classes")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="class_")
    lessons: Mapped[list["Lesson"]] = relationship("Lesson", back_populates="class_")
    
    def __repr__(self) -> str:
        return f"<Class {self.name}>"



