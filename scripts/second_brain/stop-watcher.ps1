$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PidFile = Join-Path $Root "data\runtime\watcher.pid"
$WorkspaceFile = Join-Path $Root "data\runtime\watcher.workspace"
function Stop-ProcessTree([int]$Id) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$Id" -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-ProcessTree ([int]$_.ProcessId)
    }
    Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue
}
if (Test-Path $PidFile) {
    $ProcessId = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ProcessId) { Stop-ProcessTree ([int]$ProcessId) }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $WorkspaceFile -Force -ErrorAction SilentlyContinue
    Write-Output "Second-brain watcher stopped"
} else { Write-Output "Second-brain watcher is not running" }
