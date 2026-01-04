# Установка для Python 3.14

## ⚠️ Важно

Python 3.14 - это очень новая версия, и многие библиотеки еще не имеют готовых сборок для нее.

## Рекомендации

### Вариант 1: Используйте Python 3.11 или 3.12 (рекомендуется)

Скачайте Python 3.11 или 3.12:
- Python 3.11: https://www.python.org/downloads/release/python-3119/
- Python 3.12: https://www.python.org/downloads/release/python-3120/

Затем установите зависимости:
```bash
pip install -r requirements.txt
```

### Вариант 2: Установка для Python 3.14

Если вы хотите использовать Python 3.14, используйте специальный скрипт:

```bash
install_requirements_py314.bat
```

Или вручную:
```bash
pip install --upgrade PyQt5 numpy opencv-python Pillow mss zeroconf requests pydub sounddevice soundfile python-dateutil cryptography pytz colorlog PyYAML pyinstaller
```

## Известные проблемы с Python 3.14

### ❌ Не работают (пока нет сборок):
- `netifaces` - используется для определения сетевых интерфейсов
- `PyAudio` - аудиозахват (есть альтернатива - sounddevice)

### ⚠️ Могут работать с ошибками:
- Некоторые пакеты могут требовать компиляции из исходников
- Visual Studio Build Tools может потребоваться для Windows

### ✅ Работают нормально:
- PyQt5 - GUI
- opencv-python - видео
- numpy - вычисления
- mss - захват экрана
- sounddevice - аудио (альтернатива PyAudio)

## Обходные пути

### netifaces (получение локального IP)

Вместо `netifaces` используется встроенная альтернатива в `src/common/utils.py`:

```python
def get_local_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
```

### PyAudio (аудиозахват)

Вместо `PyAudio` используется `sounddevice` - он лучше поддерживается и имеет сборки для новых версий Python.

## Запуск

После установки зависимостей запустите:

```bash
# Преподаватель
python teacher_app.py

# Студент
python student_app.py
```

## Тестирование

Если некоторые функции не работают:

1. **Трансляция экрана** - должна работать (использует mss + opencv)
2. **Сетевое подключение** - должно работать (использует встроенный socket)
3. **Аудио** - может работать с ошибками (зависит от sounddevice)
4. **GUI** - должен работать (PyQt5 поддерживает 3.14)

## Рекомендуемая конфигурация

Для производственного использования рекомендуется:

- **Python 3.11.9** - стабильная, все пакеты работают
- **Python 3.12.x** - новая, большинство пакетов работают
- **Python 3.14.x** - экспериментальная, могут быть проблемы

## Помощь

Если у вас возникли проблемы:

1. Проверьте версию Python: `python --version`
2. Попробуйте установить пакеты по одному
3. Проверьте логи установки
4. Создайте issue на GitHub с описанием проблемы

## Альтернатива: Виртуальное окружение с Python 3.11

```bash
# Установите pyenv или используйте virtualenv
python3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

**Рекомендация:** Для стабильной работы используйте Python 3.11 или 3.12

