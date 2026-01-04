"""
Видеоплеер для потоковой передачи видео студентам
"""

import cv2
import logging
import threading
import time
from typing import Optional, Callable
from pathlib import Path


logger = logging.getLogger(__name__)


class VideoStreamer:
    """Класс для потоковой передачи видеофайла"""
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap: Optional[cv2.VideoCapture] = None
        
        # Состояние
        self.playing = False
        self.paused = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.duration = 0
        
        # Поток
        self.play_thread: Optional[threading.Thread] = None
        
        # Колбэк для отправки кадров
        self.on_frame: Optional[Callable[[bytes, int], None]] = None
        
        self._load_video()
    
    def _load_video(self) -> bool:
        """Загрузить видеофайл"""
        try:
            if not Path(self.video_path).exists():
                logger.error(f"Видеофайл не найден: {self.video_path}")
                return False
            
            self.cap = cv2.VideoCapture(self.video_path)
            
            if not self.cap.isOpened():
                logger.error("Не удалось открыть видеофайл")
                return False
            
            # Получаем информацию о видео
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.duration = self.total_frames / self.fps if self.fps > 0 else 0
            
            logger.info(f"Видео загружено: {self.total_frames} кадров, {self.fps} fps, {self.duration:.1f} сек")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки видео: {e}")
            return False
    
    def play(self):
        """Начать воспроизведение"""
        if self.playing:
            if self.paused:
                self.paused = False
                logger.info("Воспроизведение возобновлено")
            return
        
        self.playing = True
        self.paused = False
        
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        
        logger.info("Воспроизведение начато")
    
    def pause(self):
        """Пауза"""
        if self.playing and not self.paused:
            self.paused = True
            logger.info("Воспроизведение приостановлено")
    
    def stop(self):
        """Остановить"""
        if not self.playing:
            return
        
        self.playing = False
        self.paused = False
        
        if self.play_thread:
            self.play_thread.join(timeout=2)
        
        # Сброс позиции
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
        
        logger.info("Воспроизведение остановлено")
    
    def seek(self, position: float):
        """Перемотать на позицию (в секундах)"""
        if not self.cap:
            return
        
        frame_number = int(position * self.fps)
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
        
        logger.info(f"Перемотка на {position:.1f} сек (кадр {frame_number})")
    
    def _play_loop(self):
        """Основной цикл воспроизведения"""
        if not self.cap:
            return
        
        frame_interval = 1.0 / self.fps
        
        while self.playing:
            # Проверяем паузу
            if self.paused:
                time.sleep(0.1)
                continue
            
            start_time = time.time()
            
            try:
                # Читаем кадр
                ret, frame = self.cap.read()
                
                if not ret:
                    # Конец видео
                    logger.info("Достигнут конец видео")
                    self.playing = False
                    break
                
                # Сжимаем в JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
                success, encoded = cv2.imencode('.jpg', frame, encode_params)
                
                if success and self.on_frame:
                    self.on_frame(encoded.tobytes(), self.current_frame)
                
                self.current_frame += 1
                
                # Контроль частоты кадров
                elapsed = time.time() - start_time
                sleep_time = frame_interval - elapsed
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Ошибка воспроизведения кадра: {e}")
                time.sleep(0.1)
        
        logger.info("Цикл воспроизведения завершен")
    
    def get_position(self) -> float:
        """Получить текущую позицию (в секундах)"""
        return self.current_frame / self.fps if self.fps > 0 else 0
    
    def get_info(self) -> dict:
        """Получить информацию о видео"""
        return {
            "path": self.video_path,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration": self.duration,
            "current_frame": self.current_frame,
            "position": self.get_position(),
            "playing": self.playing,
            "paused": self.paused
        }
    
    def close(self):
        """Закрыть видео"""
        self.stop()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        logger.info("Видео закрыто")


class AudioRecorder:
    """Класс для записи аудио (для магнитофона)"""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        
        # Буфер записи
        self.audio_buffer = []
        
        logger.info(f"AudioRecorder создан: {sample_rate}Hz, {channels} каналов")
    
    def start_recording(self):
        """Начать запись"""
        try:
            import sounddevice as sd
            
            self.recording = True
            self.audio_buffer = []
            
            def callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                if self.recording:
                    self.audio_buffer.append(indata.copy())
            
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback
            )
            self.stream.start()
            
            logger.info("Запись аудио начата")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка начала записи: {e}")
            return False
    
    def stop_recording(self) -> Optional[bytes]:
        """Остановить запись и вернуть данные"""
        if not self.recording:
            return None
        
        self.recording = False
        
        try:
            self.stream.stop()
            self.stream.close()
            
            # Объединяем буфер
            import numpy as np
            audio_data = np.concatenate(self.audio_buffer, axis=0)
            
            logger.info(f"Запись остановлена, размер: {audio_data.shape}")
            
            return audio_data.tobytes()
            
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}")
            return None
    
    def save_to_file(self, filename: str, audio_data: bytes):
        """Сохранить аудио в файл"""
        try:
            import soundfile as sf
            import numpy as np
            
            # Конвертируем bytes обратно в numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            audio_array = audio_array.reshape(-1, self.channels)
            
            sf.write(filename, audio_array, self.sample_rate)
            
            logger.info(f"Аудио сохранено: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения аудио: {e}")
            return False

