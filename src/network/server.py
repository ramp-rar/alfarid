"""
Серверный модуль (преподаватель)
Версия 2.0 - с надежной TCP буферизацией
"""

import socket
import threading
import logging
import time
from typing import Dict, Callable, Optional, List
from src.common.constants import (
    DEFAULT_PORT, MULTICAST_GROUP, MULTICAST_PORT,
    BROADCAST_INTERVAL, HEARTBEAT_INTERVAL, CONNECTION_TIMEOUT,
    MessageType, BUFFER_SIZE
)
from src.common.utils import get_local_ip
from src.network.protocol import Protocol, MessageBuilder, TCPPacketAssembler
from src.common.models import Student


logger = logging.getLogger(__name__)


class ClientHandler:
    """Обработчик соединения с одним клиентом (студентом)"""
    
    def __init__(self, client_socket: socket.socket, address: tuple):
        self.socket = client_socket
        self.address = address
        self.student_id: Optional[str] = None
        self.student: Optional[Student] = None
        self.assembler = TCPPacketAssembler()
        self.connected = True
        
        # Lock для потокобезопасной отправки
        self._send_lock = threading.Lock()
    
    def send_packet(self, packet: bytes) -> bool:
        """Отправить пакет (потокобезопасно, гарантированно весь)"""
        if not self.connected:
            return False
        
        try:
            with self._send_lock:
                total_sent = 0
                while total_sent < len(packet):
                    sent = self.socket.send(packet[total_sent:])
                    if sent == 0:
                        self.connected = False
                        return False
                    total_sent += sent
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки пакету {self.address}: {e}")
            self.connected = False
            return False
    
    def receive_packets(self) -> List[bytes]:
        """Получить готовые пакеты"""
        try:
            data = self.socket.recv(BUFFER_SIZE)
            if not data:
                self.connected = False
                return []
            return self.assembler.feed(data)
        except socket.timeout:
            return []
        except Exception as e:
            logger.error(f"Ошибка получения от {self.address}: {e}")
            self.connected = False
            return []
    
    def close(self):
        """Закрыть соединение"""
        self.connected = False
        try:
            self.socket.close()
        except:
            pass


class TeacherServer:
    """Сервер преподавателя с надежной TCP буферизацией"""
    
    def __init__(self, teacher_name: str, channel: int = 1, port: int = DEFAULT_PORT):
        self.teacher_name = teacher_name
        self.channel = channel
        self.port = port
        self.ip_address = get_local_ip()
        
        # Сокеты
        self.tcp_socket: Optional[socket.socket] = None
        self.multicast_socket: Optional[socket.socket] = None
        
        # Клиенты (студенты)
        self.students: Dict[str, Student] = {}
        self.client_handlers: Dict[str, ClientHandler] = {}
        
        # Потоки
        self.running = False
        self.threads: List[threading.Thread] = []
        
        # Locks
        self._students_lock = threading.Lock()
        
        # Колбэки
        self.on_student_connected: Optional[Callable[[Student], None]] = None
        self.on_student_disconnected: Optional[Callable[[str], None]] = None
        self.on_message_received: Optional[Callable[[str, Dict], None]] = None
        
        # Статистика
        self._stats = {
            'total_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'start_time': None
        }
        
        logger.info(f"Сервер создан: {teacher_name} на {self.ip_address}:{self.port}, канал {channel}")
    
    def start(self) -> bool:
        """Запустить сервер"""
        try:
            # TCP сокет для подключений студентов
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tcp_socket.bind(('0.0.0.0', self.port))
            self.tcp_socket.listen(50)
            logger.info(f"TCP сервер запущен на порту {self.port}")
            
            # Multicast сокет для трансляций + broadcast fallback
            self.multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            # Разрешаем broadcast, чтобы работало в сетях без multicast
            self.multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info(f"Multicast сокет создан для {MULTICAST_GROUP}:{MULTICAST_PORT} (broadcast включен)")
            
            self.running = True
            self._stats['start_time'] = time.time()
            
            # Запускаем потоки
            self._start_threads()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Остановить сервер"""
        logger.info("Остановка сервера...")
        self.running = False
        
        # Закрываем соединения со студентами
        with self._students_lock:
            for student_id, handler in list(self.client_handlers.items()):
                handler.close()
            self.client_handlers.clear()
            self.students.clear()
        
        # Закрываем серверные сокеты
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.multicast_socket:
            try:
                self.multicast_socket.close()
            except:
                pass
        
        # Ждем завершения потоков
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        self.threads.clear()
        logger.info("Сервер остановлен")
    
    def _start_threads(self):
        """Запустить рабочие потоки"""
        # Поток приема подключений
        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
        accept_thread.start()
        self.threads.append(accept_thread)
        
        # Поток широковещания
        broadcast_thread = threading.Thread(target=self._broadcast_presence, daemon=True)
        broadcast_thread.start()
        self.threads.append(broadcast_thread)
        
        # Поток проверки heartbeat
        heartbeat_thread = threading.Thread(target=self._check_heartbeats, daemon=True)
        heartbeat_thread.start()
        self.threads.append(heartbeat_thread)
    
    def _accept_connections(self):
        """Поток приема подключений студентов"""
        logger.info("Ожидание подключений студентов...")
        
        while self.running:
            try:
                self.tcp_socket.settimeout(1.0)
                client_socket, address = self.tcp_socket.accept()
                
                # Настраиваем сокет
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                logger.info(f"Новое подключение от {address}")
                self._stats['total_connections'] += 1
                
                # Обрабатываем подключение в отдельном потоке
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                self.threads.append(client_thread)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка приема подключения: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """
        Обработка клиента (студента)
        ИСПРАВЛЕНО: Теперь использует TCPPacketAssembler
        """
        handler = ClientHandler(client_socket, address)
        student_id = None
        
        try:
            # Таймаут для первого сообщения (регистрации)
            client_socket.settimeout(10.0)
            
            while self.running and handler.connected:
                # Получаем пакеты
                packets = handler.receive_packets()
                
                for packet in packets:
                    # Распаковываем сообщение
                    message = Protocol.unpack(packet)
                    if not message:
                        continue
                    
                    msg_type = message.get("type")
                    msg_data = message.get("data", {})
                    
                    self._stats['messages_received'] += 1
                    
                    # Обрабатываем тип сообщения
                    if msg_type == MessageType.STUDENT_CONNECT:
                        # Новый студент подключается
                        student_id = self._register_student(msg_data, address, handler)
                        if student_id:
                            # После регистрации убираем таймаут
                            client_socket.settimeout(None)
                        else:
                            # Регистрация не удалась
                            handler.close()
                            return
                        
                    elif msg_type == MessageType.PING:
                        # Heartbeat от студента
                        if student_id:
                            with self._students_lock:
                                if student_id in self.students:
                                    self.students[student_id].last_seen = time.time()
                            # Отправляем PONG
                            handler.send_packet(MessageBuilder.pong())
                    
                    else:
                        # Другие сообщения
                        if self.on_message_received and student_id:
                            try:
                                self.on_message_received(student_id, message)
                            except Exception as e:
                                logger.error(f"Ошибка в обработчике сообщения: {e}")
                
                # Небольшая пауза если нет пакетов
                if not packets:
                    time.sleep(0.01)
                        
        except Exception as e:
            if self.running:
                logger.error(f"Ошибка обработки клиента {address}: {e}")
        finally:
            # Отключение студента
            if student_id:
                self._unregister_student(student_id)
            handler.close()
    
    def _register_student(self, data: Dict, address: tuple, handler: ClientHandler) -> Optional[str]:
        """Зарегистрировать студента"""
        try:
            student_name = data.get("student_name", "Unknown")
            machine_id = data.get("machine_id", "")
            
            # Создаем ID студента
            student_id = f"{machine_id}_{address[0]}"
            
            # Проверяем, не подключен ли уже этот студент
            with self._students_lock:
                if student_id in self.students:
                    # Отключаем старое соединение
                    logger.warning(f"Студент {student_id} уже подключен, заменяем соединение")
                    old_handler = self.client_handlers.get(student_id)
                    if old_handler:
                        old_handler.close()
            
            # Создаем объект студента
            student = Student(
                id=student_id,
                name=student_name,
                ip_address=address[0],
                status="online",
                last_seen=time.time()
            )
            
            # Сохраняем
            with self._students_lock:
                self.students[student_id] = student
                self.client_handlers[student_id] = handler
            
            handler.student_id = student_id
            handler.student = student
            
            # Отправляем подтверждение
            response = MessageBuilder.connection_accepted(student_id)
            if not handler.send_packet(response):
                logger.error(f"Не удалось отправить подтверждение студенту {student_name}")
                return None
            
            self._stats['messages_sent'] += 1
            
            # Колбэк
            if self.on_student_connected:
                try:
                    self.on_student_connected(student)
                except Exception as e:
                    logger.error(f"Ошибка в колбэке on_student_connected: {e}")
            
            logger.info(f"Студент зарегистрирован: {student_name} ({student_id})")
            return student_id
            
        except Exception as e:
            logger.error(f"Ошибка регистрации студента: {e}")
            return None
    
    def _unregister_student(self, student_id: str):
        """Отключить студента"""
        with self._students_lock:
            if student_id in self.students:
                student = self.students[student_id]
                logger.info(f"Студент отключен: {student.name} ({student_id})")
                
                del self.students[student_id]
                if student_id in self.client_handlers:
                    del self.client_handlers[student_id]
                
                # Колбэк
                if self.on_student_disconnected:
                    try:
                        self.on_student_disconnected(student_id)
                    except Exception as e:
                        logger.error(f"Ошибка в колбэке on_student_disconnected: {e}")
    
    def _broadcast_presence(self):
        """Поток широковещания присутствия преподавателя"""
        logger.info("Запущен поток широковещания")
        
        while self.running:
            try:
                # Создаем сообщение
                message = MessageBuilder.teacher_broadcast(
                    self.teacher_name,
                    self.channel,
                    self.port
                )
                
                # Отправляем в multicast группу
                try:
                    self.multicast_socket.sendto(message, (MULTICAST_GROUP, MULTICAST_PORT))
                except Exception as me:
                    logger.debug(f"Multicast недоступен: {me}")

                # Фолбэк: broadcast для сетей без multicast
                try:
                    self.multicast_socket.sendto(message, ("255.255.255.255", MULTICAST_PORT))
                except Exception as be:
                    logger.debug(f"Broadcast недоступен: {be}")
                
                time.sleep(BROADCAST_INTERVAL)
                
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка широковещания: {e}")
                time.sleep(BROADCAST_INTERVAL)
    
    def _check_heartbeats(self):
        """Поток проверки heartbeat от студентов"""
        while self.running:
            try:
                current_time = time.time()
                students_to_remove = []
                
                # Проверяем всех студентов
                with self._students_lock:
                    for student_id, student in self.students.items():
                        if student.last_seen:
                            time_diff = current_time - student.last_seen
                            
                            if time_diff > CONNECTION_TIMEOUT:
                                logger.warning(f"Студент {student.name} не отвечает {time_diff:.1f}с, отключаем")
                                students_to_remove.append(student_id)
                
                # Отключаем неактивных (вне lock чтобы избежать deadlock)
                for student_id in students_to_remove:
                    handler = self.client_handlers.get(student_id)
                    if handler:
                        handler.close()
                    self._unregister_student(student_id)
                
                time.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка проверки heartbeat: {e}")
                time.sleep(HEARTBEAT_INTERVAL)
    
    def send_to_student(self, student_id: str, msg_type: str, data: Dict) -> bool:
        """Отправить сообщение студенту"""
        try:
            with self._students_lock:
                if student_id not in self.client_handlers:
                    logger.warning(f"Студент {student_id} не найден")
                    return False
                
                handler = self.client_handlers[student_id]
            
            message = Protocol.pack(msg_type, data)
            success = handler.send_packet(message)
            
            if success:
                self._stats['messages_sent'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка отправки студенту {student_id}: {e}")
            return False
    
    def broadcast_to_all(self, msg_type: str, data: Dict, exclude: Optional[List[str]] = None):
        """Отправить сообщение всем студентам"""
        exclude = exclude or []
        message = Protocol.pack(msg_type, data)
        
        with self._students_lock:
            handlers_to_send = [
                (sid, handler) 
                for sid, handler in self.client_handlers.items() 
                if sid not in exclude
            ]
        
        for student_id, handler in handlers_to_send:
            if handler.send_packet(message):
                self._stats['messages_sent'] += 1
    
    def get_students(self) -> List[Student]:
        """Получить список студентов"""
        with self._students_lock:
            return list(self.students.values())
    
    def get_student_count(self) -> int:
        """Получить количество подключенных студентов"""
        with self._students_lock:
            return len(self.students)
    
    def get_stats(self) -> dict:
        """Получить статистику сервера"""
        stats = self._stats.copy()
        if stats['start_time']:
            stats['uptime_seconds'] = time.time() - stats['start_time']
        stats['active_students'] = self.get_student_count()
        return stats


# Для обратной совместимости
def get_student_socket(server: TeacherServer, student_id: str) -> Optional[socket.socket]:
    """Получить сокет студента (для обратной совместимости)"""
    with server._students_lock:
        handler = server.client_handlers.get(student_id)
        return handler.socket if handler else None
