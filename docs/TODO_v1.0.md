# ALFARID v1.0 — TODO Лист разработки

## 🎯 Цель: Полноценная замена Линко V8.3/V8.5

Этот документ содержит конкретные задачи для завершения v1.0

---

## 🔴 КРИТИЧЕСКИЕ ЗАДАЧИ (Приоритет 1)

### 1. Исправить передачу больших пакетов TCP

**Проблема:** Кадры трансляции больше 65KB теряются/повреждаются

**Файл:** `src/network/client.py`

**Задача:** Добавить сборщик пакетов

```python
# В классе StudentClient, метод _receive_messages:
class PacketAssembler:
    def __init__(self):
        self.buffer = b''
    
    def feed(self, data: bytes) -> list:
        self.buffer += data
        packets = []
        # ... логика сборки
        return packets

# Использование:
def _receive_messages(self):
    assembler = PacketAssembler()
    while self.connected:
        data = self.tcp_socket.recv(BUFFER_SIZE)
        for packet in assembler.feed(data):
            message = Protocol.unpack(packet)
            # обработка...
```

**Срок:** 2 дня

---

### 2. Трансляция голоса вместе с экраном

**Файлы:** 
- `src/streaming/audio_stream.py` (создать)
- `src/teacher/main_window.py` (интегрировать)

**Задача:**
```python
class AudioStreamer:
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        
    def start_capture(self, on_audio: Callable):
        import sounddevice as sd
        def callback(indata, frames, time, status):
            compressed = zlib.compress(indata.tobytes())
            on_audio(compressed)
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback
        )
        self.stream.start()
```

**Срок:** 3 дня

---

### 3. Наблюдение за студентами (скриншоты)

**Файл:** `src/control/monitoring.py` (создать)

**Задача на стороне преподавателя:**
```python
def request_screenshot(self, student_id: str):
    self.server.send_to_student(
        student_id, 
        MessageType.SCREENSHOT_REQUEST, 
        {"quality": 50}
    )

def on_screenshot_received(self, student_id: str, data: bytes):
    # Показать в окне наблюдения
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    self.thumbnail_widgets[student_id].setPixmap(pixmap)
```

**Задача на стороне студента:**
```python
def handle_screenshot_request(self, data: dict):
    from src.streaming.screen_capture import ScreenCapture
    capture = ScreenCapture()
    screenshot = capture.capture_single_frame()
    self.client.send_message(MessageType.SCREENSHOT_RESPONSE, {
        "image": base64.b64encode(screenshot).decode()
    })
```

**Срок:** 2 дня

---

### 4. Веб-камера

**Файл:** `src/streaming/webcam.py` (создать)

```python
import cv2

class WebcamCapture:
    def __init__(self, device_id=0):
        self.cap = cv2.VideoCapture(device_id)
        self.running = False
        self.on_frame = None
    
    def start(self):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.start()
    
    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret and self.on_frame:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self.on_frame(jpeg.tobytes())
            time.sleep(1/24)  # 24 fps
```

**Срок:** 2 дня

---

### 5. Интерактивная доска (базовая версия)

**Файл:** `src/whiteboard/whiteboard.py` (создать)

**Минимальный функционал:**
- [ ] Холст для рисования
- [ ] Карандаш (черный, красный, синий)
- [ ] Ластик
- [ ] Очистка
- [ ] Отправка студентам

**Срок:** 4 дня

---

### 6. Запись урока

**Файл:** `src/streaming/recorder.py` (создать)

```python
import cv2

class LessonRecorder:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.writer = None
        self.recording = False
    
    def start(self, width=1920, height=1080, fps=24):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            self.output_path, fourcc, fps, (width, height)
        )
        self.recording = True
    
    def add_frame(self, frame: np.ndarray):
        if self.recording and self.writer:
            self.writer.write(frame)
    
    def stop(self):
        self.recording = False
        if self.writer:
            self.writer.release()
```

**Срок:** 2 дня

---

### 7. Экспорт результатов в HTML

**Файл:** `src/exams/export.py` (создать)

```python
def export_exam_results_html(exam, results, output_path):
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Результаты: {exam.title}</title>
    <style>
        body {{ font-family: Arial; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #4CAF50; color: white; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
    </style>
</head>
<body>
    <h1>Результаты экзамена: {exam.title}</h1>
    <table>
        <tr><th>Студент</th><th>Баллы</th><th>%</th><th>Статус</th></tr>
"""
    for r in results:
        pct = r.score / r.max_score * 100 if r.max_score else 0
        status = "pass" if pct >= 60 else "fail"
        html += f"<tr><td>{r.student_id}</td><td>{r.score}/{r.max_score}</td><td>{pct:.1f}%</td><td class='{status}'>{'Сдал' if pct >= 60 else 'Не сдал'}</td></tr>"
    
    html += "</table></body></html>"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
```

**Срок:** 1 день

---

### 8. Плавающая панель студента

**Файл:** `src/student/floating_toolbar.py` (создать)

Панель вверху экрана с кнопками:
- Свернуть/развернуть
- Поднять руку 🖐️
- Сообщение 💬
- Отправить файл 📤
- Полученные файлы 📥
- Справка ❓

**Срок:** 2 дня

---

### 9. Блокировка клавиатуры и мыши

**Файл:** `src/control/input_block.py` (создать)

```python
import ctypes

def block_input(block: bool = True):
    """Заблокировать/разблокировать клавиатуру и мышь"""
    try:
        ctypes.windll.user32.BlockInput(block)
        return True
    except:
        return False
```

**Внимание:** Требуются права администратора!

**Срок:** 1 день

---

### 10. Иконки и ресурсы

**Файлы:**
- `resources/icons/teacher.ico`
- `resources/icons/student.ico`
- `resources/icons/tray_online.ico`
- `resources/icons/tray_offline.ico`

**Задача:** Создать или найти подходящие иконки 256x256 ICO

**Срок:** 1 день

---

## 🟡 ВАЖНЫЕ ЗАДАЧИ (Приоритет 2)

### UI Улучшения

- [ ] Настройки размера карточек студентов
- [ ] Drag-n-drop карточек на плане класса
- [ ] Сортировка по имени/статусу
- [ ] Темная тема

### Сеть

- [ ] Реальная передача файлов через TCP
- [ ] Проверка целостности (SHA256)
- [ ] Индикатор качества связи

### Экзамены

- [ ] Таймер обратного отсчета
- [ ] Статистика (графики Chart.js)
- [ ] Импорт вопросов из текстового файла

### Магнитофон

- [ ] UI для аудиолаборатории
- [ ] Визуализация аудиоволны
- [ ] Сравнение записей

---

## 🟢 ЖЕЛАТЕЛЬНЫЕ ЗАДАЧИ (Приоритет 3)

- [ ] Локализация EN/RU
- [ ] Справочная система (F1)
- [ ] Горячие клавиши
- [ ] История чата (сохранение в БД)
- [ ] Готовые шаблоны сообщений
- [ ] Автосохранение настроек
- [ ] Проверка обновлений

---

## 📦 СБОРКА И РЕЛИЗ

### Создать файлы:

1. **teacher.spec** — PyInstaller для преподавателя
2. **student.spec** — PyInstaller для студента
3. **installer/teacher_setup.iss** — Inno Setup преподаватель
4. **installer/student_setup.iss** — Inno Setup студент
5. **build.bat** — Автоматическая сборка всего

### Тестирование перед релизом:

- [ ] Windows 7 SP1 (32-bit)
- [ ] Windows 10 (64-bit)
- [ ] Windows 11 (64-bit)
- [ ] Локальная сеть Ethernet
- [ ] WiFi 802.11n
- [ ] 10 студентов одновременно
- [ ] Трансляция 30+ минут

---

## 📊 Оценка времени

| Задача | Дни |
|--------|-----|
| TCP буферизация | 2 |
| Голосовая связь | 3 |
| Наблюдение | 2 |
| Веб-камера | 2 |
| Интерактивная доска | 4 |
| Запись урока | 2 |
| Экспорт HTML | 1 |
| Плавающая панель | 2 |
| Блокировка ввода | 1 |
| Иконки/ресурсы | 1 |
| UI улучшения | 3 |
| Тестирование | 3 |
| Сборка/установщик | 2 |
| **ИТОГО** | **~28 дней** |

---

## ✅ Готово (что уже сделано)

- [x] Сетевая инфраструктура (TCP/UDP/Multicast)
- [x] Сервер преподавателя
- [x] Клиент студента
- [x] Трансляция экрана (видео)
- [x] Чат преподаватель-студент
- [x] Блокировка экрана
- [x] Поднятие руки
- [x] Создание групп
- [x] Экзамены (5 типов вопросов)
- [x] Опросы
- [x] Автопроверка ответов
- [x] База данных SQLite
- [x] Аудиолаборатория (код)
- [x] Видеоплеер (код)
- [x] Передача файлов (код, без сети)
- [x] Удаленные команды (код)
- [x] QSS стилизация

---

*Обновлено: 02.01.2026*

