@echo off
title Audiometer Pro - Launcher
echo ============================================
echo         Audiometer Pro - Launcher
echo ============================================
echo.
echo Starting Audiometer Pro application...
echo.

cd /d "%~dp0"

REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Using virtual environment...
) else (
    echo Note: No virtual environment found, using system Python.
)

REM Launch the application
python webview_app.py

REM If there was an error, pause to show the message
if errorlevel 1 (
    echo.
    echo ============================================
    echo ERROR: Application failed to start!
    echo Please check if all dependencies are installed.
    echo ============================================
    pause
)
