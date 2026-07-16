$ErrorActionPreference = "Stop"
$ShortcutName = -join ([char[]](0x7075, 0x673A, 0x7B2C, 0x4E8C, 0x5927, 0x8111))
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) ($ShortcutName + ".lnk")
Remove-Item -LiteralPath $ShortcutPath -Force -ErrorAction SilentlyContinue
Write-Output "Desktop shortcut removed"
