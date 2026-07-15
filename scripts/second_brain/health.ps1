$ErrorActionPreference = "Stop"
try {
    $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 5
    $Status = Invoke-RestMethod -Uri "http://127.0.0.1:8765/memory/status" -TimeoutSec 10
    [pscustomobject]@{ Health=$Health.status; Port=8765; QdrantReady=$Health.qdrant.ready; Counts=($Status.counts | ConvertTo-Json -Compress) }
} catch {
    Write-Error "LingJi second brain is unavailable: $($_.Exception.Message)"
}
