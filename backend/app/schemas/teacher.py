"""
Pydantic schemas для Teacher
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# Shared properties
class TeacherBase(BaseModel):
    """Базовая схема"""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    department: str | None = None
    is_active: bool = True


# Create schema
class TeacherCreate(TeacherBase):
    """Создание преподавателя"""
    password: str = Field(..., min_length=8)


# Update schema
class TeacherUpdate(BaseModel):
    """Обновление преподавателя"""
    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=2, max_length=255)
    department: str | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8)


# Response schema
class Teacher(TeacherBase):
    """Преподаватель (для API ответов)"""
    id: uuid.UUID
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True  # Для SQLAlchemy моделей
    }


# Login schema
class TeacherLogin(BaseModel):
    """Вход преподавателя"""
    email: EmailStr
    password: str


# Token schema
class Token(BaseModel):
    """JWT токен"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Данные из токена"""
    teacher_id: uuid.UUID | None = None



