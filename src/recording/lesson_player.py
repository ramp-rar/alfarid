"""
Воспроизведение записей уроков
Версия 1.0
"""

import json
import logging
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlaybackState:
    """Состояние воспроизведения"""
    current_time: float = 0.0
    current_frame: int = 0
    is_playing: bool = False
    is_paused: bool = False
    playback_speed: float = 1.0  # 1.0 = normal, 2.0 = 2x speed


class LessonPlayer:
    """
    Плеер для записей уроков.
    
    Использование:
        player = LessonPlayer("recordings/Lesson_2026-01-03_10-00/")
        player.on_frame = lambda frame: display_frame(frame)
        player.on_event = lambda event: handle_event(event)
        player.play()
    """
    
    def __init__(self, recording_path: str):
        self.recording_path = Path(recording_path)
        
        if not self.recording_path.exists():
            raise FileNotFoundError(f"Запись не найдена: {recording_path}")
        
        # Загружаем метаданные
        self.metadata = self._load_metadata()
        
        # Загружаем данные
        self.screen_frames = self._load_screen_frames()
        self.chat_messages = self._load_chat()
        self.events = self._load_events()
        self.whiteboard_commands = self._load_whiteboard()
        
        # Статус воспроизведения
        self.state = PlaybackState()
        
        # Колбэки
        self.on_frame: Optional[Callable[[np.ndarray, int], None]] = None
        self.on_chat: Optional[Callable[[Dict], None]] = None
        self.on_event: Optional[Callable[[Dict], None]] = None
        
        logger.info(f"LessonPlayer создан: {self.metadata.get('lesson_name', 'Unknown')}")
        logger.info(f"Кадров: {len(self.screen_frames)}, Событий: {len(self.events)}")
    
    def _load_metadata(self) -> Dict:
        """Загрузить метаданные"""
        metadata_file = self.recording_path / "metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {}
    
    def _load_screen_frames(self) -> List[Path]:
        """Загрузить список кадров"""
        screen_dir = self.recording_path / "screen"
        
        if screen_dir.exists():
            frames = sorted(screen_dir.glob("*.jpg"))
            return frames
        
        return []
    
    def _load_chat(self) -> List[Dict]:
        """Загрузить чат"""
        chat_file = self.recording_path / "chat.json"
        
        if chat_file.exists():
            with open(chat_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    
    def _load_events(self) -> List[Dict]:
        """Загрузить события"""
        events_file = self.recording_path / "events.json"
        
        if events_file.exists():
            with open(events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    
    def _load_whiteboard(self) -> List[Dict]:
        """Загрузить команды доски"""
        wb_file = self.recording_path / "whiteboard.json"
        
        if wb_file.exists():
            with open(wb_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    
    def get_frame(self, frame_number: int) -> Optional[np.ndarray]:
        """Получить конкретный кадр"""
        if 0 <= frame_number < len(self.screen_frames):
            frame_path = self.screen_frames[frame_number]
            frame = cv2.imread(str(frame_path))
            return frame
        
        return None
    
    def seek(self, time_seconds: float):
        """Перемотка на время"""
        # Вычисляем номер кадра
        fps = self.metadata.get('screen_fps', 24)
        frame_number = int(time_seconds * fps)
        
        self.state.current_time = time_seconds
        self.state.current_frame = min(frame_number, len(self.screen_frames) - 1)
    
    def play(self):
        """Начать воспроизведение"""
        self.state.is_playing = True
        self.state.is_paused = False
        logger.info("Воспроизведение начато")
    
    def pause(self):
        """Пауза"""
        self.state.is_paused = True
        logger.info("Пауза")
    
    def resume(self):
        """Продолжить"""
        self.state.is_paused = False
        logger.info("Продолжено")
    
    def stop(self):
        """Остановить"""
        self.state.is_playing = False
        self.state.current_frame = 0
        self.state.current_time = 0
        logger.info("Остановлено")
    
    def get_info(self) -> Dict:
        """Получить информацию о записи"""
        return {
            'lesson_name': self.metadata.get('lesson_name'),
            'teacher': self.metadata.get('teacher_name'),
            'duration': self.metadata.get('duration_seconds'),
            'students': len(self.metadata.get('students', [])),
            'frames': len(self.screen_frames),
            'events': len(self.events),
            'chat_messages': len(self.chat_messages),
        }


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python lesson_player.py <recording_path>")
        print("\nИли создайте тестовую запись:")
        print("  python lesson_recorder.py")
        sys.exit(1)
    
    recording_path = sys.argv[1]
    
    print(f"Загрузка записи: {recording_path}")
    
    try:
        player = LessonPlayer(recording_path)
        
        info = player.get_info()
        print("\nИнформация о записи:")
        print(f"  Урок: {info['lesson_name']}")
        print(f"  Преподаватель: {info['teacher']}")
        print(f"  Длительность: {info['duration']} сек")
        print(f"  Студентов: {info['students']}")
        print(f"  Кадров: {info['frames']}")
        print(f"  Событий: {info['events']}")
        print(f"  Чат сообщений: {info['chat_messages']}")
        
        # Показываем первый кадр
        if player.screen_frames:
            print("\nПоказываю первый кадр...")
            frame = player.get_frame(0)
            if frame is not None:
                cv2.imshow("Lesson Preview", frame)
                cv2.waitKey(2000)
                cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()



