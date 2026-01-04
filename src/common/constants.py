"""
Константы приложения
"""

# Версия приложения
APP_VERSION = "1.0.0"
APP_NAME = "Alfarid"

# Сетевые константы
DEFAULT_PORT = 9999
MULTICAST_GROUP = "239.255.255.250"
MULTICAST_PORT = 10000
BROADCAST_INTERVAL = 5  # секунды
HEARTBEAT_INTERVAL = 3  # секунды
CONNECTION_TIMEOUT = 15  # секунды

# Типы сообщений (протокол)
class MessageType:
    # Общие
    PING = "PING"
    PONG = "PONG"
    DISCONNECT = "DISCONNECT"
    
    # Регистрация
    TEACHER_BROADCAST = "TEACHER_BROADCAST"
    STUDENT_CONNECT = "STUDENT_CONNECT"
    STUDENT_INFO = "STUDENT_INFO"
    CONNECTION_ACCEPTED = "CONNECTION_ACCEPTED"
    CONNECTION_REJECTED = "CONNECTION_REJECTED"
    
    # Трансляция
    SCREEN_STREAM_START = "SCREEN_STREAM_START"
    SCREEN_STREAM_STOP = "SCREEN_STREAM_STOP"
    SCREEN_FRAME = "SCREEN_FRAME"
    
    # Видео
    VIDEO_STREAM_START = "VIDEO_STREAM_START"
    VIDEO_STREAM_STOP = "VIDEO_STREAM_STOP"
    VIDEO_FRAME = "VIDEO_FRAME"
    VIDEO_CONTROL = "VIDEO_CONTROL"
    
    # Аудио
    AUDIO_STREAM_START = "AUDIO_STREAM_START"
    AUDIO_STREAM_STOP = "AUDIO_STREAM_STOP"
    AUDIO_FRAME = "AUDIO_FRAME"
    
    # Голосовая связь
    VOICE_START = "VOICE_START"
    VOICE_STOP = "VOICE_STOP"
    VOICE_DATA = "VOICE_DATA"
    
    # Веб-камера
    WEBCAM_START = "WEBCAM_START"
    WEBCAM_STOP = "WEBCAM_STOP"
    WEBCAM_FRAME = "WEBCAM_FRAME"
    
    # Интерактивная доска
    WHITEBOARD_START = "WHITEBOARD_START"
    WHITEBOARD_STOP = "WHITEBOARD_STOP"
    WHITEBOARD_COMMAND = "WHITEBOARD_COMMAND"
    WHITEBOARD_SYNC = "WHITEBOARD_SYNC"  # Синхронизация всего холста
    
    # Чат
    CHAT_MESSAGE = "CHAT_MESSAGE"
    CHAT_GROUP = "CHAT_GROUP"
    
    # Файлы
    FILE_SEND = "FILE_SEND"
    FILE_REQUEST = "FILE_REQUEST"
    FILE_CHUNK = "FILE_CHUNK"
    FILE_COMPLETE = "FILE_COMPLETE"
    
    # Управление
    LOCK_SCREEN = "LOCK_SCREEN"
    UNLOCK_SCREEN = "UNLOCK_SCREEN"
    LOCK_INPUT = "LOCK_INPUT"  # Блокировка клавиатуры/мыши
    UNLOCK_INPUT = "UNLOCK_INPUT"
    BLOCK_APP = "BLOCK_APP"
    UNBLOCK_APP = "UNBLOCK_APP"
    REMOTE_COMMAND = "REMOTE_COMMAND"
    
    # Веб-контроль
    WEB_CONTROL_SET = "WEB_CONTROL_SET"
    WEB_CONTROL_STATUS = "WEB_CONTROL_STATUS"
    
    # Передача файлов
    FILE_TRANSFER_START = "FILE_TRANSFER_START"
    FILE_TRANSFER_DATA = "FILE_TRANSFER_DATA"
    FILE_TRANSFER_END = "FILE_TRANSFER_END"
    FILE_TRANSFER_ACK = "FILE_TRANSFER_ACK"
    FILE_COLLECT_REQUEST = "FILE_COLLECT_REQUEST"
    FILE_COLLECT_RESPONSE = "FILE_COLLECT_RESPONSE"
    
    # Мониторинг активности
    ACTIVITY_REPORT = "ACTIVITY_REPORT"
    ACTIVITY_REQUEST = "ACTIVITY_REQUEST"
    SCREENSHOT_REQUEST = "SCREENSHOT_REQUEST"
    SCREENSHOT_RESPONSE = "SCREENSHOT_RESPONSE"
    
    # Экзамены
    EXAM_START = "EXAM_START"
    EXAM_ANSWER = "EXAM_ANSWER"
    EXAM_RESULT = "EXAM_RESULT"
    EXAM_END = "EXAM_END"
    
    # Опросы
    POLL_START = "POLL_START"
    POLL_ANSWER = "POLL_ANSWER"
    POLL_RESULT = "POLL_RESULT"
    
    # Группы
    GROUP_CREATE = "GROUP_CREATE"
    GROUP_ASSIGN = "GROUP_ASSIGN"
    GROUP_MESSAGE = "GROUP_MESSAGE"
    
    # Демонстрация
    DEMO_START = "DEMO_START"
    DEMO_STOP = "DEMO_STOP"
    DEMO_FRAME = "DEMO_FRAME"
    
    # Интерактивная доска
    BOARD_START = "BOARD_START"
    BOARD_DRAW = "BOARD_DRAW"
    BOARD_CLEAR = "BOARD_CLEAR"
    BOARD_STOP = "BOARD_STOP"

# Статусы студента
class StudentStatus:
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    WATCHING_VIDEO = "watching_video"
    TAKING_EXAM = "taking_exam"
    IN_GROUP = "in_group"
    SCREEN_LOCKED = "screen_locked"
    HAND_RAISED = "hand_raised"

# Качество трансляции
class StreamQuality:
    LOW = "low"          # 480p, 15 fps, низкое сжатие
    MEDIUM = "medium"    # 720p, 24 fps, среднее сжатие
    HIGH = "high"        # 1080p, 30 fps, высокое качество
    ULTRA = "ultra"      # 1080p+, 60 fps, наивысшее качество

# Настройки качества
QUALITY_SETTINGS = {
    StreamQuality.LOW: {
        "resolution": (854, 480),
        "fps": 15,
        "quality": 50
    },
    StreamQuality.MEDIUM: {
        "resolution": (1280, 720),
        "fps": 24,
        "quality": 70
    },
    StreamQuality.HIGH: {
        "resolution": (1920, 1080),
        "fps": 30,
        "quality": 85
    },
    StreamQuality.ULTRA: {
        "resolution": (1920, 1080),
        "fps": 60,
        "quality": 95
    }
}

# Аудио настройки
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_CHUNK_SIZE = 1024

# Размеры буферов
BUFFER_SIZE = 65536
MAX_PACKET_SIZE = 60000

# Пути к данным
DATA_DIR = "data"
USERDATA_DIR = "UserData"
LOGS_DIR = "logs"
RECORDINGS_DIR = "Recordings"
RESOURCES_DIR = "resources"

# Форматы файлов
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"]
SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav", ".ogg", ".flac", ".aac"]
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
SUPPORTED_DOCUMENT_FORMATS = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"]

# Ограничения
MAX_STUDENTS = 50
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 МБ
MAX_MESSAGE_LENGTH = 1000
MAX_CHANNELS = 32

# UI константы
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 768
STUDENT_CARD_SIZE = 150
GRID_SPACING = 10

# Языки
class Language:
    RUSSIAN = "ru"
    ENGLISH = "en"

# Темы
class Theme:
    LIGHT = "light"
    DARK = "dark"

