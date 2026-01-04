"""
Модуль захвата и трансляции экрана
"""

import cv2
import numpy as np
import mss
import logging
import threading
import time
from typing import Optional, Callable, Tuple
from src.common.constants import StreamQuality, QUALITY_SETTINGS


logger = logging.getLogger(__name__)


class ScreenCapture:
    """Класс для захвата экрана"""
    
    def __init__(self, quality: str = StreamQuality.MEDIUM, fps: int = 24):
        self.quality = quality
        self.fps = fps
        self.capturing = False
        self.capture_thread: Optional[threading.Thread] = None
        
        # Настройки качества
        self.settings = QUALITY_SETTINGS[quality]
        self.target_resolution = self.settings["resolution"]
        self.target_fps = self.settings.get("fps", fps)
        self.jpeg_quality = self.settings["quality"]
        
        # Колбэк для обработки кадров
        self.on_frame: Optional[Callable[[bytes, int], None]] = None
        
        # Статистика
        self.frame_count = 0
        self.dropped_frames = 0
        
        logger.info(f"ScreenCapture создан: качество={quality}, fps={self.target_fps}")
    
    def start(self) -> bool:
        """Начать захват экрана"""
        if self.capturing:
            logger.warning("Захват уже запущен")
            return False
        
        try:
            self.capturing = True
            self.frame_count = 0
            self.dropped_frames = 0
            
            # Запускаем поток захвата
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Захват экрана запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска захвата: {e}")
            self.capturing = False
            return False
    
    def stop(self):
        """Остановить захват экрана"""
        if not self.capturing:
            return
        
        logger.info("Остановка захвата экрана...")
        self.capturing = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        
        logger.info(f"Захват остановлен. Кадров: {self.frame_count}, пропущено: {self.dropped_frames}")
    
    def _capture_loop(self):
        """Основной цикл захвата"""
        frame_interval = 1.0 / self.target_fps
        
        with mss.mss() as sct:
            # Получаем информацию о мониторе
            monitor = sct.monitors[1]  # Главный монитор
            
            logger.info(f"Монитор: {monitor['width']}x{monitor['height']}")
            
            while self.capturing:
                start_time = time.time()
                
                try:
                    # Захватываем экран
                    screenshot = sct.grab(monitor)
                    
                    # Конвертируем в numpy array
                    frame = np.array(screenshot)
                    
                    # Конвертируем BGRA -> BGR
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    # Изменяем размер если нужно
                    if frame.shape[1] != self.target_resolution[0] or frame.shape[0] != self.target_resolution[1]:
                        frame = cv2.resize(frame, self.target_resolution, interpolation=cv2.INTER_LINEAR)
                    
                    # Сжимаем в JPEG
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                    success, encoded = cv2.imencode('.jpg', frame, encode_params)
                    
                    if success:
                        # Отправляем кадр через колбэк
                        if self.on_frame:
                            self.on_frame(encoded.tobytes(), self.frame_count)
                        
                        self.frame_count += 1
                    else:
                        self.dropped_frames += 1
                        logger.warning("Ошибка кодирования кадра")
                    
                    # Контроль частоты кадров
                    elapsed = time.time() - start_time
                    sleep_time = frame_interval - elapsed
                    
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    else:
                        # Кадр обрабатывался дольше интервала
                        self.dropped_frames += 1
                        
                except Exception as e:
                    logger.error(f"Ошибка захвата кадра: {e}")
                    time.sleep(0.1)
        
        logger.info("Цикл захвата завершен")
    
    def capture_single_frame(self) -> Optional[bytes]:
        """Захватить один кадр (для скриншотов)"""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 90]
                success, encoded = cv2.imencode('.jpg', frame, encode_params)
                
                if success:
                    return encoded.tobytes()
                return None
                
        except Exception as e:
            logger.error(f"Ошибка захвата одиночного кадра: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            "frame_count": self.frame_count,
            "dropped_frames": self.dropped_frames,
            "fps": self.target_fps,
            "quality": self.quality,
            "resolution": self.target_resolution
        }


class ScreenReceiver:
    """Класс для приема и отображения экрана"""
    
    def __init__(self):
        self.receiving = False
        self.current_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        
        # Статистика
        self.frames_received = 0
        self.last_frame_time = 0
        
        logger.info("ScreenReceiver создан")
    
    def process_frame(self, frame_data: bytes, frame_id: int):
        """Обработать полученный кадр"""
        try:
            # Декодируем JPEG
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
                    self.frames_received += 1
                    self.last_frame_time = time.time()
            else:
                logger.warning(f"Не удалось декодировать кадр {frame_id}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки кадра: {e}")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Получить текущий кадр"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_current_frame_as_pixmap(self):
        """Получить текущий кадр как QPixmap для отображения в Qt"""
        frame = self.get_current_frame()
        if frame is None:
            return None
        
        try:
            from PyQt5.QtGui import QImage, QPixmap
            
            # Конвертируем BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            height, width, channel = frame_rgb.shape
            bytes_per_line = 3 * width
            
            q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
            return pixmap
            
        except Exception as e:
            logger.error(f"Ошибка конвертации кадра в QPixmap: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        current_time = time.time()
        time_since_last = current_time - self.last_frame_time if self.last_frame_time > 0 else 0
        
        return {
            "frames_received": self.frames_received,
            "time_since_last_frame": time_since_last,
            "has_frame": self.current_frame is not None
        }

