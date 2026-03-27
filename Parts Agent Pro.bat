@echo off
REM Parts Agent Pro - Unified Desktop Application
REM Launch script for easy access

echo Starting Parts Agent Pro...
echo.

REM Set up environment
set PATH=%PATH%;C:\Users\Owner\.local\bin

REM Change to project directory
cd /d "C:\Users\Owner\Desktop\Parts Agent 20260313"

REM Launch the unified GUI application
echo Launching unified GUI interface...
uv run python main_app.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)