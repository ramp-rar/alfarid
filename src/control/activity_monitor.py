"""
Мониторинг активности студентов
Версия 1.0

Отслеживает:
- Активное приложение
- Открытые окна
- Активность клавиатуры/мыши
- Скриншоты по запросу
"""

import logging
import time
import threading
import base64
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Флаг доступности
ACTIVITY_MONITOR_AVAILABLE = False

try:
    import sys
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        ACTIVITY_MONITOR_AVAILABLE = True
except ImportError:
    pass


@dataclass  
class ActivityReport:
    """Отчёт об активности"""
    timestamp: float = field(default_factory=time.time)
    active_window: str = ""
    active_process: str = ""
    idle_time: float = 0  # Секунды с последней активности
    is_active: bool = True
    open_windows: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'active_window': self.active_window,
            'active_process': self.active_process,
            'idle_time': self.idle_time,
            'is_active': self.is_active,
            'open_windows': self.open_windows[:10]  # Максимум 10
        }


class ActivityMonitor:
    """
    Монитор активности (для студента)
    
    Отправляет периодические отчёты преподавателю.
    """
    
    def __init__(self, report_interval: float = 10.0):
        self.report_interval = report_interval
        self.monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Колбэк для отправки отчёта
        self.on_report: Optional[Callable[[ActivityReport], None]] = None
        
        # Последний отчёт
        self.last_report: Optional[ActivityReport] = None
        
        logger.info(f"ActivityMonitor создан (доступен: {ACTIVITY_MONITOR_AVAILABLE})")
    
    def start(self):
        """Начать мониторинг"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Мониторинг активности запущен")
    
    def stop(self):
        """Остановить мониторинг"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        
        logger.info("Мониторинг активности остановлен")
    
    def get_current_report(self) -> ActivityReport:
        """Получить текущий отчёт"""
        report = ActivityReport()
        
        if ACTIVITY_MONITOR_AVAILABLE:
            try:
                report.active_window = self._get_active_window_title()
                report.active_process = self._get_active_process_name()
                report.idle_time = self._get_idle_time()
                report.is_active = report.idle_time < 60  # Активен если меньше минуты
                report.open_windows = self._get_open_windows()
            except Exception as e:
                logger.error(f"Ошибка получения активности: {e}")
        
        self.last_report = report
        return report
    
    def _monitor_loop(self):
        """Цикл мониторинга"""
        while not self._stop_event.is_set():
            try:
                report = self.get_current_report()
                
                if self.on_report:
                    self.on_report(report)
                    
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
            
            self._stop_event.wait(self.report_interval)
    
    def _get_active_window_title(self) -> str:
        """Получить заголовок активного окна"""
        if not ACTIVITY_MONITOR_AVAILABLE:
            return ""
        
        try:
            user32 = ctypes.windll.user32
            
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buffer = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buffer, length)
            
            return buffer.value
            
        except Exception as e:
            logger.error(f"Ошибка получения заголовка окна: {e}")
            return ""
    
    def _get_active_process_name(self) -> str:
        """Получить имя активного процесса"""
        if not ACTIVITY_MONITOR_AVAILABLE:
            return ""
        
        try:
            import psutil
            
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            
            # Получаем ID процесса
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # Получаем имя процесса
            process = psutil.Process(pid.value)
            return process.name()
            
        except ImportError:
            # psutil не установлен
            return ""
        except Exception as e:
            logger.debug(f"Ошибка получения процесса: {e}")
            return ""
    
    def _get_idle_time(self) -> float:
        """Получить время простоя (секунды)"""
        if not ACTIVITY_MONITOR_AVAILABLE:
            return 0
        
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('dwTime', ctypes.c_uint)
                ]
            
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            if user32.GetLastInputInfo(ctypes.byref(lii)):
                current_time = kernel32.GetTickCount()
                idle_ms = current_time - lii.dwTime
                return idle_ms / 1000.0
            
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка получения idle time: {e}")
            return 0
    
    def _get_open_windows(self) -> List[str]:
        """Получить список открытых окон"""
        if not ACTIVITY_MONITOR_AVAILABLE:
            return []
        
        windows = []
        
        try:
            user32 = ctypes.windll.user32
            
            def callback(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd) + 1
                    if length > 1:
                        buffer = ctypes.create_unicode_buffer(length)
                        user32.GetWindowTextW(hwnd, buffer, length)
                        if buffer.value:
                            windows.append(buffer.value)
                return True
            
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
            user32.EnumWindows(WNDENUMPROC(callback), 0)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка окон: {e}")
        
        return windows


class ScreenshotCapture:
    """Захват скриншота по запросу"""
    
    @staticmethod
    def capture() -> Optional[str]:
        """Сделать скриншот и вернуть base64"""
        try:
            import mss
            import io
            from PIL import Image
            
            with mss.mss() as sct:
                # Захватываем весь экран
                monitor = sct.monitors[0]
                screenshot = sct.grab(monitor)
                
                # Конвертируем в PIL Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                
                # Уменьшаем для экономии трафика
                max_size = (1280, 720)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Сохраняем в JPEG
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=60)
                
                # Кодируем в base64
                return base64.b64encode(buffer.getvalue()).decode('ascii')
                
        except Exception as e:
            logger.error(f"Ошибка захвата скриншота: {e}")
            return None
    
    @staticmethod
    def save_screenshot(data_base64: str, filename: str) -> bool:
        """Сохранить скриншот из base64"""
        try:
            image_data = base64.b64decode(data_base64)
            
            with open(filename, 'wb') as f:
                f.write(image_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения скриншота: {e}")
            return False


class ActivityTracker:
    """
    Трекер активности (для преподавателя)
    
    Собирает и хранит отчёты от студентов.
    """
    
    def __init__(self):
        self._reports: Dict[str, ActivityReport] = {}  # student_id -> last report
        self._screenshots: Dict[str, str] = {}  # student_id -> base64
        
        logger.info("ActivityTracker создан")
    
    def update_report(self, student_id: str, report_data: Dict):
        """Обновить отчёт студента"""
        report = ActivityReport(
            timestamp=report_data.get('timestamp', time.time()),
            active_window=report_data.get('active_window', ''),
            active_process=report_data.get('active_process', ''),
            idle_time=report_data.get('idle_time', 0),
            is_active=report_data.get('is_active', True),
            open_windows=report_data.get('open_windows', [])
        )
        
        self._reports[student_id] = report
    
    def update_screenshot(self, student_id: str, screenshot_base64: str):
        """Обновить скриншот студента"""
        self._screenshots[student_id] = screenshot_base64
    
    def get_report(self, student_id: str) -> Optional[ActivityReport]:
        """Получить последний отчёт студента"""
        return self._reports.get(student_id)
    
    def get_screenshot(self, student_id: str) -> Optional[str]:
        """Получить скриншот студента"""
        return self._screenshots.get(student_id)
    
    def get_all_reports(self) -> Dict[str, ActivityReport]:
        """Получить все отчёты"""
        return self._reports.copy()
    
    def get_inactive_students(self, threshold: float = 60) -> List[str]:
        """Получить список неактивных студентов"""
        inactive = []
        current_time = time.time()
        
        for student_id, report in self._reports.items():
            if report.idle_time > threshold:
                inactive.append(student_id)
            elif current_time - report.timestamp > threshold * 2:
                # Нет отчёта слишком долго
                inactive.append(student_id)
        
        return inactive
    
    def get_distracted_students(self, allowed_apps: List[str] = None) -> List[str]:
        """Получить студентов, отвлекающихся на другие приложения"""
        if allowed_apps is None:
            allowed_apps = []
        
        distracted = []
        
        for student_id, report in self._reports.items():
            process = report.active_process.lower()
            
            # Проверяем на запрещённые приложения
            bad_apps = ['discord', 'telegram', 'steam', 'game', 'play']
            
            for bad in bad_apps:
                if bad in process and process not in [a.lower() for a in allowed_apps]:
                    distracted.append(student_id)
                    break
        
        return distracted


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест мониторинга активности...")
    print(f"Доступен: {ACTIVITY_MONITOR_AVAILABLE}")
    
    monitor = ActivityMonitor(report_interval=2)
    
    def on_report(report):
        print(f"\nОтчёт:")
        print(f"  Окно: {report.active_window[:50]}...")
        print(f"  Процесс: {report.active_process}")
        print(f"  Idle: {report.idle_time:.1f} сек")
        print(f"  Активен: {report.is_active}")
        print(f"  Окна: {len(report.open_windows)}")
    
    monitor.on_report = on_report
    
    monitor.start()
    
    import time as time_module
    time_module.sleep(10)
    
    monitor.stop()
    
    print("\nТест скриншота...")
    screenshot = ScreenshotCapture.capture()
    if screenshot:
        print(f"Скриншот: {len(screenshot)} символов base64")
    
    print("\nТест завершён!")




