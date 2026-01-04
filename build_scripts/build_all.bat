@echo off
REM Сборка EXE для Alfarid
REM Требуется: pip install pyinstaller

echo ========================================
echo Alfarid Build Script
echo ========================================
echo.

REM Проверка PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller не установлен!
    echo Установите: pip install pyinstaller
    pause
    exit /b 1
)

echo [OK] PyInstaller установлен
echo.

REM Очистка старых сборок
echo Очистка старых сборок...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo.

REM Сборка Teacher App
echo ========================================
echo Сборка Teacher App...
echo ========================================
pyinstaller build_scripts\build_teacher.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] Ошибка сборки Teacher App
    pause
    exit /b 1
)

echo [OK] Teacher App собран
echo.

REM Сборка Student App
echo ========================================
echo Сборка Student App...
echo ========================================
pyinstaller build_scripts\build_student.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] Ошибка сборки Student App
    pause
    exit /b 1
)

echo [OK] Student App собран
echo.

REM Копируем config и ресурсы
echo Копирование файлов...
copy config.ini dist\Alfarid_Teacher\ >nul
copy config.ini dist\Alfarid_Student\ >nul

if exist resources (
    xcopy /E /I /Y resources dist\Alfarid_Teacher\resources >nul
    xcopy /E /I /Y resources dist\Alfarid_Student\resources >nul
)

echo.
echo ========================================
echo Сборка завершена!
echo ========================================
echo.
echo Файлы в dist\:
echo   - Alfarid_Teacher.exe
echo   - Alfarid_Student.exe
echo.
echo Для создания установщика запустите:
echo   build_installer.bat
echo.
pause



