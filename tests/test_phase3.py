"""
Тесты для Фазы 3: Управление классом
"""

import pytest
import sys
import os
import base64
import tempfile
import time

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestInputBlocker:
    """Тесты блокировки ввода"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.control.input_blocker import (
            InputBlocker, ScreenLocker, INPUT_BLOCKER_AVAILABLE
        )
        assert InputBlocker is not None
        assert ScreenLocker is not None
    
    def test_input_blocker_creation(self):
        """Создание блокировщика"""
        from src.control.input_blocker import InputBlocker
        
        blocker = InputBlocker()
        assert blocker.blocked == False
    
    def test_screen_locker_creation(self):
        """Создание блокировщика экрана"""
        from src.control.input_blocker import ScreenLocker
        
        locker = ScreenLocker()
        assert locker.locked == False
        assert locker.message == "Экран заблокирован преподавателем"


class TestWebControl:
    """Тесты веб-контроля"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.control.web_control import (
            WebAccessMode, WebControlConfig, WebAccessController, WebControlClient
        )
        assert WebAccessMode is not None
        assert WebControlConfig is not None
    
    def test_web_access_modes(self):
        """Проверка режимов доступа"""
        from src.control.web_control import WebAccessMode
        
        assert WebAccessMode.FULL_ACCESS.value == "full_access"
        assert WebAccessMode.WHITELIST.value == "whitelist"
        assert WebAccessMode.BLACKLIST.value == "blacklist"
        assert WebAccessMode.NO_ACCESS.value == "no_access"
    
    def test_web_config_defaults(self):
        """Конфигурация по умолчанию"""
        from src.control.web_control import WebControlConfig
        
        config = WebControlConfig()
        assert config.mode == "full_access"
        assert config.whitelist == []
        assert config.blacklist == []
        assert len(config.educational_sites) > 0
        assert len(config.social_sites) > 0
    
    def test_web_controller_full_access(self):
        """Полный доступ"""
        from src.control.web_control import WebAccessController
        
        ctrl = WebAccessController()
        ctrl.set_full_access()
        
        assert ctrl.config.mode == "full_access"
        assert ctrl.is_allowed("https://vk.com") == True
        assert ctrl.is_allowed("https://google.com") == True
    
    def test_web_controller_no_access(self):
        """Заблокировать всё"""
        from src.control.web_control import WebAccessController
        
        ctrl = WebAccessController()
        ctrl.set_no_access()
        
        assert ctrl.config.mode == "no_access"
        assert ctrl.is_allowed("https://vk.com") == False
        assert ctrl.is_allowed("https://google.com") == False
    
    def test_web_controller_whitelist(self):
        """Белый список"""
        from src.control.web_control import WebAccessController
        
        ctrl = WebAccessController()
        ctrl.set_whitelist(["google.com", "wikipedia.org"])
        
        assert ctrl.config.mode == "whitelist"
        assert ctrl.is_allowed("https://google.com/search") == True
        assert ctrl.is_allowed("https://vk.com") == False
    
    def test_web_controller_blacklist(self):
        """Чёрный список"""
        from src.control.web_control import WebAccessController
        
        ctrl = WebAccessController()
        ctrl.set_blacklist(["vk.com", "facebook.com"])
        
        assert ctrl.config.mode == "blacklist"
        assert ctrl.is_allowed("https://google.com") == True
        assert ctrl.is_allowed("https://vk.com") == False
    
    def test_web_controller_educational(self):
        """Только образовательные сайты"""
        from src.control.web_control import WebAccessController
        
        ctrl = WebAccessController()
        ctrl.set_educational_only()
        
        assert ctrl.config.mode == "whitelist"
        assert ctrl.is_allowed("https://wikipedia.org") == True
        assert ctrl.is_allowed("https://tiktok.com") == False
    
    def test_web_client_apply_config(self):
        """Клиент применяет конфигурацию"""
        from src.control.web_control import WebAccessController, WebControlClient
        
        ctrl = WebAccessController()
        ctrl.set_blacklist(["vk.com"])
        
        client = WebControlClient()
        client.apply_config(ctrl.get_config())
        
        assert client.enabled == True
        assert client.is_url_allowed("https://google.com") == True
        assert client.is_url_allowed("https://vk.com") == False
    
    def test_web_client_description(self):
        """Описание режима"""
        from src.control.web_control import WebControlClient
        
        client = WebControlClient()
        
        # По умолчанию
        assert "Полный" in client.get_mode_description()
        
        # Whitelist
        client.apply_config({'mode': 'whitelist', 'whitelist': ['a', 'b'], 'blacklist': []})
        assert "2 сайтам" in client.get_mode_description()


class TestFileTransfer:
    """Тесты передачи файлов"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.files import FileSender, FileReceiver, FileCollector, FileTransferInfo
        assert FileSender is not None
        assert FileReceiver is not None
    
    def test_transfer_info(self):
        """Информация о передаче"""
        from src.files import FileTransferInfo
        
        info = FileTransferInfo(
            transfer_id="test123",
            filename="test.txt",
            file_size=1000,
            file_hash="abc123",
            total_chunks=10,
            received_chunks=5
        )
        
        assert info.progress == 50.0
        assert info.is_complete == False
        
        info.received_chunks = 10
        assert info.is_complete == True
    
    def test_file_sender_creation(self):
        """Создание отправителя"""
        from src.files import FileSender
        
        sender = FileSender()
        assert sender is not None
    
    def test_file_receiver_creation(self):
        """Создание получателя"""
        from src.files import FileReceiver
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            receiver = FileReceiver(save_dir=tmpdir)
            assert receiver is not None
            assert receiver.save_dir.exists()
    
    def test_file_send_receive(self):
        """Полный цикл отправки-получения"""
        from src.files import FileSender, FileReceiver
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаём тестовый файл
            test_file = os.path.join(tmpdir, "test.txt")
            test_content = "Hello, World!" * 100
            
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            # Настраиваем отправителя и получателя
            sender = FileSender()
            receiver = FileReceiver(save_dir=os.path.join(tmpdir, "received"))
            
            received_complete = [False]
            
            def on_start(info):
                receiver.start_transfer(
                    info.transfer_id,
                    info.filename,
                    info.file_size,
                    info.file_hash,
                    info.total_chunks
                )
            
            def on_chunk(transfer_id, chunk_num, data, total):
                receiver.add_chunk(transfer_id, chunk_num, data)
            
            def on_complete(info):
                received_complete[0] = True
            
            sender.on_transfer_start = on_start
            sender.on_chunk = on_chunk
            receiver.on_complete = on_complete
            
            # Отправляем
            transfer_id = sender.send_file(test_file)
            assert transfer_id is not None
            
            # Ждём завершения
            time.sleep(1)
            
            # Проверяем
            info = receiver.get_transfer_info(transfer_id)
            assert info is not None
    
    def test_file_collector_creation(self):
        """Создание сборщика"""
        from src.files import FileCollector
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = FileCollector(save_dir=tmpdir)
            assert collector is not None
            
            # Начинаем сбор
            collection_id = collector.start_collection("Тест")
            assert collection_id is not None
            
            # Добавляем файл
            test_data = base64.b64encode(b"Test content").decode()
            path = collector.add_file(
                collection_id, 
                "student1", 
                "Иванов Иван",
                "homework.txt",
                test_data
            )
            assert path is not None
            
            # Статус
            status = collector.get_collection_status(collection_id)
            assert status['files_count'] == 1


class TestActivityMonitor:
    """Тесты мониторинга активности"""
    
    def test_import(self):
        """Проверка импорта"""
        from src.control.activity_monitor import (
            ActivityMonitor, ActivityReport, ActivityTracker,
            ScreenshotCapture, ACTIVITY_MONITOR_AVAILABLE
        )
        assert ActivityMonitor is not None
        assert ActivityReport is not None
    
    def test_activity_report_creation(self):
        """Создание отчёта"""
        from src.control.activity_monitor import ActivityReport
        
        report = ActivityReport(
            active_window="Test Window",
            active_process="test.exe",
            idle_time=30
        )
        
        assert report.active_window == "Test Window"
        assert report.is_active == True  # idle_time < 60
        
        data = report.to_dict()
        assert 'active_window' in data
        assert 'active_process' in data
    
    def test_activity_monitor_creation(self):
        """Создание монитора"""
        from src.control.activity_monitor import ActivityMonitor
        
        monitor = ActivityMonitor(report_interval=5)
        assert monitor.monitoring == False
    
    def test_activity_tracker_creation(self):
        """Создание трекера"""
        from src.control.activity_monitor import ActivityTracker
        
        tracker = ActivityTracker()
        
        # Обновляем отчёт
        tracker.update_report("student1", {
            'active_window': "Chrome",
            'active_process': "chrome.exe",
            'idle_time': 10,
            'is_active': True
        })
        
        # Получаем
        report = tracker.get_report("student1")
        assert report is not None
        assert report.active_window == "Chrome"
    
    def test_activity_tracker_inactive_students(self):
        """Определение неактивных студентов"""
        from src.control.activity_monitor import ActivityTracker
        
        tracker = ActivityTracker()
        
        # Активный студент
        tracker.update_report("student1", {
            'active_window': "Chrome",
            'idle_time': 10,
            'is_active': True
        })
        
        # Неактивный студент
        tracker.update_report("student2", {
            'active_window': "",
            'idle_time': 120,
            'is_active': False
        })
        
        inactive = tracker.get_inactive_students(threshold=60)
        assert "student2" in inactive
        assert "student1" not in inactive


class TestClassroomControl:
    """Тесты управления классом"""
    
    def test_web_access_control_exists(self):
        """WebAccessControl в classroom_control"""
        from src.control.classroom_control import WebAccessControl
        
        ctrl = WebAccessControl()
        assert ctrl.mode == "full_access"
    
    def test_web_access_control_whitelist(self):
        """Белый список"""
        from src.control.classroom_control import WebAccessControl
        
        ctrl = WebAccessControl()
        ctrl.set_whitelist_mode(["google.com"])
        
        assert ctrl.mode == "whitelist"
        assert ctrl.is_allowed("https://google.com/search") == True
        assert ctrl.is_allowed("https://vk.com") == False
    
    def test_web_access_control_blacklist(self):
        """Чёрный список"""
        from src.control.classroom_control import WebAccessControl
        
        ctrl = WebAccessControl()
        ctrl.set_blacklist_mode(["vk.com"])
        
        assert ctrl.mode == "blacklist"
        assert ctrl.is_allowed("https://google.com") == True
        assert ctrl.is_allowed("https://vk.com/feed") == False


class TestMessageTypes:
    """Тесты типов сообщений"""
    
    def test_phase3_message_types(self):
        """Проверка типов сообщений Фазы 3"""
        from src.common.constants import MessageType
        
        # Блокировка
        assert MessageType.LOCK_SCREEN == "LOCK_SCREEN"
        assert MessageType.UNLOCK_SCREEN == "UNLOCK_SCREEN"
        assert MessageType.LOCK_INPUT == "LOCK_INPUT"
        assert MessageType.UNLOCK_INPUT == "UNLOCK_INPUT"
        
        # Веб-контроль
        assert MessageType.WEB_CONTROL_SET == "WEB_CONTROL_SET"
        
        # Файлы
        assert MessageType.FILE_TRANSFER_START == "FILE_TRANSFER_START"
        assert MessageType.FILE_TRANSFER_DATA == "FILE_TRANSFER_DATA"
        assert MessageType.FILE_TRANSFER_END == "FILE_TRANSFER_END"
        
        # Мониторинг
        assert MessageType.ACTIVITY_REPORT == "ACTIVITY_REPORT"
        assert MessageType.SCREENSHOT_REQUEST == "SCREENSHOT_REQUEST"
        assert MessageType.SCREENSHOT_RESPONSE == "SCREENSHOT_RESPONSE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




