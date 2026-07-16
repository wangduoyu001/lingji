$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PythonW = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonW)) {
    throw "Desktop environment is missing. Run scripts\desktop\setup.ps1 first."
}
Start-Process -FilePath $PythonW -WorkingDirectory $Root -WindowStyle Hidden -ArgumentList "-m", "second_brain.desktop.main"
Write-Output "LingJi Second Brain desktop started"
