"""
Передача файлов
Версия 1.0

Поддержка:
- Отправка файлов от преподавателя студентам
- Сбор файлов от студентов
- Проверка целостности (MD5)
- Прогресс передачи
"""

import os
import logging
import hashlib
import base64
import threading
import time
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


logger = logging.getLogger(__name__)


# Размер чанка для передачи (64 KB)
CHUNK_SIZE = 64 * 1024


class TransferStatus(Enum):
    """Статус передачи"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileTransferInfo:
    """Информация о передаче файла"""
    transfer_id: str
    filename: str
    file_size: int
    file_hash: str  # MD5
    total_chunks: int
    received_chunks: int = 0
    status: str = "pending"
    local_path: Optional[str] = None
    error: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    
    @property
    def progress(self) -> float:
        """Прогресс в процентах"""
        if self.total_chunks == 0:
            return 0
        return (self.received_chunks / self.total_chunks) * 100
    
    @property
    def is_complete(self) -> bool:
        return self.received_chunks >= self.total_chunks


class FileSender:
    """
    Отправитель файлов (для преподавателя)
    
    Использование:
        sender = FileSender()
        sender.on_chunk = lambda transfer_id, chunk_num, data: send_to_students(...)
        sender.send_file("path/to/file.pdf")
    """
    
    def __init__(self):
        self._transfer_id = 0
        self._active_transfers: Dict[str, FileTransferInfo] = {}
        
        # Колбэки
        self.on_transfer_start: Optional[Callable[[FileTransferInfo], None]] = None
        self.on_chunk: Optional[Callable[[str, int, str, int], None]] = None  # transfer_id, chunk_num, data_base64, total
        self.on_transfer_complete: Optional[Callable[[FileTransferInfo], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        logger.info("FileSender создан")
    
    def send_file(self, file_path: str, target_students: Optional[List[str]] = None) -> Optional[str]:
        """
        Начать отправку файла
        
        Args:
            file_path: Путь к файлу
            target_students: Список ID студентов (None = всем)
        
        Returns:
            transfer_id или None при ошибке
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"Файл не найден: {file_path}")
            if self.on_error:
                self.on_error("", f"Файл не найден: {file_path}")
            return None
            
        try:
            # Получаем информацию о файле
            file_size = path.stat().st_size
            filename = path.name
            file_hash = self._calculate_hash(file_path)
            total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            # Создаём transfer_id
            self._transfer_id += 1
            transfer_id = f"transfer_{self._transfer_id}_{int(time.time())}"
            
            # Создаём информацию о передаче
            info = FileTransferInfo(
                transfer_id=transfer_id,
                filename=filename,
                file_size=file_size,
                file_hash=file_hash,
                total_chunks=total_chunks,
                status=TransferStatus.IN_PROGRESS.value
            )
            
            self._active_transfers[transfer_id] = info
            
            # Уведомляем о начале
            if self.on_transfer_start:
                self.on_transfer_start(info)
            
            # Отправляем в отдельном потоке
            thread = threading.Thread(
                target=self._send_chunks,
                args=(transfer_id, file_path, total_chunks),
                daemon=True
            )
            thread.start()
            
            logger.info(f"Начата отправка: {filename} ({file_size} байт, {total_chunks} чанков)")
            return transfer_id
            
        except Exception as e:
            logger.error(f"Ошибка отправки файла: {e}")
            if self.on_error:
                self.on_error("", str(e))
            return None
    
    def _send_chunks(self, transfer_id: str, file_path: str, total_chunks: int):
        """Отправка чанков в отдельном потоке"""
        try:
            with open(file_path, 'rb') as f:
                chunk_num = 0
                
                while True:
                    chunk_data = f.read(CHUNK_SIZE)
                    if not chunk_data:
                        break
                    
                    # Кодируем в base64
                    encoded = base64.b64encode(chunk_data).decode('ascii')
                    
                    # Отправляем через колбэк
                    if self.on_chunk:
                        self.on_chunk(transfer_id, chunk_num, encoded, total_chunks)
                    
                    chunk_num += 1
                    
                    # Небольшая задержка чтобы не перегрузить сеть
                    time.sleep(0.01)
            
            # Обновляем статус
            if transfer_id in self._active_transfers:
                info = self._active_transfers[transfer_id]
                info.status = TransferStatus.COMPLETED.value
                info.received_chunks = total_chunks
                
                if self.on_transfer_complete:
                    self.on_transfer_complete(info)
                
                logger.info(f"Отправка завершена: {transfer_id}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки чанков: {e}")
            if transfer_id in self._active_transfers:
                self._active_transfers[transfer_id].status = TransferStatus.FAILED.value
                self._active_transfers[transfer_id].error = str(e)
            if self.on_error:
                self.on_error(transfer_id, str(e))
    
    def _calculate_hash(self, file_path: str) -> str:
        """Вычислить MD5 хэш файла"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_transfer_info(self, transfer_id: str) -> Optional[FileTransferInfo]:
        """Получить информацию о передаче"""
        return self._active_transfers.get(transfer_id)


class FileReceiver:
    """
    Получатель файлов (для студента)
    
    Использование:
        receiver = FileReceiver(save_dir="downloads")
        receiver.start_transfer(transfer_info)
        receiver.add_chunk(transfer_id, chunk_num, data)
    """
    
    def __init__(self, save_dir: str = "downloads"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self._active_transfers: Dict[str, FileTransferInfo] = {}
        self._buffers: Dict[str, Dict[int, bytes]] = {}
        
        # Колбэки
        self.on_progress: Optional[Callable[[FileTransferInfo], None]] = None
        self.on_complete: Optional[Callable[[FileTransferInfo], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        logger.info(f"FileReceiver создан: {save_dir}")
    
    def start_transfer(self, transfer_id: str, filename: str, file_size: int, 
                       file_hash: str, total_chunks: int):
        """Начать приём файла"""
        info = FileTransferInfo(
            transfer_id=transfer_id,
            filename=filename,
            file_size=file_size,
            file_hash=file_hash,
            total_chunks=total_chunks,
            status=TransferStatus.IN_PROGRESS.value
        )
        
        self._active_transfers[transfer_id] = info
        self._buffers[transfer_id] = {}
        
        logger.info(f"Начат приём: {filename} ({file_size} байт)")
    
    def add_chunk(self, transfer_id: str, chunk_num: int, data_base64: str) -> bool:
        """Добавить чанк данных"""
        if transfer_id not in self._active_transfers:
            logger.warning(f"Неизвестный transfer_id: {transfer_id}")
            return False
        
        try:
            # Декодируем
            chunk_data = base64.b64decode(data_base64)
            
            # Сохраняем в буфер
            self._buffers[transfer_id][chunk_num] = chunk_data
            
            # Обновляем прогресс
            info = self._active_transfers[transfer_id]
            info.received_chunks = len(self._buffers[transfer_id])
            
            if self.on_progress:
                self.on_progress(info)
            
            # Проверяем завершение
            if info.is_complete:
                self._finalize_transfer(transfer_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления чанка: {e}")
            return False
    
    def _finalize_transfer(self, transfer_id: str):
        """Завершить передачу - собрать файл"""
        try:
            info = self._active_transfers[transfer_id]
            buffer = self._buffers[transfer_id]
            
            # Собираем файл
            file_path = self.save_dir / info.filename
            
            # Если файл существует, добавляем номер
            counter = 1
            original_stem = file_path.stem
            while file_path.exists():
                file_path = self.save_dir / f"{original_stem}_{counter}{file_path.suffix}"
                counter += 1
            
            with open(file_path, 'wb') as f:
                for i in range(info.total_chunks):
                    if i in buffer:
                        f.write(buffer[i])
            
            # Проверяем хэш
            received_hash = self._calculate_hash(str(file_path))
            
            if received_hash == info.file_hash:
                info.status = TransferStatus.COMPLETED.value
                info.local_path = str(file_path)
                
                logger.info(f"Файл получен: {file_path}")
                
                if self.on_complete:
                    self.on_complete(info)
            else:
                info.status = TransferStatus.FAILED.value
                info.error = "Ошибка проверки целостности"
                
                # Удаляем повреждённый файл
                file_path.unlink()
                
                logger.error(f"Ошибка целостности: {transfer_id}")
                
                if self.on_error:
                    self.on_error(transfer_id, "Ошибка проверки целостности")
            
            # Очищаем буфер
            del self._buffers[transfer_id]
            
        except Exception as e:
            logger.error(f"Ошибка финализации: {e}")
            if transfer_id in self._active_transfers:
                self._active_transfers[transfer_id].status = TransferStatus.FAILED.value
                self._active_transfers[transfer_id].error = str(e)
            if self.on_error:
                self.on_error(transfer_id, str(e))
    
    def _calculate_hash(self, file_path: str) -> str:
        """Вычислить MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_transfer_info(self, transfer_id: str) -> Optional[FileTransferInfo]:
        """Получить информацию о передаче"""
        return self._active_transfers.get(transfer_id)
    
    def get_all_transfers(self) -> List[FileTransferInfo]:
        """Получить все передачи"""
        return list(self._active_transfers.values())


class FileCollector:
    """
    Сборщик файлов от студентов (для преподавателя)
    
    Позволяет запросить файлы у студентов и собрать их.
    """
    
    def __init__(self, save_dir: str = "collected"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self._collection_id = 0
        self._collections: Dict[str, Dict] = {}
        
        # Колбэки
        self.on_file_received: Optional[Callable[[str, str, str], None]] = None  # student_id, filename, path
        
        logger.info(f"FileCollector создан: {save_dir}")
    
    def start_collection(self, description: str = "Сдать работу") -> str:
        """Начать сбор файлов"""
        self._collection_id += 1
        collection_id = f"collect_{self._collection_id}_{int(time.time())}"
        
        self._collections[collection_id] = {
            'description': description,
            'files': {},
            'start_time': time.time()
        }
        
        logger.info(f"Начат сбор файлов: {collection_id}")
        return collection_id
    
    def add_file(self, collection_id: str, student_id: str, student_name: str,
                 filename: str, data_base64: str) -> Optional[str]:
        """Добавить файл от студента"""
        if collection_id not in self._collections:
            logger.warning(f"Неизвестный collection_id: {collection_id}")
            return None
        
        try:
            # Создаём папку для студента
            student_dir = self.save_dir / collection_id / student_name.replace(" ", "_")
            student_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем файл
            file_path = student_dir / filename
            file_data = base64.b64decode(data_base64)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Записываем в коллекцию
            self._collections[collection_id]['files'][student_id] = {
                'student_name': student_name,
                'filename': filename,
                'path': str(file_path),
                'time': time.time()
            }
            
            logger.info(f"Получен файл от {student_name}: {filename}")
            
            if self.on_file_received:
                self.on_file_received(student_id, filename, str(file_path))
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            return None
    
    def get_collection_status(self, collection_id: str) -> Dict:
        """Получить статус сбора"""
        if collection_id not in self._collections:
            return {}

        collection = self._collections[collection_id]
        return {
            'description': collection['description'],
            'files_count': len(collection['files']),
            'files': collection['files']
        }


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест передачи файлов...")
    
    # Создаём тестовый файл
    test_file = "test_transfer.txt"
    with open(test_file, 'w') as f:
        f.write("Hello, this is a test file!\n" * 100)
    
    # Отправитель
    sender = FileSender()
    receiver = FileReceiver(save_dir="test_downloads")
    
    received_chunks = []
    
    def on_start(info):
        print(f"Начата отправка: {info.filename}")
        receiver.start_transfer(
            info.transfer_id,
            info.filename,
            info.file_size,
            info.file_hash,
            info.total_chunks
        )
    
    def on_chunk(transfer_id, chunk_num, data, total):
        print(f"Чанк {chunk_num + 1}/{total}")
        receiver.add_chunk(transfer_id, chunk_num, data)
    
    def on_complete(info):
        print(f"Отправка завершена: {info.filename}")
    
    def on_receive_complete(info):
        print(f"Получен: {info.local_path}")
    
    sender.on_transfer_start = on_start
    sender.on_chunk = on_chunk
    sender.on_transfer_complete = on_complete
    receiver.on_complete = on_receive_complete
    
    # Отправляем
    sender.send_file(test_file)
    
    # Ждём завершения
    time.sleep(2)
    
    # Очистка
    os.remove(test_file)
    
    print("Тест завершён!")
