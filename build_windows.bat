@echo off
REM Nova Windows Build — PyInstaller
REM Requirements: pip install pyinstaller pillow pystray keyboard pywin32
REM Output: dist\Nova\Nova.exe

echo Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo Installing PyInstaller...
  pip install pyinstaller
)

echo Building Nova...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --name Nova ^
  --onedir ^
  --windowed ^
  --icon assets\nova.ico ^
  --add-data "assets;assets" ^
  --add-data ".env.example;." ^
  --hidden-import sounddevice ^
  --hidden-import numpy ^
  --hidden-import pyttsx3 ^
  --hidden-import comtypes ^
  --hidden-import vosk ^
  --hidden-import pyautogui ^
  --hidden-import win32gui ^
  --hidden-import pystray ^
  --hidden-import PIL ^
  --hidden-import keyboard ^
  --hidden-import mss ^
  --hidden-import playwright ^
  --collect-all faster_whisper ^
  --collect-all openai ^
  run.py

if errorlevel 1 (
  echo Build failed. See output above.
  exit /b 1
)

echo.
echo Build complete: dist\Nova\Nova.exe
echo.
echo IMPORTANT: Playwright browser not bundled. On target machine run:
echo   setup_browser.bat
echo.
echo To enable startup: set START_WITH_WINDOWS=true in .env or use tray menu.
echo.
pause
