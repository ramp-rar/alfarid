# Alfarid Backend API

FastAPI backend для системы удалённого обучения Alfarid.

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка PostgreSQL

```bash
# Создать базу данных
createdb alfarid_db

# Или через psql
psql -U postgres
CREATE DATABASE alfarid_db;
CREATE USER alfarid WITH PASSWORD 'alfarid_secure_pass';
GRANT ALL PRIVILEGES ON DATABASE alfarid_db TO alfarid;
```

### 3. Настройка окружения

```bash
# Скопировать пример
copy .env.example .env

# Отредактировать .env с вашими настройками
```

### 4. Запуск сервера

```bash
# Development режим
python -m app.main

# Или через uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API документация

После запуска доступна по адресам:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

## 🏗️ Структура проекта

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Конфигурация, БД, безопасность
│   ├── models/          # SQLAlchemy модели
│   ├── schemas/         # Pydantic схемы
│   ├── services/        # Бизнес-логика
│   ├── repositories/    # Работа с БД
│   └── main.py          # FastAPI app
├── migrations/          # Alembic миграции
├── tests/              # Тесты
└── requirements.txt
```

## 🔧 Разработка

### Создание миграции

```bash
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

### Тестирование

```bash
pytest
```

## 📊 Основные endpoints

### Teachers (Преподаватели)
- `GET /api/v1/teachers` - Список преподавателей
- `POST /api/v1/teachers` - Создать преподавателя
- `GET /api/v1/teachers/{id}` - Получить преподавателя
- `PUT /api/v1/teachers/{id}` - Обновить преподавателя
- `DELETE /api/v1/teachers/{id}` - Удалить преподавателя

### Students (Студенты)
- `GET /api/v1/students` - Список студентов
- `POST /api/v1/students` - Создать студента

### Classes (Классы)
- `GET /api/v1/classes` - Список классов
- `POST /api/v1/classes` - Создать класс

### Lessons (Уроки)
- `GET /api/v1/lessons` - Список уроков
- `POST /api/v1/lessons` - Создать урок

### Recordings (Записи)
- `GET /api/v1/recordings` - Список записей
- `GET /api/v1/recordings/{id}` - Получить запись

## 🔐 Безопасность

- JWT токены для аутентификации
- Bcrypt для хеширования паролей
- CORS настроен через переменные окружения

## 📦 Деплой

### Docker

```dockerfile
# Dockerfile уже создан
docker build -t alfarid-backend .
docker run -p 8000:8000 alfarid-backend
```

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```



