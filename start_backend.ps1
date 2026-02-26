#!/usr/bin/env powershell
# Simple backend restart script
Write-Host "🚀 Restarting Backend Server..." -ForegroundColor Green

# Navigate to project
Set-Location D:\BotTradingBinace

# Kill port 8000 if in use
try {
    $connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction Stop
    foreach ($conn in $connections) {
        Write-Host "Stopping process on port 8000..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "No process on port 8000" -ForegroundColor Gray
}

# Start backend
Write-Host "Starting FastAPI on port 8000..." -ForegroundColor Cyan
& .venv\Scripts\python.exe -m uvicorn apps.api.main:app --port 8000 --host 0.0.0.0 --reload
