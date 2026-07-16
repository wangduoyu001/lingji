$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PidFile = Join-Path $Root "data\runtime\api.pid"
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
    Write-Output "Second-brain API stopped"
} else { Write-Output "Second-brain API is not running" }
