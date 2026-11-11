@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Please install Python 3.10 or newer from python.org.
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
echo.
echo Starting ResolveIQ v1.2. Ollama + Qwen are detected automatically.
echo If not available, offline rules are used without stopping the application.
echo Open http://localhost:8000 in your browser.
echo Press Ctrl+C to stop the server.
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
