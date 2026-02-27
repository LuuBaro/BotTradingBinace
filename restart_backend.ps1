# Kill any existing Python processes on port 8000
$processes = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { $_.OwningProcess }

foreach ($procId in $processes) {
    if ($procId -and $procId -ne $pid) {
        Write-Host "Force killing process $procId on port 8000..."
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2 # Give it time to release the port
    }
}

Write-Host "Starting FastAPI backend on port 8000..."
$venvPython = "D:\BotTradingBinace\.venv\Scripts\python.exe"
$apiPath = "apps.api.main:app"

Set-Location D:\BotTradingBinace
& $venvPython -m uvicorn $apiPath --port 8000 --host 0.0.0.0 --reload

Write-Host "Backend started!"
