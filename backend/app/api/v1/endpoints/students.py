"""
Students API endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_students():
    """Получить список студентов"""
    return {"students": []}


@router.post("/")
async def create_student():
    """Создать студента"""
    return {"message": "TODO: implement"}



