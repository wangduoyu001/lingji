$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start-api.ps1")
& (Join-Path $PSScriptRoot "start-watcher.ps1")
