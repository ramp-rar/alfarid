"""
Тесты для компонентов Фазы 2:
- Голосовая связь
- Веб-камера
- Интерактивная доска
"""

import pytest
import time
import base64
from unittest.mock import MagicMock, patch


class TestVoiceStream:
    """Тесты голосовой связи"""
    
    def test_voice_settings_default(self):
        """Проверка настроек по умолчанию"""
        from src.audio.voice_stream import VoiceSettings
        
        settings = VoiceSettings()
        
        assert settings.sample_rate == 16000
        assert settings.channels == 1
        assert settings.chunk_duration == 0.05
        assert settings.chunk_size == 800  # 16000 * 0.05
    
    def test_voice_settings_custom(self):
        """Проверка кастомных настроек"""
        from src.audio.voice_stream import VoiceSettings
        
        settings = VoiceSettings(sample_rate=44100, channels=2, chunk_duration=0.1)
        
        assert settings.sample_rate == 44100
        assert settings.channels == 2
        assert settings.chunk_size == 4410  # 44100 * 0.1
    
    @pytest.mark.skipif(True, reason="Требуется микрофон")
    def test_voice_capture_start_stop(self):
        """Тест запуска/остановки захвата голоса"""
        from src.audio.voice_stream import VoiceCapture
        
        capture = VoiceCapture()
        
        assert capture.start() == True
        assert capture.capturing == True
        
        time.sleep(0.5)
        capture.stop()
        
        assert capture.capturing == False
    
    @pytest.mark.skipif(True, reason="Требуется аудио устройство")
    def test_voice_playback_start_stop(self):
        """Тест запуска/остановки воспроизведения"""
        from src.audio.voice_stream import VoicePlayback
        
        playback = VoicePlayback()
        
        assert playback.start() == True
        assert playback.playing == True
        
        playback.stop()
        
        assert playback.playing == False
    
    def test_voice_broadcaster_creation(self):
        """Тест создания VoiceBroadcaster"""
        from src.audio.voice_stream import VoiceBroadcaster, VoiceSettings
        
        settings = VoiceSettings(sample_rate=22050)
        broadcaster = VoiceBroadcaster(settings)
        
        assert broadcaster.settings.sample_rate == 22050
        assert broadcaster.active == False
    
    def test_voice_receiver_creation(self):
        """Тест создания VoiceReceiver"""
        from src.audio.voice_stream import VoiceReceiver, VoiceSettings
        
        settings = VoiceSettings(sample_rate=22050)
        receiver = VoiceReceiver(settings)
        
        assert receiver.settings.sample_rate == 22050
        assert receiver.active == False


class TestWebcamCapture:
    """Тесты веб-камеры"""
    
    def test_webcam_settings_default(self):
        """Проверка настроек камеры по умолчанию"""
        from src.streaming.webcam_capture import WebcamSettings
        
        settings = WebcamSettings()
        
        assert settings.camera_index == 0
        assert settings.width == 640
        assert settings.height == 480
        assert settings.fps == 15
        assert settings.quality == 70
        assert settings.resolution == (640, 480)
    
    def test_webcam_settings_custom(self):
        """Проверка кастомных настроек камеры"""
        from src.streaming.webcam_capture import WebcamSettings
        
        settings = WebcamSettings(
            camera_index=1,
            width=1280,
            height=720,
            fps=30,
            quality=85
        )
        
        assert settings.camera_index == 1
        assert settings.width == 1280
        assert settings.height == 720
        assert settings.fps == 30
        assert settings.quality == 85
    
    def test_webcam_list_cameras(self):
        """Тест получения списка камер"""
        from src.streaming.webcam_capture import WebcamCapture
        
        # Просто проверяем, что метод работает без ошибок
        cameras = WebcamCapture.list_cameras()
        assert isinstance(cameras, list)
    
    @pytest.mark.skipif(True, reason="Требуется камера")
    def test_webcam_capture_start_stop(self):
        """Тест запуска/остановки захвата камеры"""
        from src.streaming.webcam_capture import WebcamCapture
        
        webcam = WebcamCapture()
        
        if webcam.start():
            assert webcam.capturing == True
            time.sleep(0.5)
            webcam.stop()
            assert webcam.capturing == False
    
    def test_webcam_receiver_creation(self):
        """Тест создания WebcamReceiver"""
        from src.streaming.webcam_capture import WebcamReceiver
        
        receiver = WebcamReceiver()
        
        assert receiver._current_frame is None
        assert receiver._frame_id == 0
    
    def test_webcam_receiver_process_frame(self):
        """Тест обработки кадра"""
        from src.streaming.webcam_capture import WebcamReceiver
        import cv2
        import numpy as np
        
        receiver = WebcamReceiver()
        
        # Создаем тестовый кадр
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[:, :, 2] = 255  # Красный
        
        # Кодируем в JPEG
        _, encoded = cv2.imencode('.jpg', test_frame)
        frame_bytes = encoded.tobytes()
        
        # Обрабатываем
        receiver.process_frame(frame_bytes, 1)
        
        assert receiver._frame_id == 1
        assert receiver._frames_received == 1
        assert receiver._current_frame is not None
        assert receiver._current_frame.shape == (480, 640, 3)
    
    def test_webcam_broadcaster_creation(self):
        """Тест создания WebcamBroadcaster"""
        from src.streaming.webcam_capture import WebcamBroadcaster, WebcamSettings
        
        settings = WebcamSettings(fps=30)
        broadcaster = WebcamBroadcaster(settings)
        
        assert broadcaster.settings.fps == 30
        assert broadcaster.active == False


class TestWhiteboard:
    """Тесты интерактивной доски"""
    
    def test_tool_enum(self):
        """Тест enum инструментов"""
        from src.whiteboard import Tool
        
        assert Tool.PEN.value == "pen"
        assert Tool.ERASER.value == "eraser"
        assert Tool.HIGHLIGHTER.value == "highlighter"
        assert Tool.LINE.value == "line"
        assert Tool.RECTANGLE.value == "rectangle"
        assert Tool.ELLIPSE.value == "ellipse"
        assert Tool.ARROW.value == "arrow"
    
    def test_draw_command_creation(self):
        """Тест создания DrawCommand"""
        from src.whiteboard import DrawCommand
        
        cmd = DrawCommand(
            tool="pen",
            color="#FF0000",
            width=5,
            points=[(10, 10), (20, 20), (30, 30)],
            command_id=1
        )
        
        assert cmd.tool == "pen"
        assert cmd.color == "#FF0000"
        assert cmd.width == 5
        assert len(cmd.points) == 3
        assert cmd.command_id == 1
    
    @pytest.mark.skipif(True, reason="Требуется Qt")
    def test_whiteboard_canvas_init(self):
        """Тест инициализации холста"""
        from PyQt5.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        from src.whiteboard import WhiteboardCanvas
        
        canvas = WhiteboardCanvas(readonly=False)
        
        assert canvas.readonly == False
        assert canvas.canvas_pixmap is not None
        assert canvas.current_tool.value == "pen"
    
    @pytest.mark.skipif(True, reason="Требуется Qt")
    def test_whiteboard_canvas_readonly(self):
        """Тест readonly холста"""
        from PyQt5.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        from src.whiteboard import WhiteboardCanvas
        
        canvas = WhiteboardCanvas(readonly=True)
        
        assert canvas.readonly == True
    
    @pytest.mark.skipif(True, reason="Требуется Qt")
    def test_whiteboard_widget_creation(self):
        """Тест создания виджета доски"""
        from PyQt5.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        from src.whiteboard import WhiteboardWidget
        
        widget = WhiteboardWidget(readonly=False)
        
        assert hasattr(widget, 'canvas')
        assert hasattr(widget, 'toolbar')
    
    @pytest.mark.skipif(True, reason="Требуется Qt")
    def test_whiteboard_readonly_no_toolbar(self):
        """Тест readonly доски без панели инструментов"""
        from PyQt5.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        from src.whiteboard import WhiteboardWidget
        
        widget = WhiteboardWidget(readonly=True)
        
        assert hasattr(widget, 'canvas')
        assert not hasattr(widget, 'toolbar')


class TestMessageTypes:
    """Тест новых типов сообщений"""
    
    def test_voice_message_types(self):
        """Тест типов сообщений голосовой связи"""
        from src.common.constants import MessageType
        
        assert hasattr(MessageType, 'VOICE_START')
        assert hasattr(MessageType, 'VOICE_STOP')
        assert hasattr(MessageType, 'VOICE_DATA')
        
        assert MessageType.VOICE_START == "VOICE_START"
        assert MessageType.VOICE_STOP == "VOICE_STOP"
        assert MessageType.VOICE_DATA == "VOICE_DATA"
    
    def test_webcam_message_types(self):
        """Тест типов сообщений веб-камеры"""
        from src.common.constants import MessageType
        
        assert hasattr(MessageType, 'WEBCAM_START')
        assert hasattr(MessageType, 'WEBCAM_STOP')
        assert hasattr(MessageType, 'WEBCAM_FRAME')
        
        assert MessageType.WEBCAM_START == "WEBCAM_START"
        assert MessageType.WEBCAM_STOP == "WEBCAM_STOP"
        assert MessageType.WEBCAM_FRAME == "WEBCAM_FRAME"
    
    def test_whiteboard_message_types(self):
        """Тест типов сообщений интерактивной доски"""
        from src.common.constants import MessageType
        
        assert hasattr(MessageType, 'WHITEBOARD_START')
        assert hasattr(MessageType, 'WHITEBOARD_STOP')
        assert hasattr(MessageType, 'WHITEBOARD_COMMAND')
        assert hasattr(MessageType, 'WHITEBOARD_SYNC')
        
        assert MessageType.WHITEBOARD_START == "WHITEBOARD_START"
        assert MessageType.WHITEBOARD_STOP == "WHITEBOARD_STOP"
        assert MessageType.WHITEBOARD_COMMAND == "WHITEBOARD_COMMAND"
        assert MessageType.WHITEBOARD_SYNC == "WHITEBOARD_SYNC"


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_audio_import(self):
        """Тест импорта аудио модуля"""
        from src.audio.voice_stream import (
            VoiceSettings,
            VoiceCapture,
            VoicePlayback,
            VoiceBroadcaster,
            VoiceReceiver,
            AUDIO_AVAILABLE
        )
        
        assert VoiceSettings is not None
        assert VoiceCapture is not None
    
    def test_webcam_import(self):
        """Тест импорта модуля камеры"""
        from src.streaming.webcam_capture import (
            WebcamSettings,
            WebcamCapture,
            WebcamReceiver,
            WebcamBroadcaster,
            CV2_AVAILABLE
        )
        
        assert WebcamSettings is not None
        assert WebcamCapture is not None
    
    def test_whiteboard_import(self):
        """Тест импорта модуля доски"""
        from src.whiteboard import (
            WhiteboardWidget,
            WhiteboardCanvas,
            WhiteboardToolbar,
            Tool,
            DrawCommand
        )
        
        assert WhiteboardWidget is not None
        assert Tool.PEN is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

