"""
Утилиты общего назначения
"""

import os
import sys
import json
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Any, Dict, Optional
import configparser


def get_app_dir() -> str:
    """Получить директорию приложения"""
    if getattr(sys, 'frozen', False):
        # Если запущено из exe
        return os.path.dirname(sys.executable)
    else:
        # Если запущено из исходников
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ensure_dir(directory: str) -> None:
    """Убедиться что директория существует, создать если нет"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_config_path() -> str:
    """Получить путь к конфигурационному файлу"""
    return os.path.join(get_app_dir(), "config.ini")


def load_config() -> configparser.ConfigParser:
    """Загрузить конфигурацию"""
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        config.read(config_path, encoding='utf-8')
    
    return config


def save_config(config: configparser.ConfigParser) -> None:
    """Сохранить конфигурацию"""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)


def hash_password(password: str) -> str:
    """Хешировать пароль"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Проверить пароль"""
    return hash_password(password) == hashed


def get_timestamp() -> str:
    """Получить текущую временную метку"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_file_size_str(size_bytes: int) -> str:
    """Преобразовать размер файла в читаемый формат"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def serialize_message(msg_type: str, data: Dict[str, Any]) -> bytes:
    """Сериализовать сообщение в байты"""
    message = {
        "type": msg_type,
        "timestamp": get_timestamp(),
        "data": data
    }
    return json.dumps(message, ensure_ascii=False).encode('utf-8')


def deserialize_message(data: bytes) -> Optional[Dict[str, Any]]:
    """Десериализовать сообщение из байтов"""
    try:
        return json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.error(f"Ошибка десериализации сообщения: {e}")
        return None


def setup_logging(log_file: str = "app.log", level: int = logging.INFO, max_bytes: int = 2_000_000, backups: int = 3) -> None:
    """Настроить логирование с ротацией"""
    log_dir = os.path.join(get_app_dir(), "logs")
    ensure_dir(log_dir)
    log_path = os.path.join(log_dir, log_file)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    file_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [file_handler, stream_handler]


def get_local_ip() -> str:
    """Получить локальный IP адрес"""
    import socket
    try:
        # Создаем UDP сокет
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Не нужно реально подключаться
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def format_duration(seconds: int) -> str:
    """Форматировать длительность в читаемый вид"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def validate_ip(ip: str) -> bool:
    """Проверить валидность IP адреса"""
    import socket
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def get_machine_id() -> str:
    """Получить уникальный ID машины"""
    import uuid
    return str(uuid.getnode())


class Singleton(type):
    """Метакласс для создания синглтонов"""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

