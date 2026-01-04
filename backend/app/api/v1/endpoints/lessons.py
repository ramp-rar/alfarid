"""
Lessons API endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_lessons():
    """Получить список уроков"""
    return {"lessons": []}


@router.post("/")
async def create_lesson():
    """Создать урок"""
    return {"message": "TODO: implement"}



