param(
  [string]$TargetTriple = "x86_64-pc-windows-msvc",
  [string]$OutputRoot = "build/sidecar"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$entrypoint = Join-Path $repoRoot "run_packaged_control_api.py"
$buildRoot = Join-Path $repoRoot $OutputRoot
$distRoot = Join-Path $buildRoot "dist"
$workRoot = Join-Path $buildRoot "work"
$specRoot = Join-Path $buildRoot "spec"
$tauriBinaries = Join-Path $repoRoot "desktop/lingji-control/src-tauri/binaries"
$preparedExe = Join-Path $tauriBinaries "lingji-core-$TargetTriple.exe"
$preparedRuntime = Join-Path $tauriBinaries "lingji_core_lib"
$pythonExe = if ($env:LINGJI_SIDECAR_PYTHON) {
  $env:LINGJI_SIDECAR_PYTHON
} else {
  "python"
}

foreach ($path in @($buildRoot, $tauriBinaries)) {
  New-Item -ItemType Directory -Path $path -Force | Out-Null
}
foreach ($path in @($distRoot, $workRoot, $specRoot, $preparedRuntime)) {
  if (Test-Path $path) { Remove-Item $path -Recurse -Force }
}
if (Test-Path $preparedExe) { Remove-Item $preparedExe -Force }

$arguments = @(
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onedir",
  "--windowed",
  "--name", "lingji-core",
  "--contents-directory", "lingji_core_lib",
  "--distpath", $distRoot,
  "--workpath", $workRoot,
  "--specpath", $specRoot,
  "--paths", $repoRoot,
  "--collect-submodules", "src",
  "--exclude-module", "PySide6",
  "--exclude-module", "torch",
  "--exclude-module", "tensorflow",
  "--exclude-module", "paddleocr",
  "--exclude-module", "faster_whisper",
  "--exclude-module", "scenedetect",
  $entrypoint
)

Write-Host "Building LingJi runtime sidecar with PyInstaller..."
& $pythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$bundleRoot = Join-Path $distRoot "lingji-core"
$sourceExe = Join-Path $bundleRoot "lingji-core.exe"
$sourceRuntime = Join-Path $bundleRoot "lingji_core_lib"
if (-not (Test-Path $sourceExe)) { throw "Missing PyInstaller executable: $sourceExe" }
if (-not (Test-Path $sourceRuntime)) { throw "Missing PyInstaller runtime directory: $sourceRuntime" }

Copy-Item $sourceExe $preparedExe -Force
Copy-Item $sourceRuntime $preparedRuntime -Recurse -Force

$checkRoot = Join-Path $buildRoot "contract-check"
if (Test-Path $checkRoot) { Remove-Item $checkRoot -Recurse -Force }
New-Item -ItemType Directory -Path $checkRoot -Force | Out-Null
$contractPath = Join-Path $checkRoot "contract.json"
$contractCheck = Start-Process -FilePath $sourceExe -ArgumentList @(
  "--data-root", $checkRoot,
  "--check-config",
  "--check-config-output", $contractPath
) -PassThru -Wait
if ($contractCheck.ExitCode -ne 0) { throw "Packaged sidecar contract check failed" }
if (-not (Test-Path $contractPath)) { throw "Packaged sidecar did not write a contract file" }
$contract = Get-Content $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($contract.mode -ne "packaged_sidecar") { throw "Unexpected packaged runtime mode" }
if ($contract.host -ne "127.0.0.1") { throw "Packaged sidecar is not loopback-only" }
if ($contract.owner_data_outside_install_dir -ne $true) { throw "Owner-data boundary is missing" }

$runtimeFiles = Get-ChildItem $preparedRuntime -Recurse -File
$exeHash = (Get-FileHash $preparedExe -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest = [ordered]@{
  schema_version = 1
  target_triple = $TargetTriple
  executable = [ordered]@{
    path = "binaries/$(Split-Path $preparedExe -Leaf)"
    bytes = (Get-Item $preparedExe).Length
    sha256 = $exeHash
  }
  runtime_directory = [ordered]@{
    path = "binaries/lingji_core_lib"
    file_count = $runtimeFiles.Count
    bytes = ($runtimeFiles | Measure-Object Length -Sum).Sum
  }
  pyinstaller_mode = "onedir"
  contents_directory = "lingji_core_lib"
  optional_media_providers_bundled = $false
  contract = $contract
}
$manifestPath = Join-Path $tauriBinaries "lingji-core-manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content $manifestPath -Encoding UTF8

# Tauri may cache the target-triple-stripped copy in target/release. Remove it
# before bundling so the installer cannot silently reuse an older sidecar.
$staleCandidates = @(
  (Join-Path $repoRoot "desktop/lingji-control/src-tauri/target/release/lingji-core.exe"),
  (Join-Path $repoRoot "desktop/lingji-control/src-tauri/target/$TargetTriple/release/lingji-core.exe")
)
foreach ($candidate in $staleCandidates) {
  if (Test-Path $candidate) { Remove-Item $candidate -Force }
}

Write-Host "Prepared Tauri sidecar: $preparedExe"
Write-Host "Runtime files: $($runtimeFiles.Count)"
Write-Host "Executable SHA-256: $exeHash"
