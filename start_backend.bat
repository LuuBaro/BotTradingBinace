@echo off
REM Kill process on port 8001 and restart backend
cd /d D:\BotTradingBinace

echo Checking for processes on port 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001') do (
    echo Killing process %%a
    taskkill /PID %%a /F 2>nul
)

timeout /t 2

echo Starting FastAPI backend...
call .venv\Scripts\python.exe -m uvicorn apps.api.main:app --port 8001 --host 0.0.0.0 --reload

pause
