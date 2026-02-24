# Kill any existing Python processes on port 8001
$processes = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | ForEach-Object { $_.OwningProcess }

foreach ($pid in $processes) {
    Write-Host "Killing process $pid on port 8001..."
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Write-Host "Starting FastAPI backend on port 8001..."
$venvPython = "D:\BotTradingBinace\.venv\Scripts\python.exe"
$apiPath = "apps.api.main:app"

Set-Location D:\BotTradingBinace
& $venvPython -m uvicorn $apiPath --port 8001 --host 0.0.0.0 --reload

Write-Host "Backend started!"
