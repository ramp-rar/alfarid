# Сборка EXE установщика Alfarid

## Требования

1. **PyInstaller** — для создания EXE
```bash
pip install pyinstaller
```

2. **Inno Setup 6+** — для создания установщика
   - Скачать: https://jrsoftware.org/isdl.php
   - Установить в систему

## Шаг 1: Сборка EXE

```bash
# Из корня проекта:
cd build_scripts
build_all.bat
```

Это создаст:
- `dist/Alfarid_Teacher.exe` — приложение преподавателя
- `dist/Alfarid_Student.exe` — приложение студента

## Шаг 2: Создание установщика

```bash
# В Inno Setup откройте:
build_installer.iss

# Нажмите: Build > Compile
```

Это создаст:
- `installer/Alfarid-Setup-1.0.0.exe` — установщик (~150 MB)

## Шаг 3: Тестирование

1. Запустите `Alfarid-Setup-1.0.0.exe`
2. Выберите компоненты:
   - Teacher (Преподаватель)
   - Student (Студент)
   - Backend (Опционально)
3. Установите
4. Запустите из меню "Пуск"

## Структура установки

```
C:\Program Files\Alfarid\
├── Teacher\
│   ├── Alfarid_Teacher.exe
│   ├── config.ini
│   └── resources\
│
├── Student\
│   ├── Alfarid_Student.exe
│   ├── config.ini
│   └── resources\
│
├── Backend\ (опционально)
│   └── app\
│
└── docs\
```

## Размеры

- Teacher App: ~80 MB
- Student App: ~70 MB
- Установщик: ~150 MB (сжатый)
- После установки: ~200 MB

## Автоматизация

Для автоматической сборки:

```bash
# 1. Сборка EXE
build_all.bat

# 2. Создание установщика
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_installer.iss

# Готово! Установщик в installer\
```

## Примечания

- EXE файлы могут быть заблокированы антивирусом при первом запуске (ложное срабатывание)
- Для подписи EXE нужен код-signing сертификат (опционально)
- Для автообновлений можно добавить update checker



