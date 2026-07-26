param(
    [ValidateSet("production", "acceptance")]
    [string]$Workspace = "production"
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Runtime = Join-Path $Root "data\runtime"
$Logs = Join-Path $Root "logs\second_brain"
New-Item -ItemType Directory -Path $Runtime, $Logs -Force | Out-Null
Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 5 | Out-Null
$PidFile = Join-Path $Runtime "watcher.pid"
$WorkspaceFile = Join-Path $Runtime "watcher.workspace"
if (Test-Path $PidFile) {
    $Existing = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($Existing -and (Get-Process -Id $Existing -ErrorAction SilentlyContinue)) {
        Write-Output "Second-brain watcher already running with PID $Existing"
        exit 0
    }
}
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }
$Process = Start-Process -FilePath $Python -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
    -ArgumentList "-m", "second_brain.watcher", "--workspace", $Workspace `
    -RedirectStandardOutput (Join-Path $Logs "watcher.stdout.log") `
    -RedirectStandardError (Join-Path $Logs "watcher.stderr.log")
$Process.Id | Set-Content -LiteralPath $PidFile -Encoding ascii
$Workspace | Set-Content -LiteralPath $WorkspaceFile -Encoding ascii
Write-Output "Second-brain watcher started. PID=$($Process.Id), workspace=$Workspace"
