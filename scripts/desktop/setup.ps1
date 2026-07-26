$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Venv = Join-Path $Root ".venv"
$Cache = "D:\codex\cache\pip"
New-Item -ItemType Directory -Path $Cache -Force | Out-Null
$env:PIP_CACHE_DIR = $Cache
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    Write-Output "Creating D-drive virtual environment..."
    python -m venv $Venv
}
$Python = Join-Path $Venv "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements-second-brain.txt") -r (Join-Path $Root "requirements-desktop.txt")
& $Python -c "import PySide6, fastapi, qdrant_client, requests; print('DESKTOP_RUNTIME_OK', PySide6.__version__)"
& (Join-Path $PSScriptRoot "create-shortcut.ps1")
Write-Output "LingJi desktop environment is ready at $Venv"
