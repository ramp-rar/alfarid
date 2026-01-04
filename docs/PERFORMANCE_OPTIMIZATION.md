# План оптимизации производительности

## Проблема: 30+ студентов одновременно

### Текущие узкие места:

1. **Трансляция экрана**
   - 30 студентов × 24 FPS × 1920×1080 = огромный трафик
   - **Решение**: 
     - Адаптивное качество по пропускной способности
     - Multicast вместо unicast
     - WebRTC для P2P

2. **Сетевой протокол**
   - TCP для каждого студента = 30 соединений
   - **Решение**:
     - UDP multicast для трансляции
     - Группировка пакетов
     - Compression (zlib уже есть)

3. **Память**
   - 30 буферов для TCP packet assembly
   - **Решение**:
     - Пулы буферов
     - Ограничение размера буфера
     - Очистка старых данных

### Конкретные изменения:

```python
# src/common/constants.py

# Адаптивные настройки по количеству студентов
PERFORMANCE_PROFILES = {
    "small": {  # 1-10 студентов
        "max_students": 10,
        "screen_quality": "high",
        "fps": 30,
        "audio_quality": 48000,
        "enable_webcam": True,
    },
    "medium": {  # 11-20 студентов
        "max_students": 20,
        "screen_quality": "medium",
        "fps": 24,
        "audio_quality": 44100,
        "enable_webcam": True,
    },
    "large": {  # 21-50 студентов
        "max_students": 50,
        "screen_quality": "low",
        "fps": 15,
        "audio_quality": 32000,
        "enable_webcam": False,  # Только у выбранных
    }
}
```

### Multicast трансляция:

```python
# src/network/multicast_streamer.py

class MulticastStreamer:
    """
    Отправка трансляции через UDP multicast
    Вместо 30 TCP соединений = 1 multicast группа
    """
    
    def __init__(self, multicast_group="239.0.0.1", port=5004):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        self.group = (multicast_group, port)
    
    def send_frame(self, frame_data):
        # Отправка 1 раз, получают все студенты
        self.sock.sendto(frame_data, self.group)
```

## Оценка производительности:

| Параметр | Текущий (TCP) | Оптимизированный (Multicast) |
|----------|---------------|------------------------------|
| Трафик (30 студентов) | 30× | 1× |
| CPU преподавателя | ~80% | ~20% |
| Задержка | 100-300ms | 50-100ms |
| Пропускная способность | ~300 Mbps | ~10 Mbps |



