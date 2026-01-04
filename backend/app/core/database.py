"""
Database connection и session management
Async SQLAlchemy для производительности
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Создаём async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=20,  # Для высокой нагрузки
    max_overflow=40,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base class для моделей
class Base(DeclarativeBase):
    """Base class для всех моделей"""
    pass


# Dependency для получения DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI endpoints.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Инициализация БД
async def init_db():
    """Создать все таблицы"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Закрытие соединения
async def close_db():
    """Закрыть все соединения"""
    await engine.dispose()



