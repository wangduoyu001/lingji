[CmdletBinding()]
param(
    [ValidateSet("focused", "full", "release")]
    [string]$Mode = "focused",

    [ValidateSet("retrieval", "capture", "control", "obsidian", "desktop", "sidecar", "docs")]
    [string]$Area = "docs",

    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$script:Results = @()
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

function Get-GitValue {
    param([string[]]$Arguments, [string]$Fallback)

    try {
        $value = (& git @Arguments 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and $value) {
            return $value.Trim()
        }
    }
    catch {
        return $Fallback
    }
    return $Fallback
}

$commit = Get-GitValue -Arguments @("rev-parse", "HEAD") -Fallback "unknown"
$shortCommit = $commit
if ($commit.Length -ge 8) {
    $shortCommit = $commit.Substring(0, 8)
}

$branch = Get-GitValue -Arguments @("rev-parse", "--abbrev-ref", "HEAD") -Fallback "unknown"
if ($env:GITHUB_HEAD_REF) {
    $branch = $env:GITHUB_HEAD_REF
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputRoot = Join-Path $repoRoot ("output\validation\{0}-{1}-{2}" -f $stamp, $shortCommit, $Mode)
$logsRoot = Join-Path $outputRoot "logs"
New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null

function Write-ValidationSummary {
    param([string]$Overall)

    $areaValue = $null
    if ($Mode -eq "focused") {
        $areaValue = $Area
    }

    $summary = [ordered]@{
        commit = $commit
        branch = $branch
        mode = $Mode
        area = $areaValue
        overall = $Overall
        ended_at = (Get-Date).ToString("o")
        suites = @($script:Results)
    }

    $jsonPath = Join-Path $outputRoot "summary.json"
    $markdownPath = Join-Path $outputRoot "summary.md"
    $summary | ConvertTo-Json -Depth 6 | Set-Content -Path $jsonPath -Encoding UTF8

    $lines = @(
        "# LingJi Validation Summary",
        "",
        "- Commit: ``$commit``",
        "- Branch: ``$branch``",
        "- Mode: ``$Mode``"
    )
    if ($Mode -eq "focused") {
        $lines += "- Area: ``$Area``"
    }
    $lines += @(
        "- Overall: ``$Overall``",
        "",
        "| Suite | Result | Seconds | Log |",
        "|---|---:|---:|---|"
    )
    foreach ($result in $script:Results) {
        $relativeLog = $result.log.Replace($repoRoot + "\", "")
        $lines += "| $($result.name) | $($result.status) | $($result.duration_seconds) | ``$relativeLog`` |"
    }
    $lines | Set-Content -Path $markdownPath -Encoding UTF8

    return $jsonPath
}

function Invoke-ValidationStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $safeName = ($Name -replace "[^A-Za-z0-9_.-]", "-").ToLowerInvariant()
    $logPath = Join-Path $logsRoot ($safeName + ".log")
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $exitCode = 1

    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments *> $logPath
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) {
            $exitCode = 0
        }
    }
    catch {
        $_ | Out-String | Add-Content -Path $logPath -Encoding UTF8
        $exitCode = 1
    }
    finally {
        Pop-Location
        $watch.Stop()
    }

    $status = "FAIL"
    if ($exitCode -eq 0) {
        $status = "PASS"
    }

    $script:Results += [pscustomobject][ordered]@{
        name = $Name
        status = $status
        exit_code = $exitCode
        duration_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 2)
        log = $logPath
    }

    if ($exitCode -ne 0) {
        Write-Host ("[FAIL] {0}" -f $Name) -ForegroundColor Red
        if (Test-Path $logPath) {
            Get-Content -Path $logPath -Tail 80
        }
        $summaryPath = Write-ValidationSummary -Overall "FAIL"
        Write-Host ("Failure log: {0}" -f $logPath)
        Write-Host ("Summary: {0}" -f $summaryPath)
        exit $exitCode
    }

    Write-Host ("[PASS] {0} ({1}s)" -f $Name, [Math]::Round($watch.Elapsed.TotalSeconds, 2))
}

function Invoke-PythonFocused {
    param([string]$Expression)

    Invoke-ValidationStep `
        -Name ("python-{0}" -f $Area) `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("-m", "pytest", "-q", "--tb=short", "-k", $Expression)
}

function Invoke-DesktopScript {
    param([string]$Name, [string]$ScriptName)

    Invoke-ValidationStep `
        -Name $Name `
        -WorkingDirectory (Join-Path $repoRoot "desktop\lingji-control") `
        -Command "npm" `
        -Arguments @("run", $ScriptName)
}

function Invoke-FocusedValidation {
    switch ($Area) {
        "retrieval" {
            Invoke-PythonFocused "qdrant or retrieval or embedding or memory_gateway or memory_statistics"
        }
        "capture" {
            Invoke-PythonFocused "capture or extraction or idempotency"
            Invoke-DesktopScript "desktop-capture" "test:capture"
        }
        "control" {
            Invoke-PythonFocused "control or settings_governance or runtime_truth"
        }
        "obsidian" {
            Invoke-PythonFocused "obsidian"
            Invoke-DesktopScript "desktop-obsidian" "test:obsidian"
            Invoke-DesktopScript "desktop-obsidian-operations" "test:obsidian-operations"
        }
        "desktop" {
            Invoke-DesktopScript "desktop-smoke" "test:smoke"
            Invoke-DesktopScript "desktop-build" "build"
        }
        "sidecar" {
            Invoke-PythonFocused "packaged or sidecar or runtime_manager"
            Invoke-DesktopScript "desktop-runtime" "test:runtime"
            Invoke-ValidationStep `
                -Name "tauri-runtime-tests" `
                -WorkingDirectory (Join-Path $repoRoot "desktop\lingji-control") `
                -Command "cargo" `
                -Arguments @("test", "--manifest-path", "src-tauri/Cargo.toml", "--target", "x86_64-pc-windows-msvc")
        }
        "docs" {
            Invoke-ValidationStep `
                -Name "git-diff-check" `
                -WorkingDirectory $repoRoot `
                -Command "git" `
                -Arguments @("diff", "--check")
        }
    }
}

function Invoke-FullValidation {
    Invoke-ValidationStep `
        -Name "python-full" `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("-m", "pytest", "-q", "--tb=short")

    Invoke-ValidationStep `
        -Name "python-compileall" `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("-m", "compileall", "-q", "main.py", "run_service.py", "run_control_api.py", "run_packaged_control_api.py", "run_mcp_server.py", "run_extraction_worker.py", "src", "second_brain", "tests", "scripts")

    Invoke-DesktopScript "desktop-smoke" "test:smoke"
    Invoke-DesktopScript "desktop-build" "build"

    Invoke-ValidationStep `
        -Name "tauri-rust-tests" `
        -WorkingDirectory (Join-Path $repoRoot "desktop\lingji-control") `
        -Command "cargo" `
        -Arguments @("test", "--manifest-path", "src-tauri/Cargo.toml", "--target", "x86_64-pc-windows-msvc")

    Invoke-ValidationStep `
        -Name "obsidian-plugin-check" `
        -WorkingDirectory $repoRoot `
        -Command "node" `
        -Arguments @("--check", "obsidian-plugin/lingji-control/main.js")
}

$scopeText = ""
if ($Mode -eq "focused") {
    $scopeText = ", area=$Area"
}
Write-Host ("LingJi validation: mode={0}{1}" -f $Mode, $scopeText)

if ($Mode -eq "focused") {
    Invoke-FocusedValidation
}
else {
    Invoke-FullValidation
    if ($Mode -eq "release") {
        Invoke-DesktopScript "windows-release" "release:windows"
    }
}

$finalSummary = Write-ValidationSummary -Overall "PASS"
Write-Host ("Validation PASS. Summary: {0}" -f $finalSummary) -ForegroundColor Green
