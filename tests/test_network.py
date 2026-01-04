"""
Тесты для сетевого слоя Alfarid
"""

import unittest
import sys
import os
import time
import threading

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.network.protocol import Protocol, TCPPacketAssembler, MessageBuilder
from src.common.constants import MessageType


class TestProtocol(unittest.TestCase):
    """Тесты протокола"""
    
    def test_pack_unpack_simple(self):
        """Тест упаковки/распаковки простого сообщения"""
        msg_type = MessageType.PING
        data = {"test": "value"}
        
        packed = Protocol.pack(msg_type, data)
        self.assertIsInstance(packed, bytes)
        self.assertGreater(len(packed), Protocol.HEADER_SIZE)
        
        unpacked = Protocol.unpack(packed)
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked["type"], msg_type)
        self.assertEqual(unpacked["data"]["test"], "value")
    
    def test_pack_unpack_large_data(self):
        """Тест упаковки/распаковки больших данных (с компрессией)"""
        msg_type = "TEST_LARGE"
        data = {"large": "x" * 10000}  # 10KB строка
        
        packed = Protocol.pack(msg_type, data, compress=True)
        self.assertIsInstance(packed, bytes)
        
        # Проверяем что данные сжаты (меньше оригинала)
        self.assertLess(len(packed), 10000 + Protocol.HEADER_SIZE)
        
        unpacked = Protocol.unpack(packed)
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked["type"], msg_type)
        self.assertEqual(len(unpacked["data"]["large"]), 10000)
    
    def test_magic_number(self):
        """Тест magic number"""
        packed = Protocol.pack(MessageType.PING, {})
        
        # Проверяем magic
        self.assertEqual(packed[:4], Protocol.MAGIC)
    
    def test_get_packet_length(self):
        """Тест получения длины пакета"""
        packed = Protocol.pack(MessageType.PING, {"key": "value"})
        
        length = Protocol.get_packet_length(packed[:Protocol.HEADER_SIZE])
        self.assertEqual(length, len(packed))
    
    def test_unpack_invalid_data(self):
        """Тест распаковки некорректных данных"""
        # Случайные данные
        result = Protocol.unpack(b'random garbage data')
        self.assertIsNone(result)
        
        # Слишком короткие данные
        result = Protocol.unpack(b'short')
        self.assertIsNone(result)
        
        # Пустые данные
        result = Protocol.unpack(b'')
        self.assertIsNone(result)


class TestTCPPacketAssembler(unittest.TestCase):
    """Тесты сборщика TCP пакетов"""
    
    def test_single_packet(self):
        """Тест сборки одного пакета"""
        assembler = TCPPacketAssembler()
        
        packed = Protocol.pack(MessageType.PING, {})
        packets = assembler.feed(packed)
        
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0], packed)
    
    def test_multiple_packets_at_once(self):
        """Тест сборки нескольких пакетов пришедших вместе"""
        assembler = TCPPacketAssembler()
        
        packet1 = Protocol.pack(MessageType.PING, {})
        packet2 = Protocol.pack(MessageType.PONG, {})
        packet3 = Protocol.pack("TEST", {"key": "value"})
        
        # Отправляем все вместе
        combined = packet1 + packet2 + packet3
        packets = assembler.feed(combined)
        
        self.assertEqual(len(packets), 3)
        self.assertEqual(packets[0], packet1)
        self.assertEqual(packets[1], packet2)
        self.assertEqual(packets[2], packet3)
    
    def test_fragmented_packet(self):
        """Тест сборки фрагментированного пакета"""
        assembler = TCPPacketAssembler()
        
        packed = Protocol.pack(MessageType.PING, {"data": "x" * 1000})
        
        # Разбиваем на фрагменты
        chunk1 = packed[:20]
        chunk2 = packed[20:50]
        chunk3 = packed[50:]
        
        # Первый фрагмент - пакет еще не готов
        packets = assembler.feed(chunk1)
        self.assertEqual(len(packets), 0)
        
        # Второй фрагмент - все еще не готов
        packets = assembler.feed(chunk2)
        self.assertEqual(len(packets), 0)
        
        # Третий фрагмент - теперь готов
        packets = assembler.feed(chunk3)
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0], packed)
    
    def test_mixed_complete_and_fragmented(self):
        """Тест смешанных полных и фрагментированных пакетов"""
        assembler = TCPPacketAssembler()
        
        packet1 = Protocol.pack(MessageType.PING, {})
        packet2 = Protocol.pack(MessageType.PONG, {"data": "test"})
        
        # Первый полный пакет + начало второго
        data1 = packet1 + packet2[:10]
        packets = assembler.feed(data1)
        self.assertEqual(len(packets), 1)
        
        # Остаток второго пакета
        data2 = packet2[10:]
        packets = assembler.feed(data2)
        self.assertEqual(len(packets), 1)
    
    def test_sync_recovery(self):
        """Тест восстановления синхронизации после мусора"""
        assembler = TCPPacketAssembler()
        
        garbage = b'some garbage data that should be skipped'
        valid_packet = Protocol.pack(MessageType.PING, {})
        
        # Мусор + валидный пакет
        data = garbage + valid_packet
        packets = assembler.feed(data)
        
        # Должен найти валидный пакет после мусора
        self.assertEqual(len(packets), 1)
        
        # Проверяем статистику
        stats = assembler.get_stats()
        self.assertEqual(stats['sync_recoveries'], 1)
    
    def test_large_packet(self):
        """Тест сборки большого пакета (имитация кадра экрана)"""
        assembler = TCPPacketAssembler()
        
        # Создаем большой пакет (~100KB)
        large_data = "x" * 100000
        packed = Protocol.pack("SCREEN_FRAME", {"frame": large_data})
        
        # Разбиваем на чанки как TCP
        chunk_size = 65536  # Типичный размер TCP буфера
        offset = 0
        all_packets = []
        
        while offset < len(packed):
            chunk = packed[offset:offset + chunk_size]
            packets = assembler.feed(chunk)
            all_packets.extend(packets)
            offset += chunk_size
        
        # Должен получить ровно 1 пакет
        self.assertEqual(len(all_packets), 1)
        
        # Проверяем что он правильно распаковывается
        unpacked = Protocol.unpack(all_packets[0])
        self.assertIsNotNone(unpacked)
        self.assertEqual(len(unpacked["data"]["frame"]), 100000)
    
    def test_stats(self):
        """Тест статистики сборщика"""
        assembler = TCPPacketAssembler()
        
        packet1 = Protocol.pack(MessageType.PING, {})
        packet2 = Protocol.pack(MessageType.PONG, {})
        
        assembler.feed(packet1)
        assembler.feed(packet2)
        
        stats = assembler.get_stats()
        self.assertEqual(stats['packets_assembled'], 2)
        self.assertEqual(stats['bytes_processed'], len(packet1) + len(packet2))


class TestMessageBuilder(unittest.TestCase):
    """Тесты построителя сообщений"""
    
    def test_ping(self):
        """Тест создания PING"""
        packet = MessageBuilder.ping()
        unpacked = Protocol.unpack(packet)
        self.assertEqual(unpacked["type"], MessageType.PING)
    
    def test_pong(self):
        """Тест создания PONG"""
        packet = MessageBuilder.pong()
        unpacked = Protocol.unpack(packet)
        self.assertEqual(unpacked["type"], MessageType.PONG)
    
    def test_teacher_broadcast(self):
        """Тест создания TEACHER_BROADCAST"""
        packet = MessageBuilder.teacher_broadcast("Иванов И.В.", 1, 9999)
        unpacked = Protocol.unpack(packet)
        
        self.assertEqual(unpacked["type"], MessageType.TEACHER_BROADCAST)
        self.assertEqual(unpacked["data"]["teacher_name"], "Иванов И.В.")
        self.assertEqual(unpacked["data"]["channel"], 1)
        self.assertEqual(unpacked["data"]["port"], 9999)
    
    def test_student_connect(self):
        """Тест создания STUDENT_CONNECT"""
        packet = MessageBuilder.student_connect("Петров П.П.", "machine123")
        unpacked = Protocol.unpack(packet)
        
        self.assertEqual(unpacked["type"], MessageType.STUDENT_CONNECT)
        self.assertEqual(unpacked["data"]["student_name"], "Петров П.П.")
        self.assertEqual(unpacked["data"]["machine_id"], "machine123")
    
    def test_chat_message(self):
        """Тест создания CHAT_MESSAGE"""
        packet = MessageBuilder.chat_message(
            sender_id="student1",
            sender_name="Петров",
            content="Привет!",
            recipient_id="teacher"
        )
        unpacked = Protocol.unpack(packet)
        
        self.assertEqual(unpacked["type"], MessageType.CHAT_MESSAGE)
        self.assertEqual(unpacked["data"]["content"], "Привет!")
    
    def test_lock_screen(self):
        """Тест создания LOCK_SCREEN"""
        packet = MessageBuilder.lock_screen("Внимание на преподавателя!")
        unpacked = Protocol.unpack(packet)
        
        self.assertEqual(unpacked["type"], MessageType.LOCK_SCREEN)
        self.assertEqual(unpacked["data"]["message"], "Внимание на преподавателя!")


class TestCyrillicSupport(unittest.TestCase):
    """Тесты поддержки кириллицы"""
    
    def test_cyrillic_in_message(self):
        """Тест кириллицы в сообщениях"""
        msg_type = "ТЕСТ"
        data = {
            "имя": "Иванов Иван Иванович",
            "сообщение": "Привет мир! 你好世界! مرحبا بالعالم"
        }
        
        packed = Protocol.pack(msg_type, data)
        unpacked = Protocol.unpack(packed)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked["type"], msg_type)
        self.assertEqual(unpacked["data"]["имя"], data["имя"])
        self.assertEqual(unpacked["data"]["сообщение"], data["сообщение"])


if __name__ == '__main__':
    # Запускаем тесты с подробным выводом
    unittest.main(verbosity=2)

