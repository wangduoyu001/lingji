$ErrorActionPreference = "Stop"
$StartScript = (Resolve-Path (Join-Path $PSScriptRoot "start.ps1")).Path
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "LingJiSecondBrain" -Action $Action -Trigger $Trigger -Principal $Principal -Description "Optional LingJi second-brain API and bounded watcher" -Force
Write-Output "Registered optional startup task: LingJiSecondBrain"
