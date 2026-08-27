[CmdletBinding()]
param(
    [ValidateSet("focused", "full", "release")]
    [string]$Mode = "focused",

    [ValidateSet("retrieval", "capture", "control", "obsidian", "desktop", "sidecar", "docs", "validation", "automatic-memory-quality")]
    [string]$Area = "docs",

    [string]$PythonCommand = "python",

    [ValidateRange(10, 200)]
    [int]$FailureTailLines = 40
)

$ErrorActionPreference = "Stop"
$script:Results = @()
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktopRoot = Join-Path $repoRoot "desktop\lingji-control"
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
$validationRoot = Join-Path $repoRoot "output\validation"
$outputRoot = Join-Path $validationRoot ("{0}-{1}-{2}" -f $stamp, $shortCommit, $Mode)
$logsRoot = Join-Path $outputRoot "logs"
New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null

function Remove-StaleValidationRuns {
    if (-not (Test-Path $validationRoot)) {
        return
    }

    Get-ChildItem -Path $validationRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -ne $outputRoot } |
        ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
}

Remove-StaleValidationRuns

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
        log_policy = "Read summary only on success; read only the failing log tail on failure."
        suites = @($script:Results)
    }

    $jsonPath = Join-Path $outputRoot "summary.json"
    $markdownPath = Join-Path $outputRoot "summary.md"
    $latestJsonPath = Join-Path $validationRoot "latest-summary.json"
    $latestMarkdownPath = Join-Path $validationRoot "latest-summary.md"
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
        "- Log policy: success reads this summary only; failure reads only the failing log tail.",
        "",
        "| Suite | Result | Seconds | Log |",
        "|---|---:|---:|---|"
    )
    foreach ($result in $script:Results) {
        $relativeLog = $result.log.Replace($repoRoot + "\", "")
        $lines += "| $($result.name) | $($result.status) | $($result.duration_seconds) | ``$relativeLog`` |"
    }
    $lines | Set-Content -Path $markdownPath -Encoding UTF8

    Copy-Item -Path $jsonPath -Destination $latestJsonPath -Force
    Copy-Item -Path $markdownPath -Destination $latestMarkdownPath -Force

    return $latestJsonPath
}

function Invoke-ValidationStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [hashtable]$Environment = @{}
    )

    $safeName = ($Name -replace "[^A-Za-z0-9_.-]", "-").ToLowerInvariant()
    $logPath = Join-Path $logsRoot ($safeName + ".log")
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $exitCode = 1
    $previousEnvironment = @{}
    $previousErrorActionPreference = $ErrorActionPreference

    foreach ($key in $Environment.Keys) {
        $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
        [Environment]::SetEnvironmentVariable($key, [string]$Environment[$key], "Process")
    }

    Push-Location $WorkingDirectory
    try {
        $null = Get-Command $Command -ErrorAction Stop

        # Windows PowerShell 5.1 promotes native stderr to its Error stream. Some
        # successful tools, notably Vite, legitimately write warnings there. Keep
        # stderr in the log and determine success exclusively from the native exit
        # code instead of treating warning text as a terminating PowerShell error.
        $ErrorActionPreference = "Continue"
        $global:LASTEXITCODE = 0
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
        $ErrorActionPreference = $previousErrorActionPreference
        Pop-Location
        foreach ($key in $Environment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], "Process")
        }
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
            Get-Content -Path $logPath -Tail $FailureTailLines
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
        -WorkingDirectory $desktopRoot `
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
                -WorkingDirectory $desktopRoot `
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
        "validation" {
            Invoke-ValidationStep `
                -Name "native-stderr-warning-contract" `
                -WorkingDirectory $repoRoot `
                -Command "powershell" `
                -Arguments @(
                    "-NoProfile",
                    "-Command",
                    "[Console]::Error.WriteLine('expected validation warning'); exit 0"
                )
        }
        "automatic-memory-quality" {
            Invoke-ValidationStep `
                -Name "automatic-memory-quality-gate" `
                -WorkingDirectory $repoRoot `
                -Command $PythonCommand `
                -Arguments @("scripts/automatic_memory_quality_gate.py")
        }
    }
}

function Invoke-FullValidation {
    Invoke-ValidationStep `
        -Name "git-diff-check" `
        -WorkingDirectory $repoRoot `
        -Command "git" `
        -Arguments @("diff", "--check")

    Invoke-ValidationStep `
        -Name "clean-install-contracts" `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("scripts/validate_clean_install.py", "--root", ".", "--import-check")

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
        -WorkingDirectory $desktopRoot `
        -Command "cargo" `
        -Arguments @("test", "--manifest-path", "src-tauri/Cargo.toml", "--target", "x86_64-pc-windows-msvc")

    Invoke-ValidationStep `
        -Name "obsidian-plugin-check" `
        -WorkingDirectory $repoRoot `
        -Command "node" `
        -Arguments @("--check", "obsidian-plugin/lingji-control/main.js")

    foreach ($scriptPath in @(
        "browser-extension/lingji-capture/background.js",
        "browser-extension/lingji-capture/popup.js",
        "browser-extension/lingji-capture/options.js"
    )) {
        $scriptName = [IO.Path]::GetFileNameWithoutExtension($scriptPath)
        Invoke-ValidationStep `
            -Name ("browser-{0}-check" -f $scriptName) `
            -WorkingDirectory $repoRoot `
            -Command "node" `
            -Arguments @("--check", $scriptPath)
    }

    Invoke-ValidationStep `
        -Name "browser-manifest-check" `
        -WorkingDirectory $repoRoot `
        -Command "node" `
        -Arguments @("-e", "const m=require('./browser-extension/lingji-capture/manifest.json'); if(m.manifest_version!==3||!m.background||!m.options_page) process.exit(1)")

    $mcpRuntimeRoot = Join-Path $outputRoot "mcp-runtime"
    Invoke-ValidationStep `
        -Name "mcp-server-create" `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("-c", "from src.mcp_server import create_mcp_server; assert create_mcp_server(default_agent_id='lingji-local') is not None") `
        -Environment @{
            VAULT_DIR = (Join-Path $mcpRuntimeRoot "vault")
            STORAGE_DIR = (Join-Path $mcpRuntimeRoot "storage")
            WATCHDOG_ENABLED = "false"
        }
}

function Invoke-ReleaseValidation {
    # Task 4R2 owns MCP/Qdrant degradation, corruption isolation, measured
    # context baseline and scale readiness. The executable preflight must fail
    # before a scale command or its opt-in environment is constructed.
    Invoke-ValidationStep `
        -Name "automatic-memory-4r2-readiness" `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("scripts/automatic_memory_quality_gate.py", "--check-4r2")
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
        Invoke-ReleaseValidation
    }
}

$finalSummary = Write-ValidationSummary -Overall "PASS"
Write-Host ("Validation PASS. Summary: {0}" -f $finalSummary) -ForegroundColor Green
