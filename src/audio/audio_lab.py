"""
Аудиолаборатория (Цифровой магнитофон)
"""

import logging
import os
import time
import threading
from typing import Optional, Callable, List, Dict
from pathlib import Path


logger = logging.getLogger(__name__)


class AudioPlayer:
    """Аудиоплеер для воспроизведения"""
    
    def __init__(self, audio_file: Optional[str] = None):
        self.audio_file = audio_file
        self.playing = False
        self.paused = False
        self.position = 0.0  # Позиция в секундах
        self.duration = 0.0  # Длительность в секундах
        self.speed = 1.0  # Скорость воспроизведения
        
        # Поток воспроизведения
        self.play_thread: Optional[threading.Thread] = None
        
        # Колбэки
        self.on_position_changed: Optional[Callable[[float], None]] = None
        self.on_finished: Optional[Callable[[], None]] = None
        
        if audio_file:
            self._load_file(audio_file)
        
        logger.info(f"AudioPlayer создан: {audio_file}")
    
    def _load_file(self, audio_file: str) -> bool:
        """Загрузить аудиофайл"""
        try:
            if not os.path.exists(audio_file):
                logger.error(f"Аудиофайл не найден: {audio_file}")
                return False
            
            # Получаем длительность
            try:
                import soundfile as sf
                info = sf.info(audio_file)
                self.duration = info.duration
                logger.info(f"Аудио загружено: {self.duration:.1f} сек")
            except Exception as e:
                logger.warning(f"Не удалось получить длительность: {e}")
                self.duration = 0.0
            
            self.audio_file = audio_file
            self.position = 0.0
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки аудиофайла: {e}")
            return False
    
    def play(self):
        """Начать воспроизведение"""
        if not self.audio_file:
            logger.warning("Аудиофайл не загружен")
            return False
        
        if self.playing:
            if self.paused:
                self.paused = False
                logger.info("Воспроизведение возобновлено")
            return True
        
        self.playing = True
        self.paused = False
        
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        
        logger.info("Воспроизведение начато")
        return True
    
    def pause(self):
        """Пауза"""
        if self.playing and not self.paused:
            self.paused = True
            logger.info("Пауза")
    
    def stop(self):
        """Остановить"""
        if not self.playing:
            return
        
        self.playing = False
        self.paused = False
        
        if self.play_thread:
            self.play_thread.join(timeout=2)
        
        self.position = 0.0
        logger.info("Воспроизведение остановлено")
    
    def seek(self, position: float):
        """Перемотать на позицию (в секундах)"""
        self.position = max(0, min(position, self.duration))
        logger.info(f"Перемотка на {self.position:.1f} сек")
    
    def set_speed(self, speed: float):
        """Установить скорость воспроизведения (0.5 - 2.0)"""
        self.speed = max(0.5, min(speed, 2.0))
        logger.info(f"Скорость установлена: {self.speed}x")
    
    def _play_loop(self):
        """Основной цикл воспроизведения"""
        try:
            import sounddevice as sd
            import soundfile as sf
            
            # Загружаем аудио
            data, samplerate = sf.read(self.audio_file)
            
            # Определяем начальную позицию
            start_frame = int(self.position * samplerate)
            
            # Воспроизводим
            def callback(outdata, frames, time_info, status):
                nonlocal start_frame
                
                if status:
                    logger.warning(f"Audio callback status: {status}")
                
                if self.paused:
                    outdata.fill(0)
                    return
                
                end_frame = start_frame + frames
                
                if end_frame > len(data):
                    # Конец файла
                    outdata[:len(data) - start_frame] = data[start_frame:]
                    outdata[len(data) - start_frame:].fill(0)
                    self.playing = False
                    raise sd.CallbackStop
                else:
                    outdata[:] = data[start_frame:end_frame]
                    start_frame = end_frame
                    
                    # Обновляем позицию
                    self.position = start_frame / samplerate
                    
                    if self.on_position_changed:
                        self.on_position_changed(self.position)
            
            with sd.OutputStream(samplerate=samplerate, channels=data.shape[1] if len(data.shape) > 1 else 1, callback=callback):
                while self.playing:
                    time.sleep(0.1)
            
            # Завершено
            if self.on_finished:
                self.on_finished()
                
        except Exception as e:
            logger.error(f"Ошибка воспроизведения: {e}")
            self.playing = False


class AudioRecorder:
    """Записывающее устройство"""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        
        # Буфер записи
        self.audio_data = []
        
        # Поток записи
        self.record_thread: Optional[threading.Thread] = None
        
        logger.info(f"AudioRecorder создан: {sample_rate}Hz, {channels} канал(ов)")
    
    def start(self):
        """Начать запись"""
        if self.recording:
            logger.warning("Запись уже идет")
            return False
        
        self.recording = True
        self.audio_data = []
        
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.record_thread.start()
        
        logger.info("Запись начата")
        return True
    
    def stop(self) -> Optional[bytes]:
        """Остановить запись и вернуть данные"""
        if not self.recording:
            return None
        
        self.recording = False
        
        if self.record_thread:
            self.record_thread.join(timeout=2)
        
        try:
            import numpy as np
            
            if not self.audio_data:
                return None
            
            # Объединяем все куски
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            logger.info(f"Запись остановлена, размер: {audio_array.shape}")
            return audio_array.tobytes()
            
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}")
            return None
    
    def _record_loop(self):
        """Основной цикл записи"""
        try:
            import sounddevice as sd
            
            def callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Record callback status: {status}")
                
                if self.recording:
                    self.audio_data.append(indata.copy())
            
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=callback):
                while self.recording:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Ошибка записи: {e}")
            self.recording = False
    
    def save_to_file(self, filename: str, audio_data: Optional[bytes] = None) -> bool:
        """Сохранить запись в файл"""
        try:
            import soundfile as sf
            import numpy as np
            
            if audio_data is None:
                if not self.audio_data:
                    logger.warning("Нет данных для сохранения")
                    return False
                
                # Используем текущий буфер
                audio_array = np.concatenate(self.audio_data, axis=0)
            else:
                # Конвертируем bytes в numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
                if self.channels > 1:
                    audio_array = audio_array.reshape(-1, self.channels)
            
            sf.write(filename, audio_array, self.sample_rate)
            
            logger.info(f"Запись сохранена: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            return False


class AudioLab:
    """Аудиолаборатория (магнитофон)"""
    
    def __init__(self):
        self.player = AudioPlayer()
        self.recorder = AudioRecorder()
        
        # Режимы работы
        self.mode = "idle"  # idle, playing, recording, comparing
        
        # Записи студента
        self.student_recordings: List[bytes] = []
        
        logger.info("AudioLab создана")
    
    def load_course(self, audio_file: str) -> bool:
        """Загрузить аудиокурс"""
        self.player = AudioPlayer(audio_file)
        return self.player.audio_file is not None
    
    def play_original(self):
        """Воспроизвести оригинал"""
        self.mode = "playing"
        self.player.play()
    
    def pause(self):
        """Пауза"""
        self.player.pause()
    
    def stop(self):
        """Остановить"""
        self.player.stop()
        self.recorder.stop()
        self.mode = "idle"
    
    def start_recording(self):
        """Начать запись студента"""
        self.mode = "recording"
        self.recorder.start()
        logger.info("Запись студента начата")
    
    def stop_recording(self):
        """Остановить запись студента"""
        audio_data = self.recorder.stop()
        
        if audio_data:
            self.student_recordings.append(audio_data)
            logger.info(f"Запись сохранена (всего {len(self.student_recordings)})")
        
        self.mode = "idle"
    
    def play_with_recording(self):
        """Воспроизвести оригинал и записывать одновременно"""
        self.mode = "recording"
        self.recorder.start()
        self.player.play()
        logger.info("Режим: слушаем и записываем")
    
    def compare_recordings(self):
        """Режим сравнения оригинала и записи студента"""
        self.mode = "comparing"
        # TODO: Реализовать визуализацию и сравнение
        logger.info("Режим сравнения")
    
    def save_student_recording(self, filename: str, recording_index: int = -1) -> bool:
        """Сохранить запись студента"""
        if not self.student_recordings:
            logger.warning("Нет записей для сохранения")
            return False
        
        recording_data = self.student_recordings[recording_index]
        return self.recorder.save_to_file(filename, recording_data)
    
    def get_recordings_count(self) -> int:
        """Получить количество записей"""
        return len(self.student_recordings)
    
    def clear_recordings(self):
        """Очистить все записи"""
        self.student_recordings.clear()
        logger.info("Записи очищены")
    
    def set_playback_speed(self, speed: float):
        """Установить скорость воспроизведения"""
        self.player.set_speed(speed)
    
    def get_info(self) -> Dict:
        """Получить информацию о состоянии"""
        return {
            "mode": self.mode,
            "duration": self.player.duration,
            "position": self.player.position,
            "playing": self.player.playing,
            "recording": self.recorder.recording,
            "recordings_count": len(self.student_recordings),
            "speed": self.player.speed
        }

