@echo off
REM Setup Playwright browser for Nova — run once after install/build
echo Installing Playwright browsers (Chromium)...
python -m playwright install chromium
if errorlevel 1 (
  echo Failed. Try: pip install playwright && playwright install chromium
  exit /b 1
)
echo Chromium installed.
echo You can also run: python -m playwright install
pause
