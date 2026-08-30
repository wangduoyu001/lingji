[CmdletBinding()]
param(
    [ValidateSet("focused", "full", "release")]
    [string]$Mode = "focused",

    [ValidateSet("retrieval", "capture", "control", "obsidian", "desktop", "sidecar", "docs", "validation", "automatic-memory-quality", "automatic-memory-landing")]
    [string]$Area = "docs",

    [string]$PythonCommand = "python",

    [ValidateRange(10, 200)]
    [int]$FailureTailLines = 40,

    # This switch is intentionally inert unless the CI/test launcher also
    # supplies the private opt-in environment marker. It exists only to
    # exercise the release dispatch boundary without repeating full validation.
    [switch]$TestReleaseEntryOnly
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

function Normalize-ValidationPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        $fullPath = [IO.Path]::GetFullPath($Path)
        $pathRoot = [IO.Path]::GetPathRoot($fullPath)
        if ([string]::IsNullOrWhiteSpace($pathRoot)) {
            throw "path root is empty"
        }
        while ($fullPath.Length -gt $pathRoot.Length -and ($fullPath.EndsWith("\") -or $fullPath.EndsWith("/"))) {
            $fullPath = $fullPath.Substring(0, $fullPath.Length - 1)
        }
        return $fullPath
    }
    catch {
        throw "validation path is not valid"
    }
}

function Test-ValidationPathEqual {
    param(
        [Parameter(Mandatory = $true)][string]$Left,
        [Parameter(Mandatory = $true)][string]$Right
    )

    $leftPath = Normalize-ValidationPath -Path $Left
    $rightPath = Normalize-ValidationPath -Path $Right
    $comparison = [StringComparison]::Ordinal
    if ([IO.Path]::DirectorySeparatorChar -eq "\") {
        $comparison = [StringComparison]::OrdinalIgnoreCase
    }
    return [String]::Equals($leftPath, $rightPath, $comparison)
}

function Assert-ValidationRoot {
    param([Parameter(Mandatory = $true)][string]$RootPath)

    $cursor = Normalize-ValidationPath -Path $RootPath
    while ($true) {
        if (Test-Path -LiteralPath $cursor) {
            try {
                $item = Get-Item -LiteralPath $cursor -Force -ErrorAction Stop
                if (-not $item.PSIsContainer) {
                    throw "validation root is not a directory"
                }
                if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw "VALIDATION_OUTPUT_ROOT_REPARSE"
                }
            }
            catch {
                throw "VALIDATION_OUTPUT_ROOT_REPARSE"
            }
        }

        $parent = Split-Path -Parent $cursor
        if ([string]::IsNullOrWhiteSpace($parent)) {
            break
        }
        $parent = Normalize-ValidationPath -Path $parent
        if (Test-ValidationPathEqual -Left $parent -Right $cursor) {
            break
        }
        $cursor = $parent
    }
}

function Assert-ValidationRegularDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if (-not $item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw "validation directory is not regular"
        }
    }
    catch {
        throw "VALIDATION_OUTPUT_DIRECTORY_REPARSE"
    }
}

function Assert-ValidationRegularFileDestination {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ParentPath
    )

    $canonicalPath = Normalize-ValidationPath -Path $Path
    $canonicalParent = Normalize-ValidationPath -Path (Split-Path -Parent $canonicalPath)
    if (-not (Test-ValidationPathEqual -Left $canonicalParent -Right $ParentPath)) {
        throw "VALIDATION_OUTPUT_PATH_OUTSIDE_ROOT"
    }
    if (Test-Path -LiteralPath $canonicalPath) {
        try {
            $item = Get-Item -LiteralPath $canonicalPath -Force -ErrorAction Stop
            if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
                throw "validation destination is not a regular file"
            }
        }
        catch {
            throw "VALIDATION_OUTPUT_DESTINATION_REPARSE"
        }
    }
}

$configuredValidationRoot = [Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_OUTPUT_ROOT", "Process")
if ([string]::IsNullOrWhiteSpace($configuredValidationRoot)) {
    $validationRoot = Join-Path $repoRoot "output\validation"
}
else {
    $validationRoot = Normalize-ValidationPath -Path $configuredValidationRoot
}
Assert-ValidationRoot -RootPath $validationRoot

$testClock = [Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_TEST_CLOCK", "Process")
if ($testClock -match "^\d{8}-\d{6}$") {
    $stamp = $testClock
}
else {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
}

# The GUID is the ownership boundary. The timestamp remains useful to humans,
# but never determines identity or cleanup ownership by itself.
$invocationId = [Guid]::NewGuid().ToString("N")
$outputHint = [Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_OUTPUT_HINT", "Process")
$hintPrefix = ""
if ($outputHint -match "^[A-Za-z0-9_.-]{1,64}$") {
    $hintPrefix = "{0}-" -f $outputHint
}
$outputRoot = Normalize-ValidationPath -Path (Join-Path $validationRoot ("{0}{1}-{2}-{3}-{4}" -f $hintPrefix, $stamp, $invocationId, $shortCommit, $Mode))
$logsRoot = Join-Path $outputRoot "logs"

if (-not (Test-Path -LiteralPath $validationRoot)) {
    New-Item -ItemType Directory -Path $validationRoot -ErrorAction Stop | Out-Null
}
Assert-ValidationRoot -RootPath $validationRoot

$ownerMarkerPath = Join-Path $outputRoot ".owner.json"
$invocationStartedAt = (Get-Date).ToUniversalTime().ToString("o")
$processStartedAt = $null
try {
    $processStartedAt = (Get-Process -Id $PID -ErrorAction Stop).StartTime.ToUniversalTime().ToString("o")
}
catch {
    # A missing process start time is safe: a completed marker with no proof of
    # process identity will be retained by stale cleanup.
}

function Write-ValidationOwnerMarker {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("running", "completed", "failed")][string]$State
    )

    $marker = [ordered]@{
        schema_version = 1
        invocation_id = $invocationId
        process_id = [int]$PID
        process_started_at = $processStartedAt
        state = $State
        started_at = $invocationStartedAt
    }
    if ($State -ne "running") {
        $marker.ended_at = (Get-Date).ToUniversalTime().ToString("o")
    }

    Assert-ValidationRegularDirectory -Path $outputRoot
    $json = $marker | ConvertTo-Json -Compress
    if ($json.Length -gt 4096) {
        throw "validation owner marker exceeded bounded size"
    }
    Assert-ValidationRegularFileDestination -Path $ownerMarkerPath -ParentPath $outputRoot
    Set-Content -LiteralPath $ownerMarkerPath -Value $json -Encoding UTF8
}

function Test-ValidationJsonInteger {
    param([Parameter(Mandatory = $false)]$Value)

    if ($null -eq $Value) {
        return $false
    }
    $typeName = $Value.GetType().FullName
    return @(
        "System.Byte",
        "System.SByte",
        "System.Int16",
        "System.UInt16",
        "System.Int32",
        "System.UInt32",
        "System.Int64",
        "System.UInt64"
    ) -contains $typeName
}

function Test-ValidationJsonTimestamp {
    param([Parameter(Mandatory = $false)]$Value)

    if ($null -eq $Value) {
        return $false
    }
    return @("System.String", "System.DateTime", "System.DateTimeOffset") -contains $Value.GetType().FullName
}

function Read-ValidationOwnerMarker {
    param([Parameter(Mandatory = $true)][string]$DirectoryPath)

    try {
        Assert-ValidationRegularDirectory -Path $DirectoryPath
    }
    catch {
        return $null
    }
    $markerPath = Join-Path $DirectoryPath ".owner.json"
    try {
        $markerItem = Get-Item -LiteralPath $markerPath -Force -ErrorAction Stop
        if (-not $markerItem.PSIsContainer -and (($markerItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)) {
            # continue
        }
        else {
            return $null
        }
        $raw = Get-Content -LiteralPath $markerPath -Raw -ErrorAction Stop
        if ($raw.Length -gt 4096) {
            return $null
        }
        $marker = $raw | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $marker -or $marker -is [Array]) {
            return $null
        }
        $propertyNames = @($marker.PSObject.Properties | ForEach-Object { $_.Name })
        $state = [string]$marker.state
        if ($state -notin @("running", "completed", "failed")) {
            return $null
        }
        $requiredNames = @("schema_version", "invocation_id", "process_id", "process_started_at", "state", "started_at")
        if ($state -ne "running") {
            $requiredNames += "ended_at"
        }
        if ($propertyNames.Count -ne $requiredNames.Count) {
            return $null
        }
        foreach ($name in $requiredNames) {
            if ($propertyNames -notcontains $name -or $null -eq $marker.$name) {
                return $null
            }
        }
        if (-not (Test-ValidationJsonInteger -Value $marker.schema_version) -or [int64]$marker.schema_version -ne 1) {
            return $null
        }
        if (-not ($marker.state -is [string]) -or -not ($marker.invocation_id -is [string]) -or
            -not (Test-ValidationJsonTimestamp -Value $marker.process_started_at) -or
            -not (Test-ValidationJsonTimestamp -Value $marker.started_at)) {
            return $null
        }
        if ($state -ne "running" -and -not (Test-ValidationJsonTimestamp -Value $marker.ended_at)) {
            return $null
        }
        if ($marker.invocation_id -notmatch "^[0-9a-f]{32}$") {
            return $null
        }
        $directoryName = Split-Path -Leaf (Normalize-ValidationPath -Path $DirectoryPath)
        if ($directoryName -notmatch ("(^|-)" + [Regex]::Escape([string]$marker.invocation_id) + "(-|$)")) {
            return $null
        }
        $processId = 0
        if (-not (Test-ValidationJsonInteger -Value $marker.process_id) -or
            -not [int]::TryParse([string]$marker.process_id, [ref]$processId) -or $processId -le 0) {
            return $null
        }
        foreach ($timestamp in @("process_started_at", "started_at")) {
            $parsed = [DateTimeOffset]::MinValue
            if (-not [DateTimeOffset]::TryParse([string]$marker.$timestamp, $null, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$parsed)) {
                return $null
            }
        }
        if ($state -ne "running") {
            $ended = [DateTimeOffset]::MinValue
            if (-not [DateTimeOffset]::TryParse([string]$marker.ended_at, $null, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$ended)) {
                return $null
            }
        }
        return $marker
    }
    catch {
        return $null
    }
}

function Test-ValidationMarkerActive {
    param([Parameter(Mandatory = $true)]$Marker)

    # Unknown, running, malformed, or non-terminal markers are retained. This
    # is deliberately fail-closed so a nested validation cannot delete a live
    # parent whose marker is being written or is otherwise unreadable.
    if ($null -eq $Marker -or $Marker.state -ne "completed") {
        return $true
    }

    $processId = 0
    if (-not [int]::TryParse([string]$Marker.process_id, [ref]$processId) -or $processId -le 0) {
        return $true
    }
    $markerStart = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse(
            [string]$Marker.process_started_at,
            $null,
            [Globalization.DateTimeStyles]::RoundtripKind,
            [ref]$markerStart)) {
        return $true
    }

    try {
        $process = Get-Process -Id $processId -ErrorAction Stop
        if ($null -eq $process) {
            return $true
        }
        $processStart = [DateTimeOffset]::new($process.StartTime.ToUniversalTime())
        if ([Math]::Abs(($processStart - $markerStart.ToUniversalTime()).TotalSeconds) -ge 1) {
            # A reused PID is not this owner; protect it because it is not
            # proven inactive.
            return $true
        }
        # The recorded owner is still running. Keep it protected until an
        # explicit process-not-found result proves it inactive.
        return $true
    }
    catch {
        if ($_.FullyQualifiedErrorId -like "NoProcessFoundForGivenId*") {
            return $false
        }
        return $true
    }
}

function Remove-StaleValidationRuns {
    if (-not (Test-Path -LiteralPath $validationRoot)) {
        return
    }

    $rootPath = Normalize-ValidationPath -Path $validationRoot
    Get-ChildItem -LiteralPath $rootPath -Directory -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            $entry = $_
            try {
                $entryPath = Normalize-ValidationPath -Path $entry.FullName
                if (-not (Test-ValidationPathEqual -Left (Split-Path -Parent $entryPath) -Right $rootPath)) {
                    return
                }
                if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    return
                }

                $marker = Read-ValidationOwnerMarker -DirectoryPath $entryPath
                if (Test-ValidationMarkerActive -Marker $marker) {
                    return
                }

                $endedAt = [DateTimeOffset]::MinValue
                if (-not [DateTimeOffset]::TryParse(
                        [string]$marker.ended_at,
                        $null,
                        [Globalization.DateTimeStyles]::RoundtripKind,
                        [ref]$endedAt)) {
                    return
                }
                if (([DateTimeOffset]::UtcNow - $endedAt.ToUniversalTime()).TotalHours -lt 24) {
                    return
                }

                # Re-read both path and marker immediately before deletion. If
                # an entry was replaced between inspection and removal, retain it.
                $recheckItem = Get-Item -LiteralPath $entryPath -Force -ErrorAction Stop
                if (-not $recheckItem.PSIsContainer -or (($recheckItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
                    return
                }
                $recheckMarker = Read-ValidationOwnerMarker -DirectoryPath $entryPath
                if ($null -eq $recheckMarker -or $recheckMarker.invocation_id -ne $marker.invocation_id) {
                    return
                }
                if (Test-ValidationMarkerActive -Marker $recheckMarker) {
                    return
                }
                Remove-Item -LiteralPath $entryPath -Recurse -Force -ErrorAction Stop
            }
            catch {
                # Unresolved, foreign, or partially-written entries are not
                # proven stale and must remain available for diagnosis.
            }
        }
}

Remove-StaleValidationRuns
if (-not (Test-Path -LiteralPath $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -ErrorAction Stop | Out-Null
}
Assert-ValidationRegularDirectory -Path $outputRoot
if (-not (Test-Path -LiteralPath $logsRoot)) {
    New-Item -ItemType Directory -Path $logsRoot -ErrorAction Stop | Out-Null
}
Assert-ValidationRegularDirectory -Path $logsRoot
Write-ValidationOwnerMarker -State "running"

$testBarrier = [Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_TEST_BARRIER", "Process")
if ($testBarrier -eq "1") {
    Write-Output "LINGJI_VALIDATE_TEST_BARRIER_ENTERED"
    [Console]::ReadLine() | Out-Null
}

function Write-ValidationSummary {
    param([string]$Overall)

    Assert-ValidationRegularDirectory -Path $outputRoot
    Assert-ValidationRegularDirectory -Path $logsRoot

    $areaValue = $null
    if ($Mode -eq "focused") {
        $areaValue = $Area
    }

    $summary = [ordered]@{
        commit = $commit
        branch = $branch
        invocation_id = $invocationId
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
    Assert-ValidationRegularFileDestination -Path $jsonPath -ParentPath $outputRoot
    Assert-ValidationRegularFileDestination -Path $markdownPath -ParentPath $outputRoot
    $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

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
    $lines | Set-Content -LiteralPath $markdownPath -Encoding UTF8

    Publish-ValidationLatestPointer -SourcePath $jsonPath -DestinationPath $latestJsonPath -Suffix "json"
    Publish-ValidationLatestPointer -SourcePath $markdownPath -DestinationPath $latestMarkdownPath -Suffix "md"
    if ($Overall -eq "PASS") {
        Write-ValidationOwnerMarker -State "completed"
    }
    else {
        Write-ValidationOwnerMarker -State "failed"
    }

    return $latestJsonPath
}

function Publish-ValidationLatestPointer {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath,
        [Parameter(Mandatory = $true)][string]$Suffix
    )

    Assert-ValidationRegularDirectory -Path $validationRoot
    Assert-ValidationRegularFileDestination -Path $DestinationPath -ParentPath $validationRoot
    $temporaryPath = Join-Path $validationRoot (".latest-summary-{0}-{1}.tmp" -f $invocationId, $Suffix)
    try {
        Assert-ValidationRegularFileDestination -Path $temporaryPath -ParentPath $validationRoot
        Copy-Item -LiteralPath $SourcePath -Destination $temporaryPath -Force
        Assert-ValidationRegularFileDestination -Path $DestinationPath -ParentPath $validationRoot
        Move-Item -LiteralPath $temporaryPath -Destination $DestinationPath -Force
        Assert-ValidationRegularFileDestination -Path $DestinationPath -ParentPath $validationRoot
    }
    finally {
        if (Test-Path -LiteralPath $temporaryPath) {
            try {
                Assert-ValidationRegularFileDestination -Path $temporaryPath -ParentPath $validationRoot
                Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction Stop
            }
            catch {
                # Preserve a suspicious temporary path rather than following it.
            }
        }
    }
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
    $logIsSafe = $false

    foreach ($key in $Environment.Keys) {
        $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
        [Environment]::SetEnvironmentVariable($key, [string]$Environment[$key], "Process")
    }

    Push-Location $WorkingDirectory
    try {
        Assert-ValidationRegularDirectory -Path $outputRoot
        Assert-ValidationRegularDirectory -Path $logsRoot
        Assert-ValidationRegularFileDestination -Path $logPath -ParentPath $logsRoot
        $logIsSafe = $true
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
        if ($logIsSafe) {
            try {
                Assert-ValidationRegularDirectory -Path $outputRoot
                Assert-ValidationRegularDirectory -Path $logsRoot
                Assert-ValidationRegularFileDestination -Path $logPath -ParentPath $logsRoot
                $_ | Out-String | Add-Content -LiteralPath $logPath -Encoding UTF8
            }
            catch {
                Write-Host ("Validation evidence path rejected: {0}" -f $_.Exception.Message)
            }
        }
        else {
            Write-Host ("Validation evidence path rejected: {0}" -f $_.Exception.Message)
        }
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
        "automatic-memory-landing" {
            Invoke-ValidationStep `
                -Name "automatic-memory-packaged-flow" `
                -WorkingDirectory $repoRoot `
                -Command $PythonCommand `
                -Arguments @("-m", "pytest", "-q", "tests/integration/test_automatic_memory_packaged_flow.py", "--tb=short")
            Invoke-DesktopScript "desktop-rendered-owner-memory" "test:e2e:memory"
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
    function Write-ReleaseTestHook {
        param([Parameter(Mandatory = $true)][string]$Event)

        # Test-only instrumentation. Production/release behavior is unchanged
        # when this opt-in path is absent. The current quarantine exits during
        # preflight, so the scale events must remain at zero.
        $hookPath = [Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_TEST_HOOK", "Process")
        if (-not [string]::IsNullOrWhiteSpace($hookPath)) {
            Add-Content -Path $hookPath -Value $Event -Encoding UTF8
        }
    }

    Write-ReleaseTestHook -Event "preflight"
    # Task 4R2 owns MCP/Qdrant degradation, corruption isolation, measured
    # context baseline and scale readiness. The executable preflight must fail
    # before a scale command or its opt-in environment is constructed.
    Invoke-ValidationStep `
        -Name "automatic-memory-4r2-readiness" `
        -WorkingDirectory $repoRoot `
        -Command $PythonCommand `
        -Arguments @("scripts/automatic_memory_quality_gate.py", "--check-4r2")

    # These markers intentionally remain unreachable while the readiness
    # preflight is blocked. Task 4R2 may add the real scale construction and
    # invocation beneath this boundary without changing the test contract.
    Write-ReleaseTestHook -Event "scale-env"
    Write-ReleaseTestHook -Event "scale-command"
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
    $entryOnly = $TestReleaseEntryOnly -and
        ([Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_TEST_ENTRY_ONLY", "Process") -eq "1") -and
        -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("LINGJI_VALIDATE_TEST_HOOK", "Process"))
    if (-not $entryOnly) {
        Invoke-FullValidation
    }
    if ($Mode -eq "release") {
        Invoke-ReleaseValidation
    }
}

$finalSummary = Write-ValidationSummary -Overall "PASS"
Write-Host ("Validation PASS. Summary: {0}" -f $finalSummary) -ForegroundColor Green
