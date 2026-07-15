$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Runtime = Join-Path $Root "data\runtime"
$Logs = Join-Path $Root "logs\second_brain"
New-Item -ItemType Directory -Path $Runtime, $Logs -Force | Out-Null
Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 5 | Out-Null
$PidFile = Join-Path $Runtime "watcher.pid"
if (Test-Path $PidFile) {
    $Existing = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($Existing -and (Get-Process -Id $Existing -ErrorAction SilentlyContinue)) {
        Write-Output "Second-brain watcher already running with PID $Existing"
        exit 0
    }
}
$Python = (Get-Command python).Source
$Process = Start-Process -FilePath $Python -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
    -ArgumentList "-m", "second_brain.watcher" `
    -RedirectStandardOutput (Join-Path $Logs "watcher.stdout.log") `
    -RedirectStandardError (Join-Path $Logs "watcher.stderr.log")
$Process.Id | Set-Content -LiteralPath $PidFile -Encoding ascii
Write-Output "Second-brain watcher started. PID=$($Process.Id)"
