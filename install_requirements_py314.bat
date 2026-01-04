@echo off
title Lingua Classroom - Installing Dependencies (Python 3.14)
echo ========================================
echo Installing Lingua Classroom Dependencies
echo Python 3.14 Compatible Version
echo ========================================
echo.
echo This may take a few minutes...
echo.

echo Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Installing core dependencies...
pip install --upgrade PyQt5 numpy opencv-python Pillow mss

echo.
echo Installing network dependencies...
pip install --upgrade zeroconf requests

echo.
echo Installing audio dependencies (may fail on some systems)...
pip install --upgrade pydub sounddevice soundfile || echo Warning: Some audio packages failed to install

echo.
echo Installing utilities...
pip install --upgrade python-dateutil cryptography pytz colorlog PyYAML

echo.
echo Installing build tools...
pip install --upgrade pyinstaller

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Note: Some packages may not be available for Python 3.14 yet.
echo The core functionality should work without them.
echo.
pause

