"""
Клиентский модуль (студент)
Версия 2.0 - с надежной TCP буферизацией
"""

import socket
import threading
import logging
import time
from typing import Dict, Callable, Optional, List
from src.common.constants import (
    DEFAULT_PORT, MULTICAST_GROUP, MULTICAST_PORT,
    HEARTBEAT_INTERVAL, MessageType, BUFFER_SIZE
)
from src.common.utils import get_machine_id
from src.network.protocol import Protocol, MessageBuilder, TCPPacketAssembler
from src.common.models import Teacher


logger = logging.getLogger(__name__)


class StudentClient:
    """Клиент студента с надежной TCP буферизацией"""
    
    def __init__(self, student_name: str):
        self.student_name = student_name
        self.student_id: Optional[str] = None
        self.machine_id = get_machine_id()
        
        # Сокеты
        self.tcp_socket: Optional[socket.socket] = None
        self.multicast_socket: Optional[socket.socket] = None
        
        # Буферизация TCP
        self.packet_assembler: Optional[TCPPacketAssembler] = None
        
        # Подключение
        self.connected = False
        self.teacher: Optional[Teacher] = None
        self.available_teachers: Dict[str, Teacher] = {}
        
        # Потоки
        self.running = False
        self.threads: List[threading.Thread] = []
        
        # Lock для потокобезопасной отправки
        self._send_lock = threading.Lock()
        
        # Колбэки
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_message_received: Optional[Callable[[Dict], None]] = None
        self.on_teacher_found: Optional[Callable[[Teacher], None]] = None
        
        # Статистика
        self._stats = {
            'messages_received': 0,
            'messages_sent': 0,
            'bytes_received': 0,
            'bytes_sent': 0,
            'connection_time': None
        }
        
        logger.info(f"Клиент создан: {student_name} ({self.machine_id})")
    
    def start_discovery(self) -> bool:
        """Запустить поиск преподавателей"""
        try:
            # Multicast/broadcast сокет для прослушивания трансляций преподавателей
            self.multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Разрешаем broadcast, чтобы принимать фолбэк
            self.multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Привязываем к порту
            self.multicast_socket.bind(('', MULTICAST_PORT))
            
            # Присоединяемся к multicast группе
            try:
                mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton('0.0.0.0')
                self.multicast_socket.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    mreq
                )
                logger.info(f"Multicast сокет запущен на порту {MULTICAST_PORT}")
            except Exception as e:
                logger.warning(f"Multicast недоступен, используем broadcast: {e}")
            
            self.running = True
            
            # Запускаем поток прослушивания
            discovery_thread = threading.Thread(target=self._listen_broadcasts, daemon=True)
            discovery_thread.start()
            self.threads.append(discovery_thread)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска поиска: {e}")
            return False
    
    def connect_to_teacher(self, teacher: Teacher) -> bool:
        """Подключиться к преподавателю"""
        try:
            # TCP сокет для подключения
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tcp_socket.connect((teacher.ip_address, teacher.port))
            logger.info(f"Подключение к {teacher.name} на {teacher.ip_address}:{teacher.port}")
            
            # Создаем сборщик пакетов
            self.packet_assembler = TCPPacketAssembler()
            
            # Отправляем запрос на подключение
            message = MessageBuilder.student_connect(self.student_name, self.machine_id)
            self._send_raw(message)
            
            # Ждем ответ
            self.tcp_socket.settimeout(5.0)
            data = self.tcp_socket.recv(BUFFER_SIZE)
            
            # Используем сборщик для получения ответа
            packets = self.packet_assembler.feed(data)
            
            if not packets:
                logger.error("Не получен ответ от сервера")
                return False
            
            response = Protocol.unpack(packets[0])
            
            if response and response.get("type") == MessageType.CONNECTION_ACCEPTED:
                self.student_id = response["data"]["student_id"]
                self.teacher = teacher
                self.connected = True
                self.tcp_socket.settimeout(None)
                self._stats['connection_time'] = time.time()
                
                logger.info(f"Подключение принято, ID: {self.student_id}")
                
                # Запускаем рабочие потоки
                self._start_client_threads()
                
                # Колбэк
                if self.on_connected:
                    self.on_connected()
                
                return True
            
            elif response and response.get("type") == MessageType.CONNECTION_REJECTED:
                reason = response["data"].get("reason", "Unknown")
                logger.warning(f"Подключение отклонено: {reason}")
                return False
            
            else:
                logger.error("Неизвестный ответ от сервера")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            if self.tcp_socket:
                self.tcp_socket.close()
                self.tcp_socket = None
            return False
    
    def disconnect(self):
        """Отключиться от преподавателя"""
        if not self.connected:
            return
            
        logger.info("Отключение от преподавателя...")
        
        self.connected = False
        
        # Закрываем сокет
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
            self.tcp_socket = None
        
        # Очищаем буфер
        if self.packet_assembler:
            self.packet_assembler.clear()
            self.packet_assembler = None
        
        # Колбэк
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception as e:
                logger.error(f"Ошибка в колбэке on_disconnected: {e}")
        
        logger.info("Отключено")
    
    def stop(self):
        """Остановить клиент"""
        logger.info("Остановка клиента...")
        
        self.running = False
        self.disconnect()
        
        # Закрываем multicast сокет
        if self.multicast_socket:
            try:
                self.multicast_socket.close()
            except:
                pass
            self.multicast_socket = None
        
        # Ждем завершения потоков
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        self.threads.clear()
        logger.info("Клиент остановлен")
    
    def _listen_broadcasts(self):
        """Поток прослушивания трансляций преподавателей"""
        logger.info("Прослушивание трансляций преподавателей...")
        
        while self.running:
            try:
                self.multicast_socket.settimeout(1.0)
                data, address = self.multicast_socket.recvfrom(BUFFER_SIZE)
                
                # Распаковываем сообщение
                message = Protocol.unpack(data)
                if not message:
                    continue
                
                if message.get("type") == MessageType.TEACHER_BROADCAST:
                    msg_data = message.get("data", {})
                    teacher_name = msg_data.get("teacher_name")
                    channel = msg_data.get("channel")
                    port = msg_data.get("port")
                    
                    # Создаем объект преподавателя
                    teacher_id = f"{address[0]}:{port}"
                    teacher = Teacher(
                        id=teacher_id,
                        name=teacher_name,
                        ip_address=address[0],
                        channel=channel,
                        port=port
                    )
                    
                    # Добавляем в список
                    if teacher_id not in self.available_teachers:
                        self.available_teachers[teacher_id] = teacher
                        logger.info(f"Найден преподаватель: {teacher_name} на {address[0]}:{port}")
                        
                        # Колбэк
                        if self.on_teacher_found:
                            self.on_teacher_found(teacher)
                    else:
                        # Обновляем существующего
                        self.available_teachers[teacher_id] = teacher
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка прослушивания трансляций: {e}")
    
    def _start_client_threads(self):
        """Запустить рабочие потоки клиента"""
        # Поток получения сообщений
        receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
        receive_thread.start()
        self.threads.append(receive_thread)
        
        # Поток отправки heartbeat
        heartbeat_thread = threading.Thread(target=self._send_heartbeat, daemon=True)
        heartbeat_thread.start()
        self.threads.append(heartbeat_thread)
    
    def _receive_messages(self):
        """
        Поток получения сообщений от преподавателя
        ИСПРАВЛЕНО: Теперь использует TCPPacketAssembler для надежной сборки пакетов
        """
        logger.info("Запущен поток получения сообщений (с буферизацией)")
        
        while self.connected:
            try:
                self.tcp_socket.settimeout(1.0)
                data = self.tcp_socket.recv(BUFFER_SIZE)
                
                if not data:
                    logger.warning("Соединение закрыто сервером")
                    self.disconnect()
                    break
                
                self._stats['bytes_received'] += len(data)
                
                # Используем сборщик пакетов
                packets = self.packet_assembler.feed(data)
                
                for packet in packets:
                    # Распаковываем сообщение
                    message = Protocol.unpack(packet)
                    if not message:
                        continue
                    
                    self._stats['messages_received'] += 1
                    msg_type = message.get("type")
                    
                    # Обрабатываем PONG
                    if msg_type == MessageType.PONG:
                        continue
                    
                    # Другие сообщения передаем в колбэк
                    if self.on_message_received:
                        try:
                            self.on_message_received(message)
                        except Exception as e:
                            logger.error(f"Ошибка в обработчике сообщения: {e}")
                    
            except socket.timeout:
                continue
            except ConnectionResetError:
                logger.warning("Соединение сброшено сервером")
                self.disconnect()
                break
            except Exception as e:
                if self.connected:
                    logger.error(f"Ошибка получения сообщения: {e}")
                    self.disconnect()
                break
        
        # Логируем статистику при завершении
        if self.packet_assembler:
            stats = self.packet_assembler.get_stats()
            logger.info(f"Статистика сборщика: собрано пакетов={stats['packets_assembled']}, "
                       f"обработано байт={stats['bytes_processed']}, "
                       f"восстановлений синхронизации={stats['sync_recoveries']}")
    
    def _send_heartbeat(self):
        """Поток отправки heartbeat"""
        while self.connected:
            try:
                if not self.send_message(MessageType.PING, {}):
                    break
                time.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                if self.connected:
                    logger.error(f"Ошибка отправки heartbeat: {e}")
                break
    
    def _send_raw(self, data: bytes) -> bool:
        """
        Отправить сырые данные (потокобезопасно)
        Гарантирует отправку всех байт
        """
        if not self.tcp_socket:
            return False
        
        try:
            with self._send_lock:
                total_sent = 0
                while total_sent < len(data):
                    sent = self.tcp_socket.send(data[total_sent:])
                    if sent == 0:
                        return False
                    total_sent += sent
                self._stats['bytes_sent'] += total_sent
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки данных: {e}")
            return False
    
    def send_message(self, msg_type: str, data: Dict) -> bool:
        """Отправить сообщение преподавателю"""
        if not self.connected or not self.tcp_socket:
            logger.warning("Не подключен к преподавателю")
            return False
        
        try:
            message = Protocol.pack(msg_type, data)
            if self._send_raw(message):
                self._stats['messages_sent'] += 1
                return True
            return False
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    def get_available_teachers(self) -> List[Teacher]:
        """Получить список доступных преподавателей"""
        return list(self.available_teachers.values())
    
    def get_stats(self) -> dict:
        """Получить статистику соединения"""
        stats = self._stats.copy()
        if stats['connection_time']:
            stats['uptime_seconds'] = time.time() - stats['connection_time']
        return stats
