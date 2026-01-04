# Alfarid — Архитектура Production-Ready системы

## Принципы разработки (Senior Level)

### 🏗️ **Архитектурные принципы:**
1. **SOLID** — каждый модуль одна ответственность
2. **DRY** — не повторяться
3. **Clean Code** — понятные названия, короткие функции
4. **Separation of Concerns** — разделение логики
5. **Scalability** — готовность к росту

### 📁 **Новая структура проекта:**

```
alfarid/
├── alfarid-desktop/          # Desktop приложения (учитель + студент)
│   ├── src/
│   │   ├── core/             # Ядро системы
│   │   │   ├── config/       # Конфигурация
│   │   │   ├── utils/        # Утилиты
│   │   │   ├── constants/    # Константы
│   │   │   └── exceptions/   # Исключения
│   │   │
│   │   ├── domain/           # Бизнес-логика (Clean Architecture)
│   │   │   ├── models/       # Модели данных
│   │   │   ├── services/     # Сервисы
│   │   │   └── repositories/ # Репозитории
│   │   │
│   │   ├── infrastructure/   # Инфраструктура
│   │   │   ├── network/      # Сетевой слой
│   │   │   ├── storage/      # Хранилище
│   │   │   ├── streaming/    # Стриминг
│   │   │   └── recording/    # Запись
│   │   │
│   │   ├── application/      # Слой приложения
│   │   │   ├── teacher/      # UI учителя
│   │   │   ├── student/      # UI студента
│   │   │   └── shared/       # Общие компоненты
│   │   │
│   │   └── tests/            # Тесты
│   │       ├── unit/
│   │       ├── integration/
│   │       └── e2e/
│   │
│   ├── requirements/         # Зависимости
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   │
│   └── scripts/              # Скрипты сборки
│       ├── build.py
│       └── package.py
│
├── alfarid-backend/          # Backend сервер (FastAPI)
│   ├── app/
│   │   ├── api/              # REST API endpoints
│   │   │   ├── v1/
│   │   │   │   ├── teachers.py
│   │   │   │   ├── students.py
│   │   │   │   ├── classes.py
│   │   │   │   ├── lessons.py
│   │   │   │   └── recordings.py
│   │   │   └── deps.py       # Dependencies
│   │   │
│   │   ├── core/             # Конфигурация
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   │
│   │   ├── models/           # SQLAlchemy модели
│   │   │   ├── teacher.py
│   │   │   ├── student.py
│   │   │   ├── lesson.py
│   │   │   └── recording.py
│   │   │
│   │   ├── schemas/          # Pydantic схемы
│   │   │   ├── teacher.py
│   │   │   ├── student.py
│   │   │   └── lesson.py
│   │   │
│   │   ├── services/         # Бизнес-логика
│   │   │   ├── teacher_service.py
│   │   │   ├── student_service.py
│   │   │   ├── lesson_service.py
│   │   │   └── recording_service.py
│   │   │
│   │   ├── repositories/     # Работа с БД
│   │   │   ├── base.py
│   │   │   ├── teacher_repo.py
│   │   │   └── student_repo.py
│   │   │
│   │   └── utils/            # Утилиты
│   │       ├── validators.py
│   │       └── helpers.py
│   │
│   ├── migrations/           # Alembic миграции
│   ├── tests/
│   └── requirements.txt
│
├── alfarid-admin/            # Админ-панель (React)
│   ├── src/
│   │   ├── components/       # React компоненты
│   │   │   ├── Teachers/
│   │   │   ├── Students/
│   │   │   ├── Classes/
│   │   │   └── Dashboard/
│   │   │
│   │   ├── pages/            # Страницы
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Teachers.tsx
│   │   │   ├── Students.tsx
│   │   │   └── Settings.tsx
│   │   │
│   │   ├── services/         # API клиенты
│   │   │   └── api.ts
│   │   │
│   │   ├── store/            # State management (Redux/Zustand)
│   │   └── utils/
│   │
│   └── package.json
│
├── alfarid-storage/          # Хранилище данных
│   ├── recordings/           # Записи уроков
│   │   └── [teacher_id]/
│   │       └── [lesson_id]/
│   │           ├── metadata.json
│   │           ├── screen/
│   │           ├── audio/
│   │           └── events/
│   │
│   ├── files/                # Файлы от учителей
│   └── uploads/              # Загрузки студентов
│
└── docs/                     # Документация
    ├── API.md
    ├── DEPLOYMENT.md
    └── USER_GUIDE.md
```

## 🗄️ **Схема базы данных (PostgreSQL)**

```sql
-- teachers (Учителя)
CREATE TABLE teachers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- students (Студенты)
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    class_id UUID REFERENCES classes(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- classes (Классы/Группы)
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    teacher_id UUID REFERENCES teachers(id),
    description TEXT,
    max_students INTEGER DEFAULT 50,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- lessons (Уроки)
CREATE TABLE lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID REFERENCES classes(id),
    teacher_id UUID REFERENCES teachers(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'scheduled', -- scheduled, active, completed, cancelled
    
    -- Настройки качества
    quality_profile VARCHAR(50) DEFAULT 'medium',
    max_fps INTEGER DEFAULT 24,
    
    -- Статистика
    student_count INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- lesson_recordings (Записи уроков)
CREATE TABLE lesson_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES lessons(id),
    storage_path VARCHAR(500) NOT NULL,
    
    -- Метаданные
    duration_seconds INTEGER,
    file_size_mb DECIMAL(10,2),
    frame_count INTEGER,
    
    -- Статус обработки
    status VARCHAR(50) DEFAULT 'processing', -- processing, ready, failed
    is_public BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- lesson_attendance (Посещаемость)
CREATE TABLE lesson_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES lessons(id),
    student_id UUID REFERENCES students(id),
    
    joined_at TIMESTAMP,
    left_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Активность
    hand_raised_count INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    
    UNIQUE(lesson_id, student_id)
);

-- lesson_events (События урока)
CREATE TABLE lesson_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES lessons(id),
    student_id UUID REFERENCES students(id),
    
    event_type VARCHAR(100) NOT NULL, -- hand_raised, message, poll_answer, etc.
    event_data JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- settings (Настройки системы)
CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для производительности
CREATE INDEX idx_lessons_teacher ON lessons(teacher_id);
CREATE INDEX idx_lessons_class ON lessons(class_id);
CREATE INDEX idx_lessons_status ON lessons(status);
CREATE INDEX idx_attendance_lesson ON lesson_attendance(lesson_id);
CREATE INDEX idx_events_lesson ON lesson_events(lesson_id);
CREATE INDEX idx_events_type ON lesson_events(event_type);
```

## 🚀 **Оптимизация производительности**

### **1. Multicast для трансляции (вместо TCP для каждого)**

```python
# alfarid-desktop/src/infrastructure/network/multicast_manager.py

import socket
import struct
import logging
from typing import Optional
from threading import Thread, Event

logger = logging.getLogger(__name__)


class MulticastSender:
    """
    Отправка данных через UDP multicast.
    Один пакет = все студенты получают.
    
    Производительность:
    - 1 студент: 10 Mbps
    - 30 студентов: 10 Mbps (не 300 Mbps!)
    """
    
    def __init__(self, group: str = "239.0.1.1", port: int = 5005):
        self.group = group
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._setup_socket()
    
    def _setup_socket(self):
        """Настройка multicast сокета"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
            
            # Увеличиваем буфер для больших пакетов
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
            
            logger.info(f"Multicast sender готов: {self.group}:{self.port}")
        except Exception as e:
            logger.error(f"Ошибка настройки multicast: {e}")
            raise
    
    def send(self, data: bytes) -> bool:
        """Отправка данных всем подписчикам"""
        try:
            self.sock.sendto(data, (self.group, self.port))
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки multicast: {e}")
            return False
    
    def close(self):
        if self.sock:
            self.sock.close()


class MulticastReceiver:
    """
    Приём multicast данных (студент)
    """
    
    def __init__(self, group: str = "239.0.1.1", port: int = 5005):
        self.group = group
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.running = Event()
        self.thread: Optional[Thread] = None
        
        # Callback для обработки данных
        self.on_data_received = None
    
    def start(self):
        """Начать приём"""
        self._setup_socket()
        self.running.set()
        self.thread = Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        logger.info("Multicast receiver запущен")
    
    def _setup_socket(self):
        """Настройка приёма multicast"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind на порт
        self.sock.bind(('', self.port))
        
        # Подписка на multicast группу
        mreq = struct.pack("4sl", socket.inet_aton(self.group), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Увеличиваем буфер приёма
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    
    def _receive_loop(self):
        """Цикл приёма данных"""
        while self.running.is_set():
            try:
                data, addr = self.sock.recvfrom(65536)
                
                if self.on_data_received:
                    self.on_data_received(data)
                    
            except Exception as e:
                if self.running.is_set():
                    logger.error(f"Ошибка приёма multicast: {e}")
    
    def stop(self):
        """Остановить приём"""
        self.running.clear()
        if self.sock:
            self.sock.close()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Multicast receiver остановлен")
```

### **2. Адаптивное качество по количеству студентов**

```python
# alfarid-desktop/src/core/config/performance_manager.py

from dataclasses import dataclass
from typing import Literal

QualityProfile = Literal["small", "medium", "large"]


@dataclass
class PerformanceProfile:
    """Профиль производительности"""
    name: QualityProfile
    max_students: int
    screen_fps: int
    screen_quality: int  # JPEG quality 1-100
    audio_sample_rate: int
    enable_webcam: bool
    enable_whiteboard: bool


class PerformanceManager:
    """
    Автоматическое управление качеством на основе количества студентов.
    
    Цель: стабильная работа без задержек.
    """
    
    PROFILES = {
        "small": PerformanceProfile(
            name="small",
            max_students=10,
            screen_fps=30,
            screen_quality=85,
            audio_sample_rate=48000,
            enable_webcam=True,
            enable_whiteboard=True
        ),
        "medium": PerformanceProfile(
            name="medium",
            max_students=25,
            screen_fps=24,
            screen_quality=70,
            audio_sample_rate=44100,
            enable_webcam=True,
            enable_whiteboard=True
        ),
        "large": PerformanceProfile(
            name="large",
            max_students=50,
            screen_fps=15,
            screen_quality=60,
            audio_sample_rate=32000,
            enable_webcam=False,  # Отключаем для экономии
            enable_whiteboard=True
        )
    }
    
    @classmethod
    def get_profile(cls, student_count: int) -> PerformanceProfile:
        """Получить оптимальный профиль для количества студентов"""
        if student_count <= 10:
            return cls.PROFILES["small"]
        elif student_count <= 25:
            return cls.PROFILES["medium"]
        else:
            return cls.PROFILES["large"]
    
    @classmethod
    def calculate_bandwidth(cls, profile: PerformanceProfile) -> dict:
        """
        Рассчитать требуемую пропускную способность.
        
        Returns:
            dict: {"upload_mbps": float, "download_per_student_mbps": float}
        """
        # Средний размер JPEG кадра в зависимости от качества
        frame_size_kb = {
            60: 50,   # ~50 KB на кадр
            70: 70,   # ~70 KB
            85: 100   # ~100 KB
        }.get(profile.screen_quality, 70)
        
        # Трафик экрана в секунду
        screen_mbps = (frame_size_kb * profile.screen_fps * 8) / 1000
        
        # Аудио трафик (примерно)
        audio_mbps = (profile.audio_sample_rate * 2 * 8) / 1_000_000  # 2 байта на сэмпл
        
        total_upload = screen_mbps + audio_mbps
        
        return {
            "upload_mbps": round(total_upload, 2),
            "download_per_student_mbps": round(total_upload, 2),
            "total_students": profile.max_students,
            "estimated_total_mbps": round(total_upload, 2)  # С multicast не растёт!
        }
```

## 📊 **Следующие шаги (приоритет):**

Хотите я начну с:

1. **Фаза 4.1**: Создать Backend (FastAPI) + Database схему?
2. **Фаза 4.2**: Реализовать Multicast для оптимизации?
3. **Фаза 4.3**: Добавить модуль записи уроков?
4. **Фаза 4.4**: Создать админ-панель (React)?

**Или пойдём по порядку — сначала Backend + DB?**

Скажите, с чего начинаем? 🚀



