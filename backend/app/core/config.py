"""
Core configuration для Alfarid Backend
Использует pydantic-settings для валидации
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, field_validator


class Settings(BaseSettings):
    """Конфигурация приложения"""
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Alfarid Backend API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "alfarid"
    POSTGRES_PASSWORD: str = "alfarid_secure_pass"
    POSTGRES_DB: str = "alfarid_db"
    POSTGRES_PORT: int = 5432
    
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values) -> str:
        if isinstance(v, str):
            return v
        
        # Собираем URL из компонентов
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.data.get("POSTGRES_USER"),
            password=values.data.get("POSTGRES_PASSWORD"),
            host=values.data.get("POSTGRES_SERVER"),
            port=values.data.get("POSTGRES_PORT"),
            path=f"{values.data.get('POSTGRES_DB') or ''}",
        )
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React admin
        "http://localhost:8080",
    ]
    
    # File Storage
    RECORDINGS_PATH: str = "./storage/recordings"
    FILES_PATH: str = "./storage/files"
    UPLOADS_PATH: str = "./storage/uploads"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500 MB
    
    # Performance
    MAX_CONCURRENT_LESSONS: int = 50
    MAX_STUDENTS_PER_LESSON: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()



