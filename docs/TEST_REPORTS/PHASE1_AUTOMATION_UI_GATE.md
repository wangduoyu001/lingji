# Phase 1 Automation and UI Gate — Task 6

Status: `IN_PROGRESS / NOT_ACCEPTED`

This is the single authority for Task 6 packaged automation evidence. It is
Acceptance-only evidence from temporary roots; it does not represent an
Artifact, release, live 8766/8767, Production/Vault, or owner acceptance.

## Identity and boundaries

- Base reviewed: Task 6A final review `22aae07be9accf7d56a4273e8d45a521b2323dab`, accepted for Task 6.
- Execution: `tests/integration/test_automatic_memory_packaged_flow.py` launches `run_packaged_control_api.py` in a subprocess and drives the authenticated loopback API.
- Roots: pytest `tmp_path` only; third-party and Vault recursive sentinels record relative path, SHA-256, size, `mtime_ns`, mode, and symlink identity.
- Product wiring note: current scan route returns a reconciliation report without `scan_id`; the test resolves the persisted scan from `/api/automatic-memory/scans` and records this compatibility gap. No product change is included in this evidence commit.

## Scenario matrix

| # | Scenario | Evidence status | Raw counts / timing |
|---:|---|---|---|
| 1 | Fresh metadata discovery without content read | `RED/GREEN pending` | Persisted source rows remain 0 before authorization; raw directory remains empty. |
| 2 | One-time authorization and startup scan | `RED/GREEN pending` | StateDB scans, extraction jobs, structured source/conversation/message rows, and terminal queue state are read from disk. |
| 3 | File event enters queue within 30 seconds | `RED/GREEN pending` | Watcher-triggered scan timing is measured with `monotonic()` and terminal scan identity. |
| 4 | Suppressed event found by accelerated reconciliation | `RED/GREEN pending` | Runtime pause/resume plus explicit reconciliation path; persisted scan report is inspected. |
| 5 | Crash at 30% and 70%, restart to identical terminal counts | `RED/GREEN pending` | Real process kill/restart, durable lease expiry/retry, job counts and terminal status are measured per percentage. |
| 6 | Pause/resume/revoke/authorization expiry | `RED/GREEN pending` | Runtime state and source status are read through authenticated API; expiry is observed from the persisted source registry. |
| 7 | Corrupt source isolated while another source completes | `RED/GREEN pending` | Per-source scan/job terminal statuses are compared from StateDB. |
| 8 | Qdrant unavailable with truthful lexical fallback | `PASS (focused helper)` | Formal HybridRetriever diagnostics report semantic degradation reason and non-empty lexical result. |
| 9 | Sleep/wake equivalent clock jump and process restart | `RED/GREEN pending` | Source mtime jump plus packaged process restart; runtime and reconciliation terminal status are read after restart. |
| 10 | Third-party/Vault non-interference | `RED/GREEN pending` | Recursive pre/post sentinel diff must be empty. |

## Commands

```text
./.venv/bin/python -m pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short
cd desktop/lingji-control && npm run test:e2e:memory
```

The complete Task 6 focused command is registered as
`validate.ps1 -Mode focused -Area automatic-memory-landing`; it includes the
packaged integration test and the existing rendered `e2e_owner_memory_flow.mjs`.

## Limitations and cleanup

No Artifact was installed, no Production/Vault or owner data was accessed, and
no real 8766/8767 port was used. A skipped core scenario is a failure. Final
raw counts, run identities, timings, sentinel diff, regression commands and
cleanup receipts are added only after the two clean-root runs complete.

