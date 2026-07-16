$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Runtime = Join-Path $Root "data\runtime"
$Logs = Join-Path $Root "logs\second_brain"
New-Item -ItemType Directory -Path $Runtime, $Logs -Force | Out-Null
$PidFile = Join-Path $Runtime "api.pid"
if (Test-Path $PidFile) {
    $Existing = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($Existing -and (Get-Process -Id $Existing -ErrorAction SilentlyContinue)) {
        Write-Output "Second-brain API already running with PID $Existing"
        exit 0
    }
}
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }
$Process = Start-Process -FilePath $Python -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
    -ArgumentList "-m", "uvicorn", "second_brain.api:app", "--host", "127.0.0.1", "--port", "8765" `
    -RedirectStandardOutput (Join-Path $Logs "api.stdout.log") `
    -RedirectStandardError (Join-Path $Logs "api.stderr.log")
$Process.Id | Set-Content -LiteralPath $PidFile -Encoding ascii
for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 2
        if ($Health.status -eq "ok") {
            Write-Output "Second-brain API started. PID=$($Process.Id), port=8765"
            exit 0
        }
    } catch {}
}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
throw "Second-brain API failed health check. See $Logs"
