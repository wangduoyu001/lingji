$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PythonW = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonW)) { throw "pythonw.exe not found in $PythonW" }
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutName = -join ([char[]](0x7075, 0x673A, 0x7B2C, 0x4E8C, 0x5927, 0x8111))
$ShortcutPath = Join-Path $Desktop ($ShortcutName + ".lnk")
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonW
$Shortcut.Arguments = '-m second_brain.desktop.main'
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "LingJi Second Brain Windows desktop console"
$Shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,109"
$Shortcut.Save()
Write-Output "Desktop shortcut created: $ShortcutPath"
