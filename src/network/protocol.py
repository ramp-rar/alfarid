"""
Протокол обмена сообщениями между преподавателем и студентами
Версия 2.0 - с надежной TCP буферизацией
"""

import struct
import zlib
import logging
from typing import Dict, Any, Optional, List
from src.common.utils import serialize_message, deserialize_message


logger = logging.getLogger(__name__)


class Protocol:
    """Класс для работы с протоколом передачи данных"""
    
    # Заголовок пакета: MAGIC (4 байта) + VERSION (2 байта) + LENGTH (4 байта) + COMPRESSED (1 байт)
    MAGIC = b'AFRD'  # Alfarid (было LNGC)
    VERSION = 2  # Версия 2 с буферизацией
    HEADER_SIZE = 11
    HEADER_FORMAT = '!4sHIB'  # Big-endian: 4 байта, 2 байта, 4 байта, 1 байт
    
    # Максимальный размер пакета (10 MB)
    MAX_PACKET_SIZE = 10 * 1024 * 1024
    
    @classmethod
    def pack(cls, msg_type: str, data: Dict[str, Any], compress: bool = True) -> bytes:
        """
        Упаковать сообщение в бинарный формат
        
        Args:
            msg_type: Тип сообщения
            data: Данные сообщения
            compress: Сжимать ли данные
            
        Returns:
            Упакованные данные
        """
        try:
            # Сериализуем данные
            payload = serialize_message(msg_type, data)
            
            # Сжимаем если нужно и размер больше 1KB
            if compress and len(payload) > 1024:
                payload = zlib.compress(payload, level=6)
                compressed_flag = 1
            else:
                compressed_flag = 0
            
            # Создаем заголовок
            header = struct.pack(
                cls.HEADER_FORMAT,
                cls.MAGIC,
                cls.VERSION,
                len(payload),
                compressed_flag
            )
            
            return header + payload
            
        except Exception as e:
            logger.error(f"Ошибка упаковки сообщения: {e}")
            return b''
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Распаковать сообщение из бинарного формата
        
        Args:
            data: Бинарные данные (полный пакет включая заголовок)
            
        Returns:
            Распакованное сообщение или None при ошибке
        """
        try:
            # Проверяем минимальный размер
            if len(data) < cls.HEADER_SIZE:
                logger.error("Пакет слишком маленький")
                return None
            
            # Распаковываем заголовок
            header = data[:cls.HEADER_SIZE]
            magic, version, length, compressed = struct.unpack(cls.HEADER_FORMAT, header)
            
            # Проверяем magic number
            if magic != cls.MAGIC:
                logger.error(f"Неверный magic number: {magic}")
                return None
            
            # Проверяем версию (принимаем версию 1 и 2)
            if version not in (1, 2):
                logger.warning(f"Несовместимая версия протокола: {version}")
            
            # Извлекаем payload
            payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + length]
            
            # Проверяем размер
            if len(payload) != length:
                logger.error(f"Неполный пакет: ожидалось {length}, получено {len(payload)}")
                return None
            
            # Разжимаем если нужно
            if compressed:
                payload = zlib.decompress(payload)
            
            # Десериализуем
            return deserialize_message(payload)
            
        except zlib.error as e:
            logger.error(f"Ошибка декомпрессии: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка распаковки сообщения: {e}")
            return None
    
    @classmethod
    def get_packet_length(cls, header: bytes) -> Optional[int]:
        """
        Получить длину пакета из заголовка
        
        Args:
            header: Первые 11 байт (заголовок)
            
        Returns:
            Полная длина пакета (заголовок + payload) или None при ошибке
        """
        try:
            if len(header) < cls.HEADER_SIZE:
                return None
            
            magic, version, length, compressed = struct.unpack(cls.HEADER_FORMAT, header)
            
            if magic != cls.MAGIC:
                return None
            
            return cls.HEADER_SIZE + length
            
        except Exception:
            return None
    
    @classmethod
    def pack_frame(cls, frame_data: bytes, frame_id: int = 0) -> bytes:
        """
        Упаковать кадр видео/аудио
        
        Args:
            frame_data: Данные кадра
            frame_id: ID кадра
            
        Returns:
            Упакованные данные
        """
        try:
            # Заголовок кадра: FRAME_ID (4 байта) + DATA_LENGTH (4 байта)
            frame_header = struct.pack('!II', frame_id, len(frame_data))
            return frame_header + frame_data
        except Exception as e:
            logger.error(f"Ошибка упаковки кадра: {e}")
            return b''
    
    @classmethod
    def unpack_frame(cls, data: bytes) -> Optional[tuple]:
        """
        Распаковать кадр видео/аудио
        
        Args:
            data: Бинарные данные
            
        Returns:
            (frame_id, frame_data) или None при ошибке
        """
        try:
            if len(data) < 8:
                return None
            
            frame_id, length = struct.unpack('!II', data[:8])
            frame_data = data[8:8+length]
            
            if len(frame_data) != length:
                logger.error("Неполный кадр")
                return None
            
            return (frame_id, frame_data)
            
        except Exception as e:
            logger.error(f"Ошибка распаковки кадра: {e}")
            return None


class TCPPacketAssembler:
    """
    Сборщик TCP пакетов для надежной передачи
    
    TCP не гарантирует, что recv() вернет ровно один пакет.
    Этот класс собирает фрагменты в полные пакеты.
    
    Использование:
        assembler = TCPPacketAssembler()
        
        while True:
            data = socket.recv(65536)
            for packet in assembler.feed(data):
                message = Protocol.unpack(packet)
                # обработка...
    """
    
    def __init__(self, max_packet_size: int = Protocol.MAX_PACKET_SIZE):
        self.buffer = b''
        self.max_packet_size = max_packet_size
        self._stats = {
            'packets_assembled': 0,
            'bytes_processed': 0,
            'sync_recoveries': 0
        }
    
    def feed(self, data: bytes) -> List[bytes]:
        """
        Добавить полученные данные и вернуть готовые пакеты
        
        Args:
            data: Данные полученные из socket.recv()
            
        Returns:
            Список готовых пакетов (каждый можно передать в Protocol.unpack)
        """
        if not data:
            return []
        
        self.buffer += data
        self._stats['bytes_processed'] += len(data)
        
        packets = []
        
        while len(self.buffer) >= Protocol.HEADER_SIZE:
            # Проверяем magic number в начале буфера
            if self.buffer[:4] != Protocol.MAGIC:
                # Потеряна синхронизация - ищем magic
                sync_pos = self._find_magic()
                if sync_pos == -1:
                    # Magic не найден, очищаем буфер (кроме последних 3 байт)
                    if len(self.buffer) > 3:
                        self.buffer = self.buffer[-3:]
                    break
                else:
                    # Пропускаем мусор до magic
                    logger.warning(f"Синхронизация потеряна, пропускаем {sync_pos} байт")
                    self.buffer = self.buffer[sync_pos:]
                    self._stats['sync_recoveries'] += 1
                    continue
            
            # Получаем длину пакета из заголовка
            packet_length = Protocol.get_packet_length(self.buffer[:Protocol.HEADER_SIZE])
            
            if packet_length is None:
                # Невалидный заголовок, пропускаем 1 байт
                self.buffer = self.buffer[1:]
                continue
            
            # Проверяем на слишком большой пакет (возможная атака или ошибка)
            if packet_length > self.max_packet_size:
                logger.error(f"Слишком большой пакет: {packet_length} байт, пропускаем")
                self.buffer = self.buffer[1:]
                continue
            
            # Проверяем, есть ли полный пакет в буфере
            if len(self.buffer) < packet_length:
                # Ждем больше данных
                break
            
            # Извлекаем полный пакет
            packet = self.buffer[:packet_length]
            self.buffer = self.buffer[packet_length:]
            packets.append(packet)
            self._stats['packets_assembled'] += 1
        
        return packets
    
    def _find_magic(self) -> int:
        """
        Найти позицию magic number в буфере
        
        Returns:
            Позиция magic или -1 если не найден
        """
        return self.buffer.find(Protocol.MAGIC)
    
    def clear(self):
        """Очистить буфер"""
        self.buffer = b''
    
    def get_buffer_size(self) -> int:
        """Получить текущий размер буфера"""
        return len(self.buffer)
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return self._stats.copy()


class TCPSocketWrapper:
    """
    Обертка над TCP сокетом с автоматической сборкой пакетов
    
    Использование:
        wrapper = TCPSocketWrapper(socket)
        
        # Отправка
        wrapper.send_packet(Protocol.pack(msg_type, data))
        
        # Получение
        for message in wrapper.receive_messages():
            print(message)
    """
    
    def __init__(self, sock: 'socket.socket', buffer_size: int = 65536):
        self.socket = sock
        self.buffer_size = buffer_size
        self.assembler = TCPPacketAssembler()
        self._closed = False
    
    def send_packet(self, packet: bytes) -> bool:
        """
        Отправить пакет (гарантированно весь)
        
        Args:
            packet: Упакованный пакет (результат Protocol.pack)
            
        Returns:
            True если успешно
        """
        try:
            total_sent = 0
            while total_sent < len(packet):
                sent = self.socket.send(packet[total_sent:])
                if sent == 0:
                    return False
                total_sent += sent
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки пакета: {e}")
            return False
    
    def receive_packets(self, timeout: float = None) -> List[bytes]:
        """
        Получить готовые пакеты
        
        Args:
            timeout: Таймаут в секундах (None = без таймаута)
            
        Returns:
            Список готовых пакетов
        """
        try:
            if timeout is not None:
                self.socket.settimeout(timeout)
            
            data = self.socket.recv(self.buffer_size)
            
            if not data:
                self._closed = True
                return []
            
            return self.assembler.feed(data)
            
        except TimeoutError:
            return []
        except Exception as e:
            logger.error(f"Ошибка получения данных: {e}")
            self._closed = True
            return []
    
    def receive_messages(self, timeout: float = None) -> List[Dict]:
        """
        Получить готовые сообщения (уже распакованные)
        
        Args:
            timeout: Таймаут в секундах
            
        Returns:
            Список распакованных сообщений
        """
        packets = self.receive_packets(timeout)
        messages = []
        
        for packet in packets:
            message = Protocol.unpack(packet)
            if message:
                messages.append(message)
        
        return messages
    
    def is_closed(self) -> bool:
        """Проверить, закрыто ли соединение"""
        return self._closed
    
    def close(self):
        """Закрыть соединение"""
        self._closed = True
        try:
            self.socket.close()
        except:
            pass


class MessageBuilder:
    """Класс для построения стандартных сообщений"""
    
    @staticmethod
    def ping() -> bytes:
        """Создать PING сообщение"""
        from src.common.constants import MessageType
        return Protocol.pack(MessageType.PING, {}, compress=False)
    
    @staticmethod
    def pong() -> bytes:
        """Создать PONG сообщение"""
        from src.common.constants import MessageType
        return Protocol.pack(MessageType.PONG, {}, compress=False)
    
    @staticmethod
    def teacher_broadcast(teacher_name: str, channel: int, port: int) -> bytes:
        """Создать сообщение о присутствии преподавателя"""
        from src.common.constants import MessageType
        data = {
            "teacher_name": teacher_name,
            "channel": channel,
            "port": port
        }
        return Protocol.pack(MessageType.TEACHER_BROADCAST, data, compress=False)
    
    @staticmethod
    def student_connect(student_name: str, machine_id: str) -> bytes:
        """Создать запрос на подключение студента"""
        from src.common.constants import MessageType
        data = {
            "student_name": student_name,
            "machine_id": machine_id
        }
        return Protocol.pack(MessageType.STUDENT_CONNECT, data, compress=False)
    
    @staticmethod
    def connection_accepted(student_id: str) -> bytes:
        """Создать сообщение о принятии подключения"""
        from src.common.constants import MessageType
        data = {"student_id": student_id}
        return Protocol.pack(MessageType.CONNECTION_ACCEPTED, data, compress=False)
    
    @staticmethod
    def connection_rejected(reason: str) -> bytes:
        """Создать сообщение об отклонении подключения"""
        from src.common.constants import MessageType
        data = {"reason": reason}
        return Protocol.pack(MessageType.CONNECTION_REJECTED, data, compress=False)
    
    @staticmethod
    def chat_message(sender_id: str, sender_name: str, content: str, 
                    recipient_id: Optional[str] = None, group_id: Optional[str] = None) -> bytes:
        """Создать сообщение чата"""
        from src.common.constants import MessageType
        data = {
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "recipient_id": recipient_id,
            "group_id": group_id
        }
        return Protocol.pack(MessageType.CHAT_MESSAGE, data)
    
    @staticmethod
    def lock_screen(message: str = "") -> bytes:
        """Создать команду блокировки экрана"""
        from src.common.constants import MessageType
        data = {"message": message}
        return Protocol.pack(MessageType.LOCK_SCREEN, data, compress=False)
    
    @staticmethod
    def unlock_screen() -> bytes:
        """Создать команду разблокировки экрана"""
        from src.common.constants import MessageType
        return Protocol.pack(MessageType.UNLOCK_SCREEN, {}, compress=False)
    
    @staticmethod
    def screen_frame(frame_data: bytes, frame_id: int, quality: str = "medium") -> bytes:
        """Создать пакет с кадром экрана"""
        from src.common.constants import MessageType
        import base64
        data = {
            "frame_id": frame_id,
            "frame": base64.b64encode(frame_data).decode('utf-8'),
            "quality": quality
        }
        # Кадры экрана сжимаем (они большие)
        return Protocol.pack(MessageType.SCREEN_FRAME, data, compress=True)
