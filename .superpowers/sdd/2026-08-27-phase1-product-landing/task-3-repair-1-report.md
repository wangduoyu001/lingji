# Phase 1 Product Landing — Task 3 Repair Round 1 Report

Date: 2026-08-27
Branch: `codex/phase1-automatic-memory`
Base review HEAD: `53c4ce0`
Product/test commit: `f2f7312`
Evidence/docs commit: `4e5d744`

## Executive verdict

`IMPLEMENTED_FOCUSED_PASS` for the eight independent Task 3 Important findings, subject to the documented preserved Task 2 scheduler timing failure. This is synthetic/local code verification only; no Artifact, release, live 8766, UI, owner, Production, or real Vault acceptance was performed.

## TDD evidence

Repair tests were added before repair implementation. The exact RED command was:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round1.py --tb=short
8 failed, 1 warning in 1.26s
```

The eight failures mapped to I1 terminal unauthorized jobs, I2 Obsidian reads, I3 sensitive filename filtering, I4 repeated-scan counts, I5 route/runtime dispatch, I6 WorkItem status, I7 stale evidence metadata, and I8 Vault sink mutation. Setup-only corrections to the new test fixture were completed before this behavioral RED record; no existing tests were removed or weakened.

## Repairs

### I1 — terminal invalid internal jobs

Unauthorized, missing, revoked, inactive, and malformed internal snapshot jobs now fail terminally through the existing queue `fail(..., terminal=True)` path and emit the existing lifecycle callback. `process_pending` therefore cannot repeatedly re-lease an invalid job ahead of a valid ordinary extraction job. Existing revoked-job coverage now expects truthful `failed` status and an authorization error.

### I2 — bounded Obsidian reads

Automatic Obsidian enumeration now probes only the opening marker and reads frontmatter line-by-line up to `FRONTMATTER_MAX_BYTES=8192`; it stops at the frontmatter closing delimiter and never consumes note bodies. Managed directories still use the same existing scope semantics, including `lingji_memory: false` precedence. Tests track `Path.open().read/readline()` bytes, body sentinels, managed false, explicit true, and ordinary no-frontmatter notes.

### I3 — sensitive filename variants

Authorized generic roots now apply case-folded, separator-aware stem tokens for credential/auth/token/cookie/private names while retaining safe unrelated names such as `safe-history.json`. Database suffix blocking and symlink/root policy remain unchanged.

### I4 — two-scan idempotency and truthful counts

The existing snapshot admission result now identifies `existing_job`; `SnapshotJobRunner` carries inserted `queued` and reused counts through the existing `ScanRun`/`ReconciliationReport` contract. A real two-scan test proves two terminal scans, one durable extraction row, one source/conversation/message identity set, `queued=1` then `queued=0,reused=1`, and non-zero truthful Work Fact summaries. Per-scan admission reports are released after terminal Work Fact projection.

### I5 — scheduler-backed scan API

Authenticated `/api/automatic-memory/scan` now requires a composed runtime and dispatches `runtime.scan_now(source_id)`. Without runtime it returns `409` without creating a scan; with runtime it returns the real scheduler result and `work_id`. Existing pause/resume/retry routes remain registry/scheduler-owned and authentication-protected.

### I6 — Work Fact identity/status

Scan WorkItems now use the actual automatic-memory `source_id`, retain stable `automatic-memory:{scan_id}` identity, and use the existing `WorkStore.apply_extraction_transition` transaction to update WorkItem status to `retrying`, `completed`, or `failed` alongside projected outcomes. Tests cover completed and failed terminal statuses.

### I7 — evidence metadata

The prior Task 3 report now records evidence/docs commit `0d7bb84` and has no trailing whitespace. This repair report and the current acceptance entry intentionally use `pending` only until the final evidence/docs commit exists; the final metadata update records that exact completed docs SHA without self-reference.

### I8 — no automatic chat Markdown publishing

Internal automatic-memory snapshots no longer call `VaultExtractionSink.write_batch` or `write_document`, and do not invoke the configured `settings.vault_path` document sink. Existing content-addressed raw evidence and StructuredReadModel source/conversation/message rows remain authoritative. Structured sink receives empty Vault results and explicitly marks Vault/index links unavailable. A recursive Vault before/after sentinel plus a raising sink spy proves zero Vault mutation while structured data persists.

## Verification

Repair-focused and directly affected tests after implementation:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py --tb=short
22 passed, 1 warning
```

The full direct matrix (including the preserved Task 2 scheduler timing case) was run without hiding or changing the known failure. The unfiltered result was `209 passed, 1 failed, 7 warnings`; the failure remains `tests/test_automatic_memory_scheduler.py::test_daily_integrity_job_runs_without_event`, caused by the pre-existing `integrity_seconds` minimum-one-second clamp. Excluding only that named preserved edge gives `209 passed, 1 deselected, 7 warnings`. No Task 2 lifecycle/timing code was changed.

Additional gates:

- `./.venv/bin/python -m compileall -q src tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py`: pass.
- `git diff --check` over the repair range: pass after docs cleanup.
- `./.venv/bin/python scripts/check_acceptance_sync.py`: pass.
- `./.venv/bin/python scripts/check_local_execution_handoff.py`: pass; `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## Changed files

Product/test commit `f2f7312`:

- `src/automatic_memory/checkpoint.py`
- `src/automatic_memory/models.py`
- `src/automatic_memory/path_policy.py`
- `src/automatic_memory/runtime.py`
- `src/automatic_memory/scheduler.py`
- `src/control/automatic_memory_api.py`
- `src/extraction/pipeline.py`
- `src/extraction/queue.py`
- `src/obsidian/memory_scope.py`
- `src/work/store.py`
- `tests/test_automatic_memory_control_api.py`
- `tests/test_automatic_memory_repair_round1.py`
- `tests/test_extraction_worker.py`

Evidence/docs commit changes:

- `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-report.md`
- `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-1-report.md`
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/PROJECT_STATUS.md`

## Boundaries and limitations

- No live 8766 service, Artifact/release build, real UI, owner observation, Production/Vault data, cloud, or external software mutation was performed.
- No promotion seam was invoked or enabled: `evaluate`, `promote`, `submit`, `reconcile_incomplete_projections`, and `rebuild_derived_projections` remain forbidden.
- Task 2 stale scheduler cleanup-state/timing edge remains unchanged and is reported separately above; it is not converted to stopped or hidden.
- No new parser, store, queue, API, indexer, config center, UI, retrieval/vector, quality, release, or 100k feature was added.
