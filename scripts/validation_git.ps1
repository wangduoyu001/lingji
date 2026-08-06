function Get-GitValue {
    param([string[]]$Arguments, [string]$Fallback)

    try {
        $output = @(& git @Arguments 2>$null)
        $exitCode = $LASTEXITCODE
        $value = $output | Select-Object -First 1
        if ($exitCode -eq 0 -and $value) {
            return $value.Trim()
        }
    }
    catch {
        return $Fallback
    }
    return $Fallback
}
