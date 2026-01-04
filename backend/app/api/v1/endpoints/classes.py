"""
Classes API endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_classes():
    """Получить список классов"""
    return {"classes": []}


@router.post("/")
async def create_class():
    """Создать класс"""
    return {"message": "TODO: implement"}



