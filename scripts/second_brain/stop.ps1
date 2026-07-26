$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "stop-watcher.ps1")
& (Join-Path $PSScriptRoot "stop-api.ps1")
