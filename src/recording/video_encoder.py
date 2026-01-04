"""
Кодирование записи в MP4
Версия 1.0

Использует FFmpeg для конвертации:
screen/*.jpg + audio.wav -> output.mp4
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VideoEncoder:
    """
    Энкодер для экспорта записи в MP4.
    
    Требования:
    - FFmpeg должен быть установлен и доступен в PATH
    
    Использование:
        encoder = VideoEncoder()
        encoder.encode_to_mp4("recordings/Lesson_2026-01-03/", "lesson.mp4")
    """
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        logger.info(f"VideoEncoder создан (FFmpeg: {'доступен' if self.ffmpeg_available else 'не найден'})")
    
    def _check_ffmpeg(self) -> bool:
        """Проверить наличие FFmpeg"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def encode_to_mp4(
        self,
        recording_path: str,
        output_file: str,
        fps: int = 24,
        quality: str = "medium"
    ) -> bool:
        """
        Конвертировать запись в MP4.
        
        Args:
            recording_path: Путь к директории записи
            output_file: Путь к выходному MP4 файлу
            fps: FPS видео
            quality: Качество (low, medium, high)
        
        Returns:
            True если успешно
        """
        if not self.ffmpeg_available:
            logger.error("FFmpeg не найден. Установите FFmpeg для экспорта в MP4")
            return False
        
        recording_dir = Path(recording_path)
        screen_dir = recording_dir / "screen"
        audio_file = recording_dir / "audio.wav"
        
        if not screen_dir.exists():
            logger.error(f"Директория screen не найдена: {screen_dir}")
            return False
        
        # Проверяем наличие кадров
        frames = list(screen_dir.glob("*.jpg"))
        if not frames:
            logger.error("Нет кадров для конвертации")
            return False
        
        logger.info(f"Найдено {len(frames)} кадров")
        
        # Параметры качества
        quality_presets = {
            "low": {"crf": 28, "preset": "fast"},
            "medium": {"crf": 23, "preset": "medium"},
            "high": {"crf": 18, "preset": "slow"}
        }
        preset = quality_presets.get(quality, quality_presets["medium"])
        
        try:
            # Команда FFmpeg
            cmd = [
                'ffmpeg',
                '-y',  # Перезаписать если существует
                '-framerate', str(fps),
                '-i', str(screen_dir / '%05d.jpg'),  # Входные кадры
            ]
            
            # Добавляем аудио если есть
            if audio_file.exists():
                cmd.extend(['-i', str(audio_file)])
            
            # Параметры кодирования
            cmd.extend([
                '-c:v', 'libx264',
                '-crf', str(preset['crf']),
                '-preset', preset['preset'],
                '-pix_fmt', 'yuv420p',
            ])
            
            # Аудио кодек
            if audio_file.exists():
                cmd.extend([
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-shortest'  # Обрезать по самому короткому потоку
                ])
            
            cmd.append(output_file)
            
            logger.info(f"Запуск FFmpeg...")
            logger.debug(f"Команда: {' '.join(cmd)}")
            
            # Запускаем FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут макс
            )
            
            if result.returncode == 0:
                output_path = Path(output_file)
                if output_path.exists():
                    size_mb = output_path.stat().st_size / 1024 / 1024
                    logger.info(f"Видео создано: {output_file} ({size_mb:.2f} MB)")
                    return True
                else:
                    logger.error("Видео файл не создан")
                    return False
            else:
                logger.error(f"FFmpeg ошибка: {result.stderr}")
                return False
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg превысил таймаут (5 минут)")
            return False
        except Exception as e:
            logger.error(f"Ошибка кодирования: {e}")
            return False
    
    def create_thumbnail(self, recording_path: str, output_file: str) -> bool:
        """Создать превью (первый кадр)"""
        try:
            recording_dir = Path(recording_path)
            screen_dir = recording_dir / "screen"
            
            # Берём первый кадр
            first_frame = screen_dir / "00000.jpg"
            
            if not first_frame.exists():
                # Пробуем найти любой кадр
                frames = sorted(screen_dir.glob("*.jpg"))
                if not frames:
                    return False
                first_frame = frames[0]
            
            # Копируем или уменьшаем
            frame = cv2.imread(str(first_frame))
            if frame is None:
                return False
            
            # Уменьшаем для превью
            max_size = (320, 180)
            h, w = frame.shape[:2]
            scale = min(max_size[0] / w, max_size[1] / h)
            
            if scale < 1:
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
            
            # Сохраняем
            cv2.imwrite(output_file, frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            
            logger.info(f"Превью создано: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания превью: {e}")
            return False
    
    def _load_chat(self) -> List[Dict]:
        """Загрузить чат"""
        chat_file = self.recording_path / "chat.json"
        if chat_file.exists():
            with open(chat_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _load_events(self) -> List[Dict]:
        """Загрузить события"""
        events_file = self.recording_path / "events.json"
        if events_file.exists():
            with open(events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _load_whiteboard(self) -> List[Dict]:
        """Загрузить команды доски"""
        wb_file = self.recording_path / "whiteboard.json"
        if wb_file.exists():
            with open(wb_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_encoder.py <recording_path> [output.mp4]")
        sys.exit(1)
    
    recording_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output.mp4"
    
    encoder = VideoEncoder()
    
    if not encoder.ffmpeg_available:
        print("ERROR: FFmpeg не установлен!")
        print("Скачайте с: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    print(f"Конвертация: {recording_path} -> {output_file}")
    
    success = encoder.encode_to_mp4(recording_path, output_file)
    
    if success:
        print(f"SUCCESS: Видео создано: {output_file}")
    else:
        print("ERROR: Не удалось создать видео")



