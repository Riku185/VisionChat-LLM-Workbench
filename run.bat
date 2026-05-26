@echo off
echo ========================================
echo   Vision Chat — Starting...
echo ========================================

REM Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python main.py
pause
