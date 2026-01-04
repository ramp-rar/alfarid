"""
Запись уроков
Версия 1.0

Записывает:
- Экран преподавателя (JPEG кадры)
- Аудио преподавателя (MP3)
- Веб-камеру преподавателя (опционально)
- Интерактивную доску (команды рисования)
- Чат сообщения
- События урока (студент поднял руку, и т.д.)
"""

import os
import json
import logging
import threading
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """Конфигурация записи"""
    # Output
    output_dir: str = "recordings"
    
    # Quality
    screen_fps: int = 24
    screen_quality: int = 70  # JPEG quality
    audio_bitrate: str = "128k"
    
    # Features
    record_screen: bool = True
    record_audio: bool = True
    record_webcam: bool = False
    record_whiteboard: bool = True
    record_chat: bool = True
    record_events: bool = True
    
    # Limits
    max_duration_minutes: int = 180  # 3 часа макс


@dataclass
class LessonMetadata:
    """Метаданные урока"""
    lesson_id: str
    lesson_name: str
    teacher_name: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None
    
    # Participants
    students: List[str] = field(default_factory=list)
    student_count: int = 0
    
    # Stats
    frame_count: int = 0
    event_count: int = 0
    chat_messages: int = 0
    
    # Files
    screen_dir: str = "screen"
    audio_file: str = "audio.wav"
    webcam_file: Optional[str] = None
    whiteboard_file: str = "whiteboard.json"
    chat_file: str = "chat.json"
    events_file: str = "events.json"


class LessonRecorder:
    """
    Рекордер урока.
    
    Использование:
        recorder = LessonRecorder()
        recorder.start_recording("Урок математики")
        
        # Во время урока:
        recorder.add_screen_frame(frame_data)
        recorder.add_audio_chunk(audio_data)
        recorder.add_event("student_hand_raised", {"student": "Иван"})
        recorder.add_chat_message("Иван", "Вопрос...")
        
        recorder.stop_recording()
    """
    
    def __init__(self, config: Optional[RecordingConfig] = None):
        self.config = config or RecordingConfig()
        self.recording = False
        
        # Текущая запись
        self.current_recording: Optional[Path] = None
        self.metadata: Optional[LessonMetadata] = None
        self.start_time: Optional[float] = None
        
        # Буферы
        self._screen_frames: List[bytes] = []
        self._audio_chunks: List[bytes] = []
        self._whiteboard_commands: List[Dict] = []
        self._chat_messages: List[Dict] = []
        self._events: List[Dict] = []
        
        # Потоки сохранения
        self._save_thread: Optional[threading.Thread] = None
        self._save_lock = threading.Lock()
        
        logger.info("LessonRecorder создан")
    
    def start_recording(
        self,
        lesson_name: str,
        teacher_name: str,
        students: List[str] = None
    ) -> str:
        """
        Начать запись урока.
        
        Returns:
            Path к директории записи
        """
        if self.recording:
            logger.warning("Запись уже идёт")
            return str(self.current_recording)
        
        # Создаём директорию для записи
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = "".join(c for c in lesson_name if c.isalnum() or c in (' ', '-', '_'))
        recording_name = f"{safe_name}_{timestamp}"
        
        recording_path = Path(self.config.output_dir) / recording_name
        recording_path.mkdir(parents=True, exist_ok=True)
        
        # Создаём поддиректории
        if self.config.record_screen:
            (recording_path / "screen").mkdir(exist_ok=True)
        
        # Метаданные
        lesson_id = f"lesson_{int(time.time())}"
        self.metadata = LessonMetadata(
            lesson_id=lesson_id,
            lesson_name=lesson_name,
            teacher_name=teacher_name,
            start_time=timestamp,
            students=students or [],
            student_count=len(students) if students else 0
        )
        
        self.current_recording = recording_path
        self.start_time = time.time()
        self.recording = True
        
        # Очищаем буферы
        self._screen_frames.clear()
        self._audio_chunks.clear()
        self._whiteboard_commands.clear()
        self._chat_messages.clear()
        self._events.clear()
        
        logger.info(f"Запись начата: {recording_path}")
        
        return str(recording_path)
    
    def add_screen_frame(self, frame_data: bytes):
        """Добавить кадр экрана"""
        if not self.recording or not self.config.record_screen:
            return
        
        with self._save_lock:
            self._screen_frames.append(frame_data)
            self.metadata.frame_count += 1
            
            # Периодически сохраняем на диск
            if len(self._screen_frames) >= 100:  # Каждые ~4 секунды при 24 FPS
                self._flush_screen_frames()
    
    def add_audio_chunk(self, audio_data: bytes):
        """Добавить аудио чанк"""
        if not self.recording or not self.config.record_audio:
            return
        
        with self._save_lock:
            self._audio_chunks.append(audio_data)
    
    def add_whiteboard_command(self, command: Dict):
        """Добавить команду рисования на доске"""
        if not self.recording or not self.config.record_whiteboard:
            return
        
        # Добавляем timestamp
        command['timestamp'] = time.time() - self.start_time
        
        with self._save_lock:
            self._whiteboard_commands.append(command)
    
    def add_chat_message(self, sender: str, content: str, is_teacher: bool = True):
        """Добавить чат сообщение"""
        if not self.recording or not self.config.record_chat:
            return
        
        message = {
            'timestamp': time.time() - self.start_time,
            'sender': sender,
            'content': content,
            'is_teacher': is_teacher,
            'time': datetime.now().strftime("%H:%M:%S")
        }
        
        with self._save_lock:
            self._chat_messages.append(message)
            self.metadata.chat_messages += 1
    
    def add_event(self, event_type: str, data: Dict):
        """Добавить событие"""
        if not self.recording or not self.config.record_events:
            return
        
        event = {
            'timestamp': time.time() - self.start_time,
            'type': event_type,
            'data': data,
            'time': datetime.now().strftime("%H:%M:%S")
        }
        
        with self._save_lock:
            self._events.append(event)
            self.metadata.event_count += 1
    
    def _flush_screen_frames(self):
        """Сохранить кадры экрана на диск"""
        if not self._screen_frames:
            return
        
        try:
            screen_dir = self.current_recording / "screen"
            
            # Получаем текущий номер кадра
            existing_frames = list(screen_dir.glob("*.jpg"))
            start_number = len(existing_frames)
            
            # Сохраняем
            for i, frame_data in enumerate(self._screen_frames):
                frame_number = start_number + i
                frame_path = screen_dir / f"{frame_number:05d}.jpg"
                
                with open(frame_path, 'wb') as f:
                    f.write(frame_data)
            
            logger.debug(f"Сохранено {len(self._screen_frames)} кадров")
            self._screen_frames.clear()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения кадров: {e}")
    
    def stop_recording(self) -> Optional[str]:
        """
        Остановить запись урока.
        
        Returns:
            Path к записи или None
        """
        if not self.recording:
            return None
        
        self.recording = False
        
        logger.info("Остановка записи...")
        
        # Финализируем запись
        try:
            # Сохраняем оставшиеся кадры
            if self._screen_frames:
                self._flush_screen_frames()
            
            # Сохраняем аудио
            if self._audio_chunks and self.config.record_audio:
                self._save_audio()
            
            # Сохраняем доску
            if self._whiteboard_commands:
                self._save_whiteboard()
            
            # Сохраняем чат
            if self._chat_messages:
                self._save_chat()
            
            # Сохраняем события
            if self._events:
                self._save_events()
            
            # Обновляем метаданные
            self.metadata.end_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.metadata.duration_seconds = int(time.time() - self.start_time)
            
            # Сохраняем метаданные
            self._save_metadata()
            
            recording_path = str(self.current_recording)
            logger.info(f"Запись завершена: {recording_path}")
            
            return recording_path
            
        except Exception as e:
            logger.error(f"Ошибка финализации записи: {e}")
            return None
    
    def _save_audio(self):
        """Сохранить аудио"""
        try:
            audio_path = self.current_recording / self.metadata.audio_file
            
            # Объединяем чанки
            audio_data = b''.join(self._audio_chunks)
            
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"Аудио сохранено: {len(self._audio_chunks)} чанков")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения аудио: {e}")
    
    def _save_whiteboard(self):
        """Сохранить команды доски"""
        try:
            wb_path = self.current_recording / self.metadata.whiteboard_file
            
            with open(wb_path, 'w', encoding='utf-8') as f:
                json.dump(self._whiteboard_commands, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Доска сохранена: {len(self._whiteboard_commands)} команд")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения доски: {e}")
    
    def _save_chat(self):
        """Сохранить чат"""
        try:
            chat_path = self.current_recording / self.metadata.chat_file
            
            with open(chat_path, 'w', encoding='utf-8') as f:
                json.dump(self._chat_messages, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Чат сохранён: {len(self._chat_messages)} сообщений")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения чата: {e}")
    
    def _save_events(self):
        """Сохранить события"""
        try:
            events_path = self.current_recording / self.metadata.events_file
            
            with open(events_path, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, indent=2, ensure_ascii=False)
            
            logger.info(f"События сохранены: {len(self._events)} событий")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения событий: {e}")
    
    def _save_metadata(self):
        """Сохранить метаданные"""
        try:
            metadata_path = self.current_recording / "metadata.json"
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.metadata), f, indent=2, ensure_ascii=False)
            
            logger.info("Метаданные сохранены")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения метаданных: {e}")
    
    def get_recording_path(self) -> Optional[str]:
        """Получить путь к текущей записи"""
        return str(self.current_recording) if self.current_recording else None
    
    def is_recording(self) -> bool:
        """Проверить статус записи"""
        return self.recording


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Тест записи урока...")
    
    recorder = LessonRecorder()
    
    # Начинаем запись
    path = recorder.start_recording(
        lesson_name="Тестовый урок",
        teacher_name="Иванов И.В.",
        students=["Петров П.", "Сидоров С."]
    )
    
    print(f"Запись начата: {path}")
    
    # Добавляем тестовые данные
    for i in range(10):
        # Тестовый кадр
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        recorder.add_screen_frame(buffer.tobytes())
        
        time.sleep(0.1)
    
    # Добавляем события
    recorder.add_event("lesson_start", {"time": "10:00"})
    recorder.add_chat_message("Иванов И.В.", "Здравствуйте!", is_teacher=True)
    recorder.add_chat_message("Петров П.", "Добрый день!", is_teacher=False)
    recorder.add_event("hand_raised", {"student": "Сидоров С."})
    
    # Останавливаем
    final_path = recorder.stop_recording()
    
    print(f"Запись завершена: {final_path}")
    print(f"Кадров: {recorder.metadata.frame_count}")
    print(f"Событий: {recorder.metadata.event_count}")
    print(f"Чат сообщений: {recorder.metadata.chat_messages}")
    
    # Проверяем файлы
    if final_path:
        recording_dir = Path(final_path)
        files = list(recording_dir.rglob("*"))
        print(f"\nСозданные файлы ({len(files)}):")
        for f in files:
            if f.is_file():
                print(f"  - {f.relative_to(recording_dir)} ({f.stat().st_size} bytes)")
    
    print("\nТест завершён!")



