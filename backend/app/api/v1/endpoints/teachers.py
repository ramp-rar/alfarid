"""
Teachers API endpoints
CRUD операции для преподавателей
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Teacher
from app.schemas.teacher import (
    Teacher as TeacherSchema,
    TeacherCreate,
    TeacherUpdate,
)
from app.core.security import get_password_hash

router = APIRouter()


@router.get("/", response_model=List[TeacherSchema])
async def get_teachers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех преподавателей.
    
    Поддерживает пагинацию через skip/limit.
    """
    result = await db.execute(
        select(Teacher)
        .offset(skip)
        .limit(limit)
        .order_by(Teacher.created_at.desc())
    )
    teachers = result.scalars().all()
    return teachers


@router.post("/", response_model=TeacherSchema, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    teacher_in: TeacherCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать нового преподавателя.
    
    Email должен быть уникальным.
    """
    # Проверяем уникальность email
    result = await db.execute(
        select(Teacher).where(Teacher.email == teacher_in.email)
    )
    existing_teacher = result.scalar_one_or_none()
    
    if existing_teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )
    
    # Создаём преподавателя
    teacher = Teacher(
        email=teacher_in.email,
        password_hash=get_password_hash(teacher_in.password),
        full_name=teacher_in.full_name,
        department=teacher_in.department,
        is_active=teacher_in.is_active,
    )
    
    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)
    
    return teacher


@router.get("/{teacher_id}", response_model=TeacherSchema)
async def get_teacher(
    teacher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получить преподавателя по ID"""
    result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден"
        )
    
    return teacher


@router.put("/{teacher_id}", response_model=TeacherSchema)
async def update_teacher(
    teacher_id: uuid.UUID,
    teacher_in: TeacherUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить данные преподавателя"""
    result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден"
        )
    
    # Обновляем поля
    update_data = teacher_in.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(teacher, field, value)
    
    await db.commit()
    await db.refresh(teacher)
    
    return teacher


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teacher(
    teacher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Удалить преподавателя"""
    result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден"
        )
    
    await db.delete(teacher)
    await db.commit()
    
    return None



