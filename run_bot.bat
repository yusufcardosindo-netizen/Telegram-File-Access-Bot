@echo off
title Telegram File Access Bot - Made by @VIJAYEDITOR77
cd /d "%~dp0"
echo ============================================================
echo   Telegram File Access Bot with 5-Minute Self-Destruction
echo   Watermark: Made by @VIJAYEDITOR77 on Telegram
echo ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org
    pause
    exit /b
)

echo Checking dependencies...
python -c "import telegram, dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    python -m pip install -r requirements.txt
)

echo.
echo Starting Bot...
python bot.py
if %errorlevel% neq 0 (
    echo.
    echo Bot stopped with an error. Check .env configuration!
    pause
)
