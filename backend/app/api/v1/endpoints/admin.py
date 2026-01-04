"""
Admin panel endpoints
Простая админ-панель на Jinja2 templates
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Teacher, Student, Lesson, Class

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Главная страница админ-панели.
    
    Показывает статистику:
    - Количество учителей
    - Количество студентов
    - Активных уроков
    - Записей уроков
    """
    # Статистика
    teachers_count = await db.scalar(select(func.count()).select_from(Teacher))
    students_count = await db.scalar(select(func.count()).select_from(Student))
    lessons_count = await db.scalar(select(func.count()).select_from(Lesson))
    classes_count = await db.scalar(select(func.count()).select_from(Class))
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "teachers_count": teachers_count or 0,
        "students_count": students_count or 0,
        "lessons_count": lessons_count or 0,
        "classes_count": classes_count or 0,
    })


@router.get("/teachers", response_class=HTMLResponse)
async def admin_teachers(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Список преподавателей"""
    result = await db.execute(
        select(Teacher).order_by(Teacher.created_at.desc())
    )
    teachers = result.scalars().all()
    
    return templates.TemplateResponse("teachers.html", {
        "request": request,
        "teachers": teachers
    })


@router.get("/students", response_class=HTMLResponse)
async def admin_students(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Список студентов"""
    result = await db.execute(
        select(Student).order_by(Student.created_at.desc())
    )
    students = result.scalars().all()
    
    return templates.TemplateResponse("students.html", {
        "request": request,
        "students": students
    })


@router.get("/lessons", response_class=HTMLResponse)
async def admin_lessons(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Список уроков"""
    result = await db.execute(
        select(Lesson).order_by(Lesson.start_time.desc())
    )
    lessons = result.scalars().all()
    
    return templates.TemplateResponse("lessons.html", {
        "request": request,
        "lessons": lessons
    })



