"""
API v1 router
Объединяет все endpoint'ы
"""

from fastapi import APIRouter
from app.api.v1.endpoints import teachers, students, classes, lessons, recordings, admin

api_router = APIRouter()

# Include все routers
api_router.include_router(teachers.router, prefix="/teachers", tags=["teachers"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(lessons.router, prefix="/lessons", tags=["lessons"])
api_router.include_router(recordings.router, prefix="/recordings", tags=["recordings"])

# Admin panel (без /api/v1 префикса, прямо на /admin)
admin_router = APIRouter()
admin_router.include_router(admin.router, prefix="/admin", tags=["admin"])

