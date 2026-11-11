@echo off
cd /d "%~dp0"
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama is not installed. Download and install it from https://ollama.com/download
  echo Then run this file again. ResolveIQ still works with offline rules meanwhile.
  pause
  exit /b 1
)
echo Downloading the Qwen2.5 3B model locally (about 1.9 GB, first time only)...
ollama pull qwen2.5:3b
if errorlevel 1 (
  echo Model download unavailable. Check internet and retry later. Offline mode still works.
  pause
  exit /b 1
)
echo.
echo Qwen is installed. Leave Ollama running, start ResolveIQ, and press Refresh AI status.
ollama list
pause
