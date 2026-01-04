"""
Тесты для модуля записи уроков
"""

import pytest
import sys
import os
import tempfile
import time
import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestLessonRecorder:
    """Тесты записи уроков"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.recording import LessonRecorder, RecordingConfig
        assert LessonRecorder is not None
        assert RecordingConfig is not None
    
    def test_recorder_creation(self):
        """Создание рекордера"""
        from src.recording import LessonRecorder, RecordingConfig
        
        config = RecordingConfig()
        recorder = LessonRecorder(config)
        
        assert recorder is not None
        assert recorder.recording == False
    
    def test_recording_lifecycle(self):
        """Жизненный цикл записи"""
        from src.recording import LessonRecorder
        
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = LessonRecorder()
            recorder.config.output_dir = tmpdir
            
            # Начать запись
            path = recorder.start_recording(
                lesson_name="Test Lesson",
                teacher_name="Test Teacher",
                students=["Student 1", "Student 2"]
            )
            
            assert path is not None
            assert recorder.recording == True
            assert recorder.metadata.lesson_name == "Test Lesson"
            
            # Добавляем данные
            test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', test_frame)
            
            for i in range(5):
                recorder.add_screen_frame(buffer.tobytes())
            
            recorder.add_chat_message("Teacher", "Hello", is_teacher=True)
            recorder.add_event("test_event", {"data": "test"})
            
            # Останавливаем
            final_path = recorder.stop_recording()
            
            assert final_path is not None
            assert recorder.recording == False
            assert recorder.metadata.frame_count == 5
            assert recorder.metadata.chat_messages == 1
            assert recorder.metadata.event_count == 1
    
    def test_metadata_saved(self):
        """Сохранение метаданных"""
        from src.recording import LessonRecorder
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = LessonRecorder()
            recorder.config.output_dir = tmpdir
            
            path = recorder.start_recording(
                lesson_name="Meta Test",
                teacher_name="Teacher",
                students=["S1", "S2", "S3"]
            )
            
            final_path = recorder.stop_recording()
            
            # Проверяем metadata.json
            from pathlib import Path
            metadata_file = Path(final_path) / "metadata.json"
            
            assert metadata_file.exists()
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            assert metadata['lesson_name'] == "Meta Test"
            assert metadata['teacher_name'] == "Teacher"
            assert metadata['student_count'] == 3


class TestLessonPlayer:
    """Тесты воспроизведения"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.recording import LessonPlayer
        assert LessonPlayer is not None


class TestVideoEncoder:
    """Тесты кодирования"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.recording import VideoEncoder
        assert VideoEncoder is not None
    
    def test_ffmpeg_check(self):
        """Проверка FFmpeg"""
        from src.recording.video_encoder import VideoEncoder
        
        encoder = VideoEncoder()
        # FFmpeg может быть установлен или нет
        assert isinstance(encoder.ffmpeg_available, bool)


class TestMulticast:
    """Тесты multicast"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.network.multicast import MulticastSender, MulticastReceiver
        assert MulticastSender is not None
        assert MulticastReceiver is not None
    
    def test_multicast_creation(self):
        """Создание multicast sender/receiver"""
        from src.network.multicast import MulticastSender, MulticastReceiver, MulticastConfig
        
        config = MulticastConfig()
        assert config.group == "239.255.1.1"
        assert config.port == 5005
        
        sender = MulticastSender(config)
        assert sender.running == True
        
        receiver = MulticastReceiver(config)
        assert receiver is not None
        
        # Очистка
        sender.close()
        receiver.stop()
    
    def test_multicast_send_receive(self):
        """Отправка и приём через multicast"""
        from src.network.multicast import MulticastSender, MulticastReceiver
        
        receiver = MulticastReceiver()
        
        received_data = []
        
        def on_data(data):
            received_data.append(data)
        
        receiver.on_data = on_data
        receiver.start()
        
        # Небольшая задержка для инициализации
        time.sleep(0.2)
        
        sender = MulticastSender()
        
        # Отправляем данные
        test_message = b"Test multicast message"
        sender.send(test_message)
        
        # Ждём получения
        time.sleep(0.5)
        
        # Очистка
        sender.close()
        receiver.stop()
        
        # Проверяем
        assert len(received_data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



