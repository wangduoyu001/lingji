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

$sidecarManifestPath = Join-Path $desktopRoot "src-tauri/binaries/lingji-core-manifest.json"
if (-not (Test-Path $sidecarManifestPath)) {
  throw "Packaged runtime manifest was not produced"
}
$sidecarManifest = Get-Content $sidecarManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($sidecarManifest.target_triple -ne $Target) {
  throw "Runtime sidecar target does not match the Desktop target"
}
if ($sidecarManifest.pyinstaller_mode -ne "onedir") {
  throw "Runtime sidecar must use the onedir packaging contract"
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
$sidecarManifestOutput = Join-Path $output "lingji-core-manifest.json"
Copy-Item $installer.FullName $installerOutput -Force
Copy-Item $appExecutable $executableOutput -Force
Copy-Item $sidecarManifestPath $sidecarManifestOutput -Force

$artifactFiles = @($installerOutput, $executableOutput, $sidecarManifestOutput)
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
  schema_version = 2
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
    python_sidecar_included = $true
    pyinstaller_mode = [string]$sidecarManifest.pyinstaller_mode
    sidecar_executable_bytes = [long]$sidecarManifest.executable.bytes
    sidecar_executable_sha256 = [string]$sidecarManifest.executable.sha256
    sidecar_runtime_file_count = [int]$sidecarManifest.runtime_directory.file_count
    sidecar_runtime_bytes = [long]$sidecarManifest.runtime_directory.bytes
    optional_media_providers_bundled = [bool]$sidecarManifest.optional_media_providers_bundled
    owner_data_root = "%LOCALAPPDATA%\\LingJi"
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
LingJi Windows Desktop + Packaged Runtime

Version: $version
Commit: $Commit
Build time (UTC): $BuildTimeUtc
Channel: $Channel
Target: $Target
Installer: NSIS current-user setup
Code signed: no

This P2-11B package contains the Tauri Desktop application and the fixed LingJi Python runtime Sidecar.
The Desktop manages only the Sidecar process it started. A healthy external 8766 process is detected but is not stopped or restarted.
Owner data is stored outside the installation directory under %LOCALAPPDATA%\LingJi by default.
Optional media providers and large local models are not bundled or downloaded automatically.
The automatic updater is not included yet.

Installing, upgrading or uninstalling this Desktop package must not intentionally delete the Obsidian Vault,
LingJi storage, runtime settings, SQLite state or Qdrant collections.
"@
$notes | Set-Content -Path (Join-Path $output "INSTALLATION-NOTES.txt") -Encoding UTF8

Write-Host "Windows Desktop + Sidecar release prepared at $output"
Get-ChildItem $output | Select-Object Name, Length | Format-Table -AutoSize
