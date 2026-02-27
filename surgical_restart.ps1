# Surgical Kill
function Stop-PortProcess([int]$port) {
    Write-Host "Checking port $port..."
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess -gt 0) {
            Write-Host "Killing process $($conn.OwningProcess) on port $port"
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

Stop-PortProcess 8000
Stop-PortProcess 8001
Stop-PortProcess 3000

Write-Host "Waiting for cleanup..."
Start-Sleep -Seconds 5

# Start Backend
$venvPython = "D:\BotTradingBinace\.venv\Scripts\python.exe"
Write-Host "Starting Backend..."
Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn apps.api.main:app --port 8000 --host 0.0.0.0" -WorkingDirectory "D:\BotTradingBinace" -WindowStyle Hidden

# Start Worker
Write-Host "Starting Worker..."
Start-Process -FilePath $venvPython -ArgumentList "-m apps.worker.main" -WorkingDirectory "D:\BotTradingBinace" -WindowStyle Hidden

# Start Frontend
Write-Host "Starting Frontend..."
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --port 3000" -WorkingDirectory "D:\BotTradingBinace\apps\dashboard" -WindowStyle Hidden

Write-Host "System Refresh Complete."
