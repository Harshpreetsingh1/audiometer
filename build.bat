@echo off
REM ============================================================
REM Audiometry Pro - Build Script
REM ============================================================
REM This script builds a standalone Windows executable using PyInstaller.
REM Prerequisites: pip install pyinstaller
REM ============================================================

echo.
echo ============================================================
echo   Building Audiometry Pro Executable
echo ============================================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed.
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "Audiometry_Pro.spec" del /q "Audiometry_Pro.spec"

REM Build the executable
echo Building executable...
pyinstaller --noconsole --onefile ^
    --name "Audiometry_Pro" ^
    --add-data "audiometer_ui.html;." ^
    --add-data "audiometer;audiometer" ^
    --add-data "ascending_method.py;." ^
    webview_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Build Complete!
echo ============================================================
echo   Output: dist\Audiometry_Pro.exe
echo ============================================================
echo.

pause
