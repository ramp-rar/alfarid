"""
Блокировка ввода (клавиатура/мышь) на Windows
Версия 2.0

Использует:
1. Полноэкранный оверлей с перехватом событий
2. Установка фокуса и удержание окна поверх всех
"""

import logging
import sys
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Флаг доступности
INPUT_BLOCKER_AVAILABLE = False

try:
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        INPUT_BLOCKER_AVAILABLE = True
except ImportError:
    pass


class InputBlocker:
    """
    Блокировщик клавиатуры и мыши для Windows.
    
    Использует BlockInput API (требует права админа).
    Если права недоступны, просто логирует статус.
    """
    
    def __init__(self):
        self.blocked = False
        self._use_block_input = False
        
        # Колбэк при попытке ввода
        self.on_blocked_input: Optional[Callable[[], None]] = None
        
        logger.info(f"InputBlocker создан (доступен: {INPUT_BLOCKER_AVAILABLE})")
    
    def block(self) -> bool:
        """Заблокировать ввод"""
        if not INPUT_BLOCKER_AVAILABLE:
            logger.warning("Блокировка ввода недоступна (не Windows)")
            return False
        
        if self.blocked:
            return True
        
        self.blocked = True
        
        # Пробуем BlockInput (работает только с правами админа)
        try:
            user32 = ctypes.windll.user32
            result = user32.BlockInput(True)
            if result:
                self._use_block_input = True
                logger.info("Ввод заблокирован через BlockInput API")
                return True
            else:
                logger.debug("BlockInput не удался (нужны права админа)")
        except Exception as e:
            logger.debug(f"BlockInput ошибка: {e}")
        
        logger.info("Блокировка активирована (overlay режим)")
        return True
    
    def unblock(self):
        """Разблокировать ввод"""
        if not self.blocked:
            return
        
        self.blocked = False
        
        if self._use_block_input:
            try:
                user32 = ctypes.windll.user32
                user32.BlockInput(False)
                logger.info("BlockInput отключен")
            except Exception as e:
                logger.error(f"Ошибка отключения BlockInput: {e}")
            self._use_block_input = False
        
        logger.info("Ввод разблокирован")
    
    def is_blocked(self) -> bool:
        """Проверить статус блокировки"""
        return self.blocked


class ScreenLocker:
    """
    Полная блокировка экрана с оверлеем.
    
    Показывает полноэкранное окно которое:
    - Перехватывает все события клавиатуры (кроме Ctrl+Alt+Del)
    - Перехватывает все клики мыши
    - Остаётся поверх всех окон
    - Постоянно захватывает фокус
    """
    
    def __init__(self):
        self.locked = False
        self.overlay = None
        self.input_blocker = InputBlocker()
        self.message = "Экран заблокирован преподавателем"
        self._focus_timer = None
        
        logger.info("ScreenLocker создан")
    
    def lock(self, message: str = None, block_input: bool = True):
        """Заблокировать экран"""
        if self.locked:
            if message:
                self.update_message(message)
            return
        
        if message:
            self.message = message
        
        self.locked = True
        
        # Блокируем ввод через API (если есть права)
        if block_input:
            self.input_blocker.block()
        
        # Показываем оверлей который перехватывает события
        self._show_overlay()
        
        logger.info(f"Экран заблокирован: {self.message}")
    
    def unlock(self):
        """Разблокировать экран"""
        if not self.locked:
            return
        
        self.locked = False
        
        # Разблокируем ввод
        self.input_blocker.unblock()
        
        # Скрываем оверлей
        self._hide_overlay()
        
        logger.info("Экран разблокирован")
    
    def _show_overlay(self):
        """Показать оверлей блокировки с перехватом событий"""
        try:
            from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
            from PyQt5.QtCore import Qt, QTimer, QEvent
            from PyQt5.QtGui import QFont, QKeyEvent
            
            logger.info("Создание оверлея блокировки...")
            
            if self.overlay:
                logger.info("Закрытие предыдущего оверлея")
                self.overlay.close()
                self.overlay = None
            
            # Создаём оверлей с перехватом событий
            class LockOverlay(QWidget):
                def __init__(self, message, parent_locker):
                    super().__init__()
                    self.parent_locker = parent_locker
                    self.message = message
                    self.focus_timer = None
                    self._setup_ui()
                
                def _setup_ui(self):
                    # Флаги окна для максимальной блокировки
                    self.setWindowFlags(
                        Qt.WindowStaysOnTopHint | 
                        Qt.FramelessWindowHint | 
                        Qt.Window
                    )
                    
                    # Стиль
                    self.setStyleSheet("""
                        QWidget {
                            background: qlineargradient(
                                x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1a1a2e, stop:1 #16213e
                            );
                        }
                    """)
                    
                    layout = QVBoxLayout(self)
                    layout.setAlignment(Qt.AlignCenter)
                    
                    # Иконка замка
                    icon_label = QLabel("🔒")
                    icon_label.setAlignment(Qt.AlignCenter)
                    icon_label.setStyleSheet("font-size: 120pt; margin-bottom: 30px;")
                    layout.addWidget(icon_label)
                    
                    # Сообщение
                    self.msg_label = QLabel(self.message)
                    self.msg_label.setAlignment(Qt.AlignCenter)
                    self.msg_label.setWordWrap(True)
                    self.msg_label.setStyleSheet("""
                        color: white;
                        font-size: 32pt;
                        font-weight: bold;
                        padding: 20px;
                    """)
                    layout.addWidget(self.msg_label)
                    
                    # Подсказка
                    hint_label = QLabel("Ожидайте разблокировки преподавателем")
                    hint_label.setAlignment(Qt.AlignCenter)
                    hint_label.setStyleSheet("""
                        color: #888;
                        font-size: 16pt;
                        margin-top: 50px;
                    """)
                    layout.addWidget(hint_label)
                    
                    # Таймер для удержания фокуса
                    self.focus_timer = QTimer(self)
                    self.focus_timer.timeout.connect(self._grab_focus)
                    self.focus_timer.start(500)  # Каждые 500мс
                
                def _setup_event_blocking(self):
                    """Установить перехват событий"""
                    self.setMouseTracking(True)
                    try:
                        self.grabKeyboard()  # Захватить клавиатуру
                        logger.info("Клавиатура захвачена")
                    except Exception as e:
                        logger.warning(f"Не удалось захватить клавиатуру: {e}")
                    
                    # grabMouse может вызвать проблемы, вместо этого
                    # перехватываем события в mousePressEvent и т.д.
                    self.setFocus()
                
                def _grab_focus(self):
                    """Захватить фокус и поднять окно"""
                    if self.parent_locker.locked:
                        self.raise_()
                        self.activateWindow()
                        self.setFocus()
                        
                        # На Windows поднимаем окно поверх всех
                        if INPUT_BLOCKER_AVAILABLE:
                            try:
                                hwnd = int(self.winId())
                                user32 = ctypes.windll.user32
                                user32.SetWindowPos(
                                    hwnd, -1,  # HWND_TOPMOST
                                    0, 0, 0, 0,
                                    0x0001 | 0x0002  # SWP_NOSIZE | SWP_NOMOVE
                                )
                                user32.SetForegroundWindow(hwnd)
                            except:
                                pass
                
                def update_message(self, message):
                    self.message = message
                    self.msg_label.setText(message)
                
                # Перехватываем ВСЕ события клавиатуры
                def keyPressEvent(self, event):
                    # Блокируем все клавиши
                    event.accept()
                
                def keyReleaseEvent(self, event):
                    event.accept()
                
                # Перехватываем ВСЕ события мыши
                def mousePressEvent(self, event):
                    event.accept()
                
                def mouseReleaseEvent(self, event):
                    event.accept()
                
                def mouseDoubleClickEvent(self, event):
                    event.accept()
                
                def mouseMoveEvent(self, event):
                    event.accept()
                
                def wheelEvent(self, event):
                    event.accept()
                
                # Блокируем закрытие
                def closeEvent(self, event):
                    if self.parent_locker.locked:
                        event.ignore()
                    else:
                        if self.focus_timer:
                            self.focus_timer.stop()
                        try:
                            self.releaseKeyboard()
                        except:
                            pass
                        event.accept()
                
                # Блокируем Alt+F4 и другие системные комбинации
                def event(self, event):
                    if event.type() == QEvent.ShortcutOverride:
                        event.accept()
                        return True
                    return super().event(event)
            
            self.overlay = LockOverlay(self.message, self)
            self.overlay.showFullScreen()
            self.overlay.raise_()
            self.overlay.activateWindow()
            
            # Захватываем клавиатуру и мышь после показа окна
            QTimer.singleShot(100, self.overlay._setup_event_blocking)
            QTimer.singleShot(200, self.overlay._grab_focus)
            
            logger.info("Оверлей блокировки показан")
            
        except Exception as e:
            logger.error(f"Ошибка показа оверлея: {e}")
            import traceback
            traceback.print_exc()
    
    def _hide_overlay(self):
        """Скрыть оверлей"""
        if self.overlay:
            try:
                if self.overlay.focus_timer:
                    self.overlay.focus_timer.stop()
                try:
                    self.overlay.releaseKeyboard()
                except:
                    pass
                self.overlay.close()
                self.overlay.deleteLater()
                logger.info("Оверлей блокировки скрыт")
            except Exception as e:
                logger.error(f"Ошибка скрытия оверлея: {e}")
            self.overlay = None
    
    def update_message(self, message: str):
        """Обновить сообщение"""
        self.message = message
        if self.locked and self.overlay:
            try:
                self.overlay.update_message(message)
            except:
                pass


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест блокировки экрана...")
    print(f"Доступно: {INPUT_BLOCKER_AVAILABLE}")
    
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    locker = ScreenLocker()
    
    print("Блокировка на 5 секунд...")
    locker.lock("Тестовая блокировка экрана")
    
    # Таймер для разблокировки
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(5000, lambda: locker.unlock())
    QTimer.singleShot(5100, app.quit)
    
    app.exec_()
    
    print("Тест завершён!")
