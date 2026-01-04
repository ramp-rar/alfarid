"""
Голосовая трансляция в реальном времени
Версия 1.0
"""

import logging
import threading
import time
import zlib
import base64
import queue
from typing import Optional, Callable, List
from dataclasses import dataclass

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class VoiceSettings:
    """Настройки голосовой связи"""
    sample_rate: int = 16000  # 16kHz достаточно для голоса
    channels: int = 1  # Моно
    chunk_duration: float = 0.05  # 50ms на чанк
    compression_level: int = 6  # zlib compression
    
    @property
    def chunk_size(self) -> int:
        return int(self.sample_rate * self.chunk_duration)


class VoiceCapture:
    """Захват голоса с микрофона для трансляции"""
    
    def __init__(self, settings: Optional[VoiceSettings] = None):
        if not AUDIO_AVAILABLE:
            raise RuntimeError("sounddevice не установлен. Установите: pip install sounddevice")
        
        self.settings = settings or VoiceSettings()
        self.capturing = False
        self.stream: Optional[sd.InputStream] = None
        
        # Очередь для аудио чанков
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        
        # Поток отправки
        self.send_thread: Optional[threading.Thread] = None
        
        # Колбэк для отправки данных
        self.on_audio_chunk: Optional[Callable[[bytes, int], None]] = None
        
        # Статистика
        self._chunk_id = 0
        self._chunks_sent = 0
        self._bytes_sent = 0
        
        # Определение активности голоса (VAD простой)
        self.vad_enabled = True
        self.vad_threshold = 0.01  # Порог громкости
        
        logger.info(f"VoiceCapture создан: {self.settings.sample_rate}Hz, {self.settings.channels}ch")
    
    def start(self) -> bool:
        """Начать захват голоса"""
        if self.capturing:
            logger.warning("Захват уже идет")
            return False
        
        try:
            # Создаем поток захвата
            self.stream = sd.InputStream(
                samplerate=self.settings.sample_rate,
                channels=self.settings.channels,
                blocksize=self.settings.chunk_size,
                dtype=np.float32,
                callback=self._audio_callback
            )
            
            self.capturing = True
            self._chunk_id = 0
            self._chunks_sent = 0
            self._bytes_sent = 0
            
            # Запускаем поток обработки
            self.send_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.send_thread.start()
            
            # Запускаем захват
            self.stream.start()
            
            logger.info("Захват голоса запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска захвата голоса: {e}")
            self.capturing = False
            return False
    
    def stop(self):
        """Остановить захват"""
        if not self.capturing:
            return
        
        self.capturing = False
        
        # Останавливаем поток захвата
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        # Ждем завершения потока обработки
        if self.send_thread:
            self.send_thread.join(timeout=2)
        
        # Очищаем очередь
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
        
        logger.info(f"Захват голоса остановлен. Отправлено: {self._chunks_sent} чанков, {self._bytes_sent} байт")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Колбэк захвата аудио"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        if not self.capturing:
            return
        
        # Простой VAD - проверяем громкость
        if self.vad_enabled:
            volume = np.abs(indata).mean()
            if volume < self.vad_threshold:
                return  # Тишина, не отправляем
        
        # Добавляем в очередь
        try:
            self.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            # Очередь переполнена, пропускаем чанк
            pass
    
    def _process_audio(self):
        """Поток обработки и отправки аудио"""
        while self.capturing:
            try:
                # Получаем чанк из очереди
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Сжимаем данные
                compressed = self._compress_audio(audio_data)
                
                if compressed and self.on_audio_chunk:
                    self._chunk_id += 1
                    self._chunks_sent += 1
                    self._bytes_sent += len(compressed)
                    
                    self.on_audio_chunk(compressed, self._chunk_id)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка обработки аудио: {e}")
    
    def _compress_audio(self, audio_data: np.ndarray) -> Optional[bytes]:
        """Сжать аудио данные"""
        try:
            # Конвертируем float32 -> int16 для лучшего сжатия
            audio_int16 = (audio_data * 32767).astype(np.int16)
            raw_bytes = audio_int16.tobytes()
            
            # Сжимаем zlib
            compressed = zlib.compress(raw_bytes, level=self.settings.compression_level)
            
            return compressed
            
        except Exception as e:
            logger.error(f"Ошибка сжатия аудио: {e}")
            return None
    
    def set_vad_threshold(self, threshold: float):
        """Установить порог VAD (0.0 - 1.0)"""
        self.vad_threshold = max(0.0, min(1.0, threshold))
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            'capturing': self.capturing,
            'chunks_sent': self._chunks_sent,
            'bytes_sent': self._bytes_sent,
            'queue_size': self.audio_queue.qsize()
        }


class VoicePlayback:
    """Воспроизведение голоса из сети"""
    
    def __init__(self, settings: Optional[VoiceSettings] = None):
        if not AUDIO_AVAILABLE:
            raise RuntimeError("sounddevice не установлен")
        
        self.settings = settings or VoiceSettings()
        self.playing = False
        self.stream: Optional[sd.OutputStream] = None
        
        # Буфер для воспроизведения
        self.audio_buffer: queue.Queue = queue.Queue(maxsize=200)
        
        # Джиттер-буфер (накапливаем перед воспроизведением)
        self.jitter_buffer_size = 3  # Количество чанков перед началом
        self._buffering = True
        self._buffer_count = 0
        
        # Статистика
        self._chunks_received = 0
        self._chunks_played = 0
        self._underruns = 0
        
        logger.info(f"VoicePlayback создан: {self.settings.sample_rate}Hz")
    
    def start(self) -> bool:
        """Начать воспроизведение"""
        if self.playing:
            return False
        
        try:
            self.stream = sd.OutputStream(
                samplerate=self.settings.sample_rate,
                channels=self.settings.channels,
                blocksize=self.settings.chunk_size,
                dtype=np.float32,
                callback=self._playback_callback
            )
            
            self.playing = True
            self._buffering = True
            self._buffer_count = 0
            self._chunks_received = 0
            self._chunks_played = 0
            self._underruns = 0
            
            self.stream.start()
            
            logger.info("Воспроизведение голоса запущено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска воспроизведения: {e}")
            return False
    
    def stop(self):
        """Остановить воспроизведение"""
        if not self.playing:
            return
        
        self.playing = False
        
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        # Очищаем буфер
        while not self.audio_buffer.empty():
            try:
                self.audio_buffer.get_nowait()
            except:
                break
        
        logger.info(f"Воспроизведение остановлено. Получено: {self._chunks_received}, воспроизведено: {self._chunks_played}, underruns: {self._underruns}")
    
    def add_audio_chunk(self, compressed_data: bytes, chunk_id: int):
        """Добавить аудио чанк для воспроизведения"""
        if not self.playing:
            return
        
        try:
            # Декомпрессия
            audio_data = self._decompress_audio(compressed_data)
            
            if audio_data is not None:
                self._chunks_received += 1
                
                try:
                    self.audio_buffer.put_nowait(audio_data)
                    self._buffer_count += 1
                    
                    # Проверяем буферизацию
                    if self._buffering and self._buffer_count >= self.jitter_buffer_size:
                        self._buffering = False
                        logger.debug("Джиттер-буфер заполнен, начинаем воспроизведение")
                        
                except queue.Full:
                    # Буфер переполнен, пропускаем
                    pass
                    
        except Exception as e:
            logger.error(f"Ошибка добавления аудио чанка: {e}")
    
    def _decompress_audio(self, compressed_data: bytes) -> Optional[np.ndarray]:
        """Распаковать аудио данные"""
        try:
            # Распаковываем zlib
            raw_bytes = zlib.decompress(compressed_data)
            
            # Конвертируем int16 -> float32
            audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32767.0
            
            return audio_float32.reshape(-1, self.settings.channels)
            
        except Exception as e:
            logger.error(f"Ошибка декомпрессии аудио: {e}")
            return None
    
    def _playback_callback(self, outdata, frames, time_info, status):
        """Колбэк воспроизведения"""
        if status:
            logger.warning(f"Playback callback status: {status}")
        
        # Если буферизуемся - тишина
        if self._buffering:
            outdata.fill(0)
            return
        
        try:
            audio_data = self.audio_buffer.get_nowait()
            
            # Проверяем размер
            if len(audio_data) >= frames:
                outdata[:] = audio_data[:frames].reshape(outdata.shape)
            else:
                outdata[:len(audio_data)] = audio_data.reshape(-1, self.settings.channels)
                outdata[len(audio_data):].fill(0)
            
            self._chunks_played += 1
            
        except queue.Empty:
            # Нет данных - тишина
            outdata.fill(0)
            self._underruns += 1
            
            # Если много underruns - снова буферизуемся
            if self._underruns > 10:
                self._buffering = True
                self._buffer_count = 0
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        return {
            'playing': self.playing,
            'buffering': self._buffering,
            'chunks_received': self._chunks_received,
            'chunks_played': self._chunks_played,
            'buffer_size': self.audio_buffer.qsize(),
            'underruns': self._underruns
        }


class VoiceBroadcaster:
    """
    Менеджер голосовой трансляции (для преподавателя)
    
    Использование:
        broadcaster = VoiceBroadcaster()
        broadcaster.on_voice_data = lambda data, id: server.broadcast_to_all("VOICE", {"data": data, "id": id})
        broadcaster.start()  # Начать трансляцию
        ...
        broadcaster.stop()
    """
    
    def __init__(self, settings: Optional[VoiceSettings] = None):
        self.settings = settings or VoiceSettings()
        self.capture: Optional[VoiceCapture] = None
        self.active = False
        
        # Колбэк для отправки голоса
        self.on_voice_data: Optional[Callable[[str, int], None]] = None
        
        logger.info("VoiceBroadcaster создан")
    
    def start(self) -> bool:
        """Начать голосовую трансляцию"""
        if self.active:
            return False
        
        try:
            self.capture = VoiceCapture(self.settings)
            self.capture.on_audio_chunk = self._on_audio_chunk
            
            if self.capture.start():
                self.active = True
                logger.info("Голосовая трансляция запущена")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка запуска голосовой трансляции: {e}")
            return False
    
    def stop(self):
        """Остановить голосовую трансляцию"""
        if not self.active:
            return
        
        self.active = False
        
        if self.capture:
            self.capture.stop()
            self.capture = None
        
        logger.info("Голосовая трансляция остановлена")
    
    def _on_audio_chunk(self, compressed_data: bytes, chunk_id: int):
        """Обработка аудио чанка"""
        if self.on_voice_data:
            # Кодируем в base64 для передачи через JSON
            encoded = base64.b64encode(compressed_data).decode('ascii')
            self.on_voice_data(encoded, chunk_id)
    
    def set_vad_threshold(self, threshold: float):
        """Установить порог активации голоса"""
        if self.capture:
            self.capture.set_vad_threshold(threshold)
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        if self.capture:
            return self.capture.get_stats()
        return {'active': False}


class VoiceReceiver:
    """
    Менеджер приема голоса (для студента)
    
    Использование:
        receiver = VoiceReceiver()
        receiver.start()
        
        # При получении сообщения VOICE:
        receiver.add_voice_data(data, chunk_id)
    """
    
    def __init__(self, settings: Optional[VoiceSettings] = None):
        self.settings = settings or VoiceSettings()
        self.playback: Optional[VoicePlayback] = None
        self.active = False
        
        logger.info("VoiceReceiver создан")
    
    def start(self) -> bool:
        """Начать прием голоса"""
        if self.active:
            return False
        
        try:
            self.playback = VoicePlayback(self.settings)
            
            if self.playback.start():
                self.active = True
                logger.info("Прием голоса запущен")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка запуска приема голоса: {e}")
            return False
    
    def stop(self):
        """Остановить прием"""
        if not self.active:
            return
        
        self.active = False
        
        if self.playback:
            self.playback.stop()
            self.playback = None
        
        logger.info("Прием голоса остановлен")
    
    def add_voice_data(self, encoded_data: str, chunk_id: int):
        """Добавить полученные голосовые данные"""
        if not self.active or not self.playback:
            return
        
        try:
            # Декодируем из base64
            compressed = base64.b64decode(encoded_data)
            self.playback.add_audio_chunk(compressed, chunk_id)
            
        except Exception as e:
            logger.error(f"Ошибка добавления голосовых данных: {e}")
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        if self.playback:
            return self.playback.get_stats()
        return {'active': False}


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест голосовой связи...")
    print("Нажмите Enter для записи, потом Enter для остановки")
    
    # Тест захвата
    capture = VoiceCapture()
    chunks = []
    
    def on_chunk(data, id):
        chunks.append((data, id))
        print(f"Чанк {id}: {len(data)} байт")
    
    capture.on_audio_chunk = on_chunk
    
    input("Нажмите Enter для начала записи...")
    capture.start()
    
    input("Нажмите Enter для остановки...")
    capture.stop()
    
    print(f"\nЗаписано {len(chunks)} чанков")
    
    # Тест воспроизведения
    if chunks:
        input("Нажмите Enter для воспроизведения...")
        
        playback = VoicePlayback()
        playback.start()
        
        for data, id in chunks:
            playback.add_audio_chunk(data, id)
            time.sleep(0.05)
        
        time.sleep(1)
        playback.stop()
    
    print("Тест завершен!")

