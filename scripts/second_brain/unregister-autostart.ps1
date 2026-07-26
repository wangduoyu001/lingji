$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName "LingJiSecondBrain" -Confirm:$false -ErrorAction SilentlyContinue
Write-Output "Removed startup task: LingJiSecondBrain"
