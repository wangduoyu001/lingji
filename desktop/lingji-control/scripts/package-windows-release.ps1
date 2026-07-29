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

function Get-PeSubsystem {
  param([Parameter(Mandatory = $true)][string]$Path)

  $stream = [System.IO.File]::OpenRead($Path)
  $reader = New-Object System.IO.BinaryReader($stream)
  try {
    if ($stream.Length -lt 256) {
      throw "PE file is too small: $Path"
    }

    $stream.Position = 0x3c
    $peOffset = $reader.ReadInt32()
    if ($peOffset -lt 0 -or ($peOffset + 94) -gt $stream.Length) {
      throw "Invalid PE header offset: $Path"
    }

    $stream.Position = $peOffset
    if ($reader.ReadUInt32() -ne 0x00004550) {
      throw "Missing PE signature: $Path"
    }

    $optionalHeaderOffset = $peOffset + 24
    $stream.Position = $optionalHeaderOffset
    $magic = $reader.ReadUInt16()
    if ($magic -ne 0x010b -and $magic -ne 0x020b) {
      throw "Unsupported PE optional header: $Path"
    }

    $stream.Position = $optionalHeaderOffset + 68
    return [int]$reader.ReadUInt16()
  }
  finally {
    $reader.Dispose()
    $stream.Dispose()
  }
}

$desktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tauriRoot = Join-Path $desktopRoot "src-tauri"
$tauriConfigPath = Join-Path $tauriRoot "tauri.conf.json"
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

$sidecarManifestPath = Join-Path $tauriRoot "binaries/lingji-core-manifest.json"
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

$sidecarRelativePath = ([string]$sidecarManifest.executable.path).Replace("/", "\")
$sidecarExecutable = Join-Path $tauriRoot $sidecarRelativePath
if (-not (Test-Path $sidecarExecutable)) {
  throw "Runtime sidecar executable was not produced: $sidecarExecutable"
}

$windowsGuiSubsystem = 2
$desktopSubsystem = Get-PeSubsystem -Path $appExecutable
$sidecarSubsystem = Get-PeSubsystem -Path $sidecarExecutable
if ($desktopSubsystem -ne $windowsGuiSubsystem) {
  throw "Desktop executable must use the Windows GUI subsystem; actual value: $desktopSubsystem"
}
if ($sidecarSubsystem -ne $windowsGuiSubsystem) {
  throw "Runtime sidecar must use the Windows GUI subsystem; actual value: $sidecarSubsystem"
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
  schema_version = 4
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
  desktop_pe_subsystem = "windows_gui"
  signed = $false
  artifacts = $artifacts
  data_preservation = [ordered]@{
    owner_data_bundled = $false
    uninstall_deletes_owner_data = $false
    bootstrap_config = "%LOCALAPPDATA%\LingJi\desktop-bootstrap.json"
    bootstrap_config_contains_runtime_data = $false
    protected_data = @("Obsidian Vault", "LingJi storage", "runtime settings", "SQLite state", "Qdrant collections")
  }
  runtime_boundary = [ordered]@{
    control_api = "http://127.0.0.1:8766"
    python_sidecar_included = $true
    pyinstaller_mode = [string]$sidecarManifest.pyinstaller_mode
    sidecar_pe_subsystem = "windows_gui"
    sidecar_executable_bytes = [long]$sidecarManifest.executable.bytes
    sidecar_executable_sha256 = [string]$sidecarManifest.executable.sha256
    sidecar_runtime_file_count = [int]$sidecarManifest.runtime_directory.file_count
    sidecar_runtime_bytes = [long]$sidecarManifest.runtime_directory.bytes
    optional_media_providers_bundled = [bool]$sidecarManifest.optional_media_providers_bundled
    owner_data_root = "owner-selected-non-system-drive\<workspace>"
    workspace_profiles = @("production", "acceptance")
    first_run_configuration_required = $true
    c_drive_runtime_data_allowed = $false
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
Desktop subsystem: Windows GUI
Sidecar subsystem: Windows GUI
Code signed: no

This package contains the Tauri Desktop application and the fixed LingJi Python runtime Sidecar.
The Desktop manages only the Sidecar process it started. A healthy external 8766 process is detected but is not stopped or restarted.
On first launch, the owner must select a non-C base data directory and choose the production or acceptance workspace.
Runtime databases, vectors, raw data, logs, cache, backups and generated data are stored under <selected base>\<workspace>.
%LOCALAPPDATA%\LingJi\desktop-bootstrap.json stores only the small Desktop bootstrap pointer; it is not the Runtime data root.
Optional media providers and large local models are not bundled or downloaded automatically.
The automatic updater is not included yet.

Installing, upgrading or uninstalling this Desktop package must not intentionally delete the Obsidian Vault,
LingJi storage, runtime settings, SQLite state or Qdrant collections.
"@
$notes | Set-Content -Path (Join-Path $output "INSTALLATION-NOTES.txt") -Encoding UTF8

Write-Host "Windows Desktop + Sidecar release prepared at $output"
Get-ChildItem $output | Select-Object Name, Length | Format-Table -AutoSize
