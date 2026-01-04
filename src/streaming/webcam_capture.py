"""
Захват и трансляция веб-камеры
Версия 1.0
"""

import logging
import threading
import time
import base64
import zlib
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class WebcamSettings:
    """Настройки веб-камеры"""
    camera_index: int = 0  # Индекс камеры (0 = по умолчанию)
    width: int = 640
    height: int = 480
    fps: int = 15
    quality: int = 70  # JPEG качество (1-100)
    
    @property
    def resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)


class WebcamCapture:
    """
    Захват видео с веб-камеры
    
    Использование:
        webcam = WebcamCapture()
        webcam.on_frame = lambda frame, id: send_to_students(frame, id)
        webcam.start()
        ...
        webcam.stop()
    """
    
    def __init__(self, settings: Optional[WebcamSettings] = None):
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV не установлен. Установите: pip install opencv-python")
        
        self.settings = settings or WebcamSettings()
        self.capturing = False
        self.cap: Optional[cv2.VideoCapture] = None
        
        # Поток захвата
        self.capture_thread: Optional[threading.Thread] = None
        
        # Колбэк для кадров
        self.on_frame: Optional[Callable[[bytes, int], None]] = None
        
        # Статистика
        self._frame_id = 0
        self._frames_sent = 0
        self._bytes_sent = 0
        self._last_fps_time = 0
        self._fps_frame_count = 0
        self._current_fps = 0.0
        
        logger.info(f"WebcamCapture создан: камера {self.settings.camera_index}, "
                    f"{self.settings.width}x{self.settings.height} @ {self.settings.fps}fps")
    
    @staticmethod
    def list_cameras(max_count: int = 5) -> List[int]:
        """Получить список доступных камер"""
        if not CV2_AVAILABLE:
            return []
        
        available = []
        for i in range(max_count):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        
        return available
    
    def start(self) -> bool:
        """Начать захват камеры"""
        if self.capturing:
            logger.warning("Захват камеры уже идет")
            return False
        
        try:
            # Открываем камеру
            self.cap = cv2.VideoCapture(self.settings.camera_index)
            
            if not self.cap.isOpened():
                logger.error(f"Не удалось открыть камеру {self.settings.camera_index}")
                return False
            
            # Устанавливаем параметры
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.settings.fps)
            
            # Проверяем реальные параметры
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Камера открыта: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            self.capturing = True
            self._frame_id = 0
            self._frames_sent = 0
            self._bytes_sent = 0
            self._last_fps_time = time.time()
            self._fps_frame_count = 0
            
            # Запускаем поток захвата
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Захват веб-камеры запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска камеры: {e}")
            self.capturing = False
            return False
    
    def stop(self):
        """Остановить захват"""
        if not self.capturing:
            return
        
        self.capturing = False
        
        # Ждем завершения потока
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        
        # Освобождаем камеру
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        
        logger.info(f"Захват камеры остановлен. Отправлено: {self._frames_sent} кадров, {self._bytes_sent} байт")
    
    def _capture_loop(self):
        """Основной цикл захвата"""
        frame_interval = 1.0 / self.settings.fps
        last_frame_time = 0
        
        while self.capturing:
            try:
                current_time = time.time()
                
                # Контролируем FPS
                elapsed = current_time - last_frame_time
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    continue
                
                last_frame_time = current_time
                
                # Захватываем кадр
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Не удалось захватить кадр")
                    time.sleep(0.1)
                    continue
                
                # Кодируем в JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.settings.quality]
                _, encoded = cv2.imencode('.jpg', frame, encode_params)
                frame_bytes = encoded.tobytes()
                
                # Отправляем через колбэк
                if self.on_frame:
                    self._frame_id += 1
                    self._frames_sent += 1
                    self._bytes_sent += len(frame_bytes)
                    
                    self.on_frame(frame_bytes, self._frame_id)
                
                # Обновляем FPS
                self._fps_frame_count += 1
                if current_time - self._last_fps_time >= 1.0:
                    self._current_fps = self._fps_frame_count / (current_time - self._last_fps_time)
                    self._fps_frame_count = 0
                    self._last_fps_time = current_time
                    
            except Exception as e:
                logger.error(f"Ошибка в цикле захвата камеры: {e}")
                time.sleep(0.1)
    
    def get_preview_frame(self) -> Optional[bytes]:
        """Получить превью кадр (для UI)"""
        if not self.cap or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            if not ret:
                return None
            
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
            _, encoded = cv2.imencode('.jpg', frame, encode_params)
            return encoded.tobytes()
            
        except Exception as e:
            logger.error(f"Ошибка получения превью: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            'capturing': self.capturing,
            'frame_id': self._frame_id,
            'frames_sent': self._frames_sent,
            'bytes_sent': self._bytes_sent,
            'fps': self._current_fps,
            'camera_index': self.settings.camera_index,
            'resolution': self.settings.resolution
        }
    
    def set_quality(self, quality: int):
        """Установить качество JPEG (1-100)"""
        self.settings.quality = max(1, min(100, quality))


class WebcamReceiver:
    """
    Приемник видео с веб-камеры (для студента)
    
    Использование:
        receiver = WebcamReceiver()
        receiver.process_frame(frame_bytes, frame_id)
        pixmap = receiver.get_current_frame_as_pixmap()
    """
    
    def __init__(self):
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV не установлен")
        
        self._current_frame: Optional[np.ndarray] = None
        self._frame_id = 0
        self._frames_received = 0
        
        # FPS calculation
        self._last_fps_time = time.time()
        self._fps_frame_count = 0
        self._current_fps = 0.0
        
        self._lock = threading.Lock()
        
        logger.info("WebcamReceiver создан")
    
    def process_frame(self, frame_bytes: bytes, frame_id: int):
        """Обработать полученный кадр"""
        try:
            # Декодируем JPEG
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning("Не удалось декодировать кадр камеры")
                return
            
            with self._lock:
                self._current_frame = frame
                self._frame_id = frame_id
                self._frames_received += 1
            
            # Обновляем FPS
            current_time = time.time()
            self._fps_frame_count += 1
            if current_time - self._last_fps_time >= 1.0:
                self._current_fps = self._fps_frame_count / (current_time - self._last_fps_time)
                self._fps_frame_count = 0
                self._last_fps_time = current_time
                
        except Exception as e:
            logger.error(f"Ошибка обработки кадра камеры: {e}")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Получить текущий кадр как numpy array (BGR)"""
        with self._lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
        return None
    
    def get_current_frame_as_pixmap(self):
        """Получить текущий кадр как QPixmap"""
        try:
            from PyQt5.QtGui import QImage, QPixmap
            
            with self._lock:
                if self._current_frame is None:
                    return None
                
                frame = self._current_frame.copy()
            
            # Конвертируем BGR -> RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            qimage = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            return QPixmap.fromImage(qimage)
            
        except Exception as e:
            logger.error(f"Ошибка конвертации кадра камеры в QPixmap: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            'frame_id': self._frame_id,
            'frames_received': self._frames_received,
            'fps': self._current_fps
        }


class WebcamBroadcaster:
    """
    Менеджер трансляции веб-камеры (для преподавателя)
    
    Использование:
        broadcaster = WebcamBroadcaster()
        broadcaster.on_frame_data = lambda data, id: server.broadcast("WEBCAM", {"data": data, "id": id})
        broadcaster.start()
        ...
        broadcaster.stop()
    """
    
    def __init__(self, settings: Optional[WebcamSettings] = None):
        self.settings = settings or WebcamSettings()
        self.capture: Optional[WebcamCapture] = None
        self.active = False
        
        # Колбэк для отправки
        self.on_frame_data: Optional[Callable[[str, int], None]] = None
        
        logger.info("WebcamBroadcaster создан")
    
    @staticmethod
    def list_cameras() -> List[int]:
        """Получить список доступных камер"""
        return WebcamCapture.list_cameras()
    
    def start(self, camera_index: int = 0) -> bool:
        """Начать трансляцию камеры"""
        if self.active:
            return False
        
        try:
            self.settings.camera_index = camera_index
            self.capture = WebcamCapture(self.settings)
            self.capture.on_frame = self._on_frame
            
            if self.capture.start():
                self.active = True
                logger.info(f"Трансляция камеры {camera_index} запущена")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка запуска трансляции камеры: {e}")
            return False
    
    def stop(self):
        """Остановить трансляцию"""
        if not self.active:
            return
        
        self.active = False
        
        if self.capture:
            self.capture.stop()
            self.capture = None
        
        logger.info("Трансляция камеры остановлена")
    
    def _on_frame(self, frame_bytes: bytes, frame_id: int):
        """Обработка кадра для отправки"""
        if self.on_frame_data:
            # Кодируем в base64 для JSON
            encoded = base64.b64encode(frame_bytes).decode('ascii')
            self.on_frame_data(encoded, frame_id)
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        if self.capture:
            return self.capture.get_stats()
        return {'active': False}
    
    def set_quality(self, quality: int):
        """Установить качество"""
        self.settings.quality = max(1, min(100, quality))
        if self.capture:
            self.capture.set_quality(quality)


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест веб-камеры...")
    
    # Список камер
    cameras = WebcamCapture.list_cameras()
    print(f"Доступные камеры: {cameras}")
    
    if not cameras:
        print("Камеры не найдены!")
        exit(1)
    
    # Тест захвата
    webcam = WebcamCapture()
    
    frame_count = 0
    def on_frame(data, id):
        global frame_count
        frame_count += 1
        if frame_count % 15 == 0:
            print(f"Кадр {id}: {len(data)} байт, FPS: {webcam._current_fps:.1f}")
    
    webcam.on_frame = on_frame
    
    print("Запуск камеры (5 секунд)...")
    if webcam.start():
        time.sleep(5)
        webcam.stop()
        print(f"Захвачено кадров: {webcam._frames_sent}")
    else:
        print("Не удалось запустить камеру!")
    
    print("Тест завершен!")

