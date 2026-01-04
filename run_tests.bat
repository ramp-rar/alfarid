@echo off
echo ========================================
echo Lingua Classroom - Testing Suite
echo ========================================
echo.

echo Starting both Teacher and Student apps for testing...
echo.

echo Starting Teacher App...
start "Lingua Teacher" python teacher_app.py

timeout /t 3 /nobreak >nul

echo Starting Student App...
start "Lingua Student" python student_app.py

echo.
echo ========================================
echo Both applications started!
echo Test the connection between them.
echo ========================================
pause

