"""
FastAPI Main Application
Alfarid Backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1 import api_router, admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events для инициализации и очистки"""
    # Startup
    print("🚀 Запуск Alfarid Backend API...")
    await init_db()
    print("✅ База данных инициализирована")
    
    yield
    
    # Shutdown
    print("🔻 Остановка Alfarid Backend API...")
    await close_db()
    print("✅ Соединения с БД закрыты")


# Создаём FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API для системы удалённого обучения Alfarid",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include Admin panel (без префикса)
app.include_router(admin_router)


# Health check
@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "ok",
        "version": settings.VERSION,
        "service": "alfarid-backend"
    }


# Root endpoint
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Alfarid Backend API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

