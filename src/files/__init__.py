"""
Модуль передачи файлов
"""

from .file_transfer import (
    FileSender,
    FileReceiver,
    FileCollector,
    FileTransferInfo,
    TransferStatus,
    CHUNK_SIZE
)

__all__ = [
    'FileSender',
    'FileReceiver',
    'FileCollector',
    'FileTransferInfo',
    'TransferStatus',
    'CHUNK_SIZE'
]
