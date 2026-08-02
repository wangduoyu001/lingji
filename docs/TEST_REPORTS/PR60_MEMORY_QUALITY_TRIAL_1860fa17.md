# PR #60 Memory Quality Trial — 1860fa17 Day 0 Failure Report

## Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 1860fa17c5de26b0ff4d54ace48158a6e343505a
Artifact: lingji-windows-0.1.0-1860fa17 (ID 8830371064)
Failure: D0-AUTO-IMPORT-QUEUE-STALLED
```

The fixed Artifact passed identity verification, isolated installation, startup
binding, and metadata-only discovery. It fails the Day 0 automatic-import
requirement: after one authorized synthetic ChatGPT export, the durable job
remained `queued` for 40 seconds with `attempts = 0`. No background worker
processed the job. A queued job is not an import success.

## Safe evidence

| Check | Result |
|---|---|
| Artifact ZIP and published component hashes | PASS |
| Isolated D-drive installation and Sidecar hash | PASS |
| First startup | PASS, 16.5 seconds |
| Runtime ping | PASS: acceptance workspace and contract version 1 |
| Metadata-only candidate scan | PASS: exactly two synthetic candidates; no paths exposed |
| One-action authorization | PASS: one authorization created job `LJ-JOB-A0D24984A012` |
| Automatic queue processing | **FAIL**: `queued` for 40 seconds, 0 attempts |
| Real data | NOT_READ |
| Stage 1 / Stage 2 | NOT_RUN |

The synthetic content, runtime tokens, private logs, databases, and absolute
owner paths are deliberately excluded from this report.

## Required repair

The packaged runtime must start and own the extraction worker against its
durable queue. The replacement Artifact must be rebuilt from the repair and
must repeat Day 0 from a clean isolated task root; it cannot inherit this
Artifact's result.

## Scope stopped by the P0 gate

Per the active task, no Codex client configuration, real MCP content call,
candidate approval/rejection, Windows reboot, real-data authorization, Stage 1,
or Stage 2 was attempted after this failure.
