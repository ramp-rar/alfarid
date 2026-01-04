"""
Recordings API endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_recordings():
    """Получить список записей"""
    return {"recordings": []}


@router.get("/{recording_id}")
async def get_recording(recording_id: str):
    """Получить запись по ID"""
    return {"recording_id": recording_id}



