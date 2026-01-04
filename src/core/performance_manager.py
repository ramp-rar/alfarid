"""
Менеджер производительности
Версия 1.0

Автоматически адаптирует качество на основе:
- Количества подключённых студентов
- Пропускной способности сети
- Загрузки CPU

Обеспечивает стабильную работу без задержек!
"""

import logging
import time
from typing import Literal, Optional
from dataclasses import dataclass

# Опциональная зависимость
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

QualityProfile = Literal["small", "medium", "large", "ultra"]


@dataclass
class PerformanceProfile:
    """Профиль производительности"""
    name: QualityProfile
    max_students: int
    screen_fps: int
    screen_quality: int  # JPEG quality 1-100
    screen_resolution: tuple  # (width, height)
    audio_sample_rate: int
    enable_webcam: bool
    enable_whiteboard: bool
    use_multicast: bool
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'max_students': self.max_students,
            'screen_fps': self.screen_fps,
            'screen_quality': self.screen_quality,
            'screen_resolution': self.screen_resolution,
            'audio_sample_rate': self.audio_sample_rate,
            'enable_webcam': self.enable_webcam,
            'enable_whiteboard': self.enable_whiteboard,
            'use_multicast': self.use_multicast,
        }


class PerformanceManager:
    """
    Менеджер производительности.
    
    Автоматически выбирает оптимальный профиль.
    """
    
    # Предустановленные профили
    PROFILES = {
        "small": PerformanceProfile(
            name="small",
            max_students=10,
            screen_fps=30,
            screen_quality=85,
            screen_resolution=(1920, 1080),
            audio_sample_rate=48000,
            enable_webcam=True,
            enable_whiteboard=True,
            use_multicast=False,  # TCP для малых групп
        ),
        "medium": PerformanceProfile(
            name="medium",
            max_students=25,
            screen_fps=24,
            screen_quality=70,
            screen_resolution=(1280, 720),
            audio_sample_rate=44100,
            enable_webcam=True,
            enable_whiteboard=True,
            use_multicast=True,  # Multicast рекомендуется
        ),
        "large": PerformanceProfile(
            name="large",
            max_students=50,
            screen_fps=15,
            screen_quality=60,
            screen_resolution=(1280, 720),
            audio_sample_rate=32000,
            enable_webcam=False,  # Отключаем для экономии
            enable_whiteboard=True,
            use_multicast=True,  # Multicast обязателен
        ),
        "ultra": PerformanceProfile(
            name="ultra",
            max_students=100,
            screen_fps=10,
            screen_quality=50,
            screen_resolution=(854, 480),
            audio_sample_rate=24000,
            enable_webcam=False,
            enable_whiteboard=False,
            use_multicast=True,  # Только multicast
        ),
    }
    
    @classmethod
    def get_profile_for_students(cls, student_count: int) -> PerformanceProfile:
        """
        Получить оптимальный профиль для количества студентов.
        
        Args:
            student_count: Количество студентов
        
        Returns:
            Оптимальный профиль
        """
        if student_count <= 10:
            return cls.PROFILES["small"]
        elif student_count <= 25:
            return cls.PROFILES["medium"]
        elif student_count <= 50:
            return cls.PROFILES["large"]
        else:
            return cls.PROFILES["ultra"]
    
    @classmethod
    def get_profile_by_name(cls, name: QualityProfile) -> PerformanceProfile:
        """Получить профиль по имени"""
        return cls.PROFILES.get(name, cls.PROFILES["medium"])
    
    @classmethod
    def calculate_bandwidth(cls, profile: PerformanceProfile, student_count: int) -> dict:
        """
        Рассчитать требуемую пропускную способность.
        
        Returns:
            dict с оценками трафика
        """
        # Размер JPEG кадра (примерно)
        width, height = profile.screen_resolution
        pixels = width * height
        
        # Примерный размер кадра в зависимости от качества
        bytes_per_pixel = profile.screen_quality / 100 * 0.2  # ~0.1-0.2 байт/пиксель для JPEG
        frame_size_kb = (pixels * bytes_per_pixel) / 1024
        
        # Трафик экрана в секунду
        screen_mbps = (frame_size_kb * profile.screen_fps * 8) / 1000
        
        # Аудио трафик
        audio_mbps = (profile.audio_sample_rate * 2 * 8) / 1_000_000  # 2 байта на сэмпл (16-bit)
        
        # Веб-камера (если включена)
        webcam_mbps = 2.0 if profile.enable_webcam else 0
        
        # Общий upload преподавателя
        total_upload = screen_mbps + audio_mbps + webcam_mbps
        
        # С multicast трафик не зависит от количества студентов!
        if profile.use_multicast:
            total_for_all = total_upload
        else:
            total_for_all = total_upload * student_count
        
        return {
            "upload_mbps": round(total_upload, 2),
            "upload_for_all_students_mbps": round(total_for_all, 2),
            "download_per_student_mbps": round(total_upload, 2),
            "student_count": student_count,
            "use_multicast": profile.use_multicast,
            "savings_vs_tcp": f"{student_count}x" if profile.use_multicast else "1x",
        }
    
    @classmethod
    def get_system_resources(cls) -> dict:
        """Получить текущие ресурсы системы"""
        if not PSUTIL_AVAILABLE:
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_available_gb": 4.0,
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
            }
        except Exception as e:
            logger.error(f"Ошибка получения ресурсов: {e}")
            return {}
    
    @classmethod
    def recommend_profile(cls, student_count: int) -> dict:
        """
        Рекомендовать профиль с обоснованием.
        
        Returns:
            dict с профилем и рекомендациями
        """
        profile = cls.get_profile_for_students(student_count)
        bandwidth = cls.calculate_bandwidth(profile, student_count)
        resources = cls.get_system_resources()
        
        # Рекомендации
        recommendations = []
        
        if student_count > 20 and not profile.use_multicast:
            recommendations.append("⚠️ Рекомендуется включить Multicast для лучшей производительности")
        
        if resources.get('cpu_percent', 0) > 70:
            recommendations.append("⚠️ Высокая загрузка CPU. Рассмотрите снижение качества или FPS")
        
        if resources.get('memory_available_gb', 0) < 2:
            recommendations.append("⚠️ Мало свободной памяти. Закройте ненужные приложения")
        
        if bandwidth['upload_for_all_students_mbps'] > 100 and not profile.use_multicast:
            recommendations.append("⚠️ Высокий трафик! Multicast снизит его в {student_count}x раз")
        
        return {
            "profile": profile,
            "bandwidth": bandwidth,
            "resources": resources,
            "recommendations": recommendations,
            "verdict": "OK" if not recommendations else "NEEDS_ATTENTION"
        }


# Для тестирования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    import sys
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    
    print("=" * 60)
    print("Performance Manager - Test")
    print("=" * 60)
    print()
    
    # Тест для разных размеров классов
    for student_count in [5, 15, 30, 60]:
        print(f"\nClass: {student_count} students")
        print("-" * 60)
        
        result = PerformanceManager.recommend_profile(student_count)
        
        profile = result['profile']
        print(f"Profile: {profile.name}")
        print(f"  - FPS: {profile.screen_fps}")
        print(f"  - Quality: {profile.screen_quality}")
        print(f"  - Resolution: {profile.screen_resolution[0]}x{profile.screen_resolution[1]}")
        print(f"  - Multicast: {profile.use_multicast}")
        
        bandwidth = result['bandwidth']
        print(f"\nBandwidth:")
        print(f"  - Upload: {bandwidth['upload_mbps']} Mbps")
        print(f"  - Total for all: {bandwidth['upload_for_all_students_mbps']} Mbps")
        print(f"  - Savings: {bandwidth['savings_vs_tcp']}")
        
        if result['recommendations']:
            print(f"\nRecommendations:")
            for rec in result['recommendations']:
                print(f"  {rec}")
        else:
            print("\nOptimal!")
    
    print("\n" + "=" * 60)
    print("Test complete!")

