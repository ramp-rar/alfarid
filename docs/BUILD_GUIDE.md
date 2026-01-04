# Руководство по сборке Lingua Classroom

## Сборка установщиков Windows

### Требования

- Python 3.9+
- PyInstaller
- NSIS (Nullsoft Scriptable Install System)

### Шаг 1: Установка зависимостей

```bash
pip install pyinstaller
```

Скачайте и установите NSIS: https://nsis.sourceforge.io/

### Шаг 2: Создание исполняемых файлов

#### Для преподавателя:

```bash
pyinstaller --name="LinguaClassroom-Teacher" ^
            --windowed ^
            --onefile ^
            --icon=resources/teacher_icon.ico ^
            --add-data="resources;resources" ^
            --add-data="config.ini;." ^
            teacher_app.py
```

#### Для студента:

```bash
pyinstaller --name="LinguaClassroom-Student" ^
            --windowed ^
            --onefile ^
            --icon=resources/student_icon.ico ^
            --add-data="resources;resources" ^
            --add-data="config.ini;." ^
            student_app.py
```

После выполнения команд исполняемые файлы будут находиться в папке `dist/`.

### Шаг 3: Создание установщика с NSIS

#### Создайте файл `installer/teacher_installer.nsi`:

```nsis
; Lingua Classroom Teacher Installer Script

!define APP_NAME "Lingua Classroom Teacher"
!define APP_VERSION "1.0.0"
!define PUBLISHER "Lingua Classroom Community"
!define WEB_SITE "https://lingua-classroom.org"
!define INSTALL_DIR "$PROGRAMFILES\LinguaClassroom\Teacher"

Name "${APP_NAME}"
OutFile "LinguaClassroom-Teacher-v${APP_VERSION}-setup.exe"
InstallDir "${INSTALL_DIR}"

!include "MUI2.nsh"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Основные файлы" SecMain
    SetOutPath "$INSTDIR"
    
    ; Копируем исполняемый файл
    File "dist\LinguaClassroom-Teacher.exe"
    
    ; Копируем ресурсы
    SetOutPath "$INSTDIR\resources"
    File /r "resources\*"
    
    ; Копируем конфигурацию
    SetOutPath "$INSTDIR"
    File "config.ini"
    
    ; Создаем ярлыки
    CreateDirectory "$SMPROGRAMS\Lingua Classroom"
    CreateShortCut "$SMPROGRAMS\Lingua Classroom\Teacher.lnk" "$INSTDIR\LinguaClassroom-Teacher.exe"
    CreateShortCut "$DESKTOP\Lingua Classroom Teacher.lnk" "$INSTDIR\LinguaClassroom-Teacher.exe"
    
    ; Создаем uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Записываем в реестр
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\LinguaClassroom-Teacher.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${WEB_SITE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Удаляем файлы
    Delete "$INSTDIR\LinguaClassroom-Teacher.exe"
    Delete "$INSTDIR\config.ini"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR\resources"
    RMDir "$INSTDIR"
    
    ; Удаляем ярлыки
    Delete "$SMPROGRAMS\Lingua Classroom\Teacher.lnk"
    Delete "$DESKTOP\Lingua Classroom Teacher.lnk"
    RMDir "$SMPROGRAMS\Lingua Classroom"
    
    ; Удаляем из реестра
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
```

#### Создайте аналогичный файл для студента: `installer/student_installer.nsi`

### Шаг 4: Компиляция установщиков

```bash
cd installer
makensis teacher_installer.nsi
makensis student_installer.nsi
```

Установщики будут созданы в папке `installer/`.

## Сборка portable версии

Для создания portable версии (без установки):

```bash
# Создайте папку
mkdir LinguaClassroom-Portable

# Скопируйте файлы
copy dist\LinguaClassroom-Teacher.exe LinguaClassroom-Portable\
copy dist\LinguaClassroom-Student.exe LinguaClassroom-Portable\
xcopy resources LinguaClassroom-Portable\resources\ /E /I
copy config.ini LinguaClassroom-Portable\

# Создайте архив
# Используйте 7-Zip или WinRAR для создания .zip архива
```

## Тестирование

### Перед релизом обязательно протестируйте:

1. ✅ Установка на чистой Windows
2. ✅ Запуск преподавателя
3. ✅ Запуск студента
4. ✅ Подключение студента к преподавателю
5. ✅ Все основные функции работают
6. ✅ Удаление через Control Panel

### Тестовые конфигурации:

- Windows 7 SP1 (32-bit)
- Windows 10 (64-bit)
- Windows 11 (64-bit)

## Подписывание кода (опционально)

Для повышения доверия рекомендуется подписать исполняемые файлы цифровой подписью:

```bash
signtool sign /f certificate.pfx /p password /t http://timestamp.comodoca.com LinguaClassroom-Teacher.exe
```

## CI/CD автоматизация

### GitHub Actions workflow (.github/workflows/build.yml):

```yaml
name: Build Installers

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executables
      run: |
        pyinstaller teacher.spec
        pyinstaller student.spec
    
    - name: Install NSIS
      run: choco install nsis
    
    - name: Build installers
      run: |
        makensis installer/teacher_installer.nsi
        makensis installer/student_installer.nsi
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v2
      with:
        name: installers
        path: installer/*.exe
```

## Структура релиза

```
Release/
├── LinguaClassroom-Teacher-v1.0-setup.exe
├── LinguaClassroom-Student-v1.0-setup.exe
├── LinguaClassroom-v1.0-portable.zip
├── Documentation/
│   ├── QuickStart-RU.pdf
│   ├── TeacherGuide-RU.pdf
│   ├── StudentGuide-RU.pdf
│   └── ...
└── Source/
    └── lingua-classroom-v1.0-source.zip
```

## Контрольные суммы

После сборки создайте файл с контрольными суммами:

```bash
certutil -hashfile LinguaClassroom-Teacher-v1.0-setup.exe SHA256
certutil -hashfile LinguaClassroom-Student-v1.0-setup.exe SHA256
```

Сохраните в файл `checksums.txt`.

---

**Вопросы?** Обращайтесь: dev@lingua-classroom.org

