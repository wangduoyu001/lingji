param(
  [Parameter(Mandatory = $true)]
  [string]$Commit,

  [Parameter(Mandatory = $true)]
  [string]$BuildTimeUtc,

  [string]$Channel = "ci",
  [string]$Target = "x86_64-pc-windows-msvc",
  [string]$OutputDirectory = "release/windows-x64"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$desktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tauriConfigPath = Join-Path $desktopRoot "src-tauri/tauri.conf.json"
$tauriConfig = Get-Content $tauriConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$version = [string]$tauriConfig.version
if ([string]::IsNullOrWhiteSpace($version)) {
  throw "Tauri version is missing"
}

$bundleDirectory = Join-Path $desktopRoot "src-tauri/target/$Target/release/bundle/nsis"
if (-not (Test-Path $bundleDirectory)) {
  $bundleDirectory = Join-Path $desktopRoot "src-tauri/target/release/bundle/nsis"
}
$installer = Get-ChildItem -Path $bundleDirectory -Filter "*-setup.exe" -File -ErrorAction Stop |
  Sort-Object LastWriteTimeUtc -Descending |
  Select-Object -First 1
if ($null -eq $installer -or $installer.Length -le 0) {
  throw "NSIS installer was not produced"
}

$appExecutableCandidates = @(
  (Join-Path $desktopRoot "src-tauri/target/$Target/release/lingji-control-center.exe"),
  (Join-Path $desktopRoot "src-tauri/target/release/lingji-control-center.exe")
)
$appExecutable = $appExecutableCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($appExecutable)) {
  throw "Desktop executable was not produced"
}

$output = Join-Path $desktopRoot $OutputDirectory
if (Test-Path $output) {
  Remove-Item $output -Recurse -Force
}
New-Item -ItemType Directory -Path $output -Force | Out-Null

$installerName = "LingJi_${version}_windows_x64_setup.exe"
$executableName = "LingJi_${version}_windows_x64.exe"
$installerOutput = Join-Path $output $installerName
$executableOutput = Join-Path $output $executableName
Copy-Item $installer.FullName $installerOutput -Force
Copy-Item $appExecutable $executableOutput -Force

$artifactFiles = @($installerOutput, $executableOutput)
$artifacts = foreach ($artifactPath in $artifactFiles) {
  $file = Get-Item $artifactPath
  if ($file.Length -le 0) {
    throw "Release artifact is empty: $($file.Name)"
  }
  $hash = Get-FileHash -Path $file.FullName -Algorithm SHA256
  [ordered]@{
    name = $file.Name
    bytes = $file.Length
    sha256 = $hash.Hash.ToLowerInvariant()
  }
}

$metadata = [ordered]@{
  schema_version = 1
  product_name = "LingJi"
  display_name = "灵机"
  version = $version
  commit = $Commit
  build_time_utc = $BuildTimeUtc
  channel = $Channel
  target = $Target
  installer_format = "nsis"
  installer_install_mode = "currentUser"
  webview_install_mode = "embedBootstrapper"
  signed = $false
  artifacts = $artifacts
  data_preservation = [ordered]@{
    owner_data_bundled = $false
    uninstall_deletes_owner_data = $false
    protected_data = @("Obsidian Vault", "LingJi storage", "runtime settings", "SQLite state", "Qdrant collections")
  }
  runtime_boundary = [ordered]@{
    control_api = "http://127.0.0.1:8766"
    python_sidecar_included = $false
    updater_included = $false
  }
}

$metadataPath = Join-Path $output "build-metadata.json"
$metadata | ConvertTo-Json -Depth 8 | Set-Content -Path $metadataPath -Encoding UTF8

$sumLines = foreach ($artifact in $artifacts) {
  "$($artifact.sha256)  $($artifact.name)"
}
$sumLines | Set-Content -Path (Join-Path $output "SHA256SUMS.txt") -Encoding ASCII

$notes = @"
LingJi Windows Release Baseline

Version: $version
Commit: $Commit
Build time (UTC): $BuildTimeUtc
Channel: $Channel
Target: $Target
Installer: NSIS current-user setup
Code signed: no

This P2-11A package contains the Tauri Desktop application only.
The LingJi Python runtime sidecar and automatic service lifecycle are planned for P2-11B.
Until then, the authenticated local control service on 127.0.0.1:8766 must be started separately.

Installing, upgrading or uninstalling this Desktop package must not intentionally delete the Obsidian Vault,
LingJi storage, runtime settings, SQLite state or Qdrant collections.
"@
$notes | Set-Content -Path (Join-Path $output "INSTALLATION-NOTES.txt") -Encoding UTF8

Write-Host "Windows release baseline prepared at $output"
Get-ChildItem $output | Select-Object Name, Length | Format-Table -AutoSize
