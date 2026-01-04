# Audiometer Pro - PowerShell Launcher
# Double-click this file or right-click and select "Run with PowerShell"

$Host.UI.RawUI.WindowTitle = "Audiometer Pro - Launcher"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "         Audiometer Pro - Launcher         " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Audiometer Pro application..." -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check for virtual environment and activate it
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Using virtual environment..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
}
else {
    Write-Host "Note: No virtual environment found, using system Python." -ForegroundColor Yellow
}

# Launch the application
try {
    python webview_app.py
}
catch {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "ERROR: Application failed to start!" -ForegroundColor Red
    Write-Host "Please check if all dependencies are installed." -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
