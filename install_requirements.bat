@echo off
title Lingua Classroom - Installing Dependencies
echo ========================================
echo Installing Lingua Classroom Dependencies
echo ========================================
echo.

REM Проверка версии Python
python --version 2>&1 | findstr /C:"3.14" >nul
if %errorlevel%==0 (
    echo.
    echo WARNING: You are using Python 3.14!
    echo Some packages may not be available yet.
    echo.
    echo Recommended: Use Python 3.11 or 3.12 for best compatibility.
    echo.
    echo Press any key to continue with Python 3.14 installation...
    echo Or close this window and use install_requirements_py314.bat
    pause
    echo.
    echo Using Python 3.14 installation script...
    call install_requirements_py314.bat
    exit /b
)

echo This may take a few minutes...
echo.

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo.
echo ========================================
echo Installation complete!
echo ========================================
pause

