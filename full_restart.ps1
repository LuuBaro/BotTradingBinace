# 1. Kill everything
Write-Host "Stopping all Python processes..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "Cleaning caches..."
# Remove Python caches
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
# Remove Vite cache
if (Test-Path "apps\dashboard\node_modules\.vite") {
    Remove-Item -Path "apps\dashboard\node_modules\.vite" -Force -Recurse -ErrorAction SilentlyContinue
}

Write-Host "Waiting for ports to clear..."
Start-Sleep -Seconds 3

# 2. Check ports
$ports = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
if ($ports) {
    Write-Host "Warning: Ports still occupied. Waiting longer..."
    Start-Sleep -Seconds 5
}

# 3. Start Backend
Write-Host "Starting Backend on 8000..."
$venvPython = "D:\BotTradingBinace\.venv\Scripts\python.exe"
Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn apps.api.main:app --port 8000 --host 0.0.0.0" -WorkingDirectory "D:\BotTradingBinace" -WindowStyle Hidden

# 4. Start Worker
Write-Host "Starting Worker..."
Start-Process -FilePath $venvPython -ArgumentList "-m apps.worker.main" -WorkingDirectory "D:\BotTradingBinace" -WindowStyle Hidden

# 5. Start Frontend
Write-Host "Starting Frontend (Vite)..."
Set-Location "D:\BotTradingBinace\apps\dashboard"
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -WorkingDirectory "D:\BotTradingBinace\apps\dashboard" -WindowStyle Hidden

Write-Host "All systems restarted on Port 8000 (BE) and 3000 (FE)."
