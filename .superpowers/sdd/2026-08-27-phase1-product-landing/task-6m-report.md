# Task 6M — Automatic-memory transient lifecycle

Date: 2026-08-28  
Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
Baseline: `8cc4d4aabce5a09e7db3754ed9197e33e0b5bf2a`  
Product/test commit: `1901628eee197e3d71d7e070c41c9e586d5468de`

## Scope and disposition

This bounded task closes the Task 6C Repair Round 1 defect in which
`_execute_internal_snapshot` left `.automatic-memory-*.json/jsonl/md` adapter
dispatch hard links after a real process crash. It does not change Task 6's
packaged harness, UI, retrieval, quality gate, promotion, discovery or API
surface. Task 6 remains `IN_PROGRESS / NOT_ACCEPTED`.

The marker now uses `.automatic-memory-v1-{job_id}.{lease_token}{suffix}` with
bounded safe segments; unknown/future marker versions fail closed. The existing extraction queue is the only ownership
authority. Reconciliation is limited to direct children of the configured raw
root and regular files. Terminal, released, expired, or provably dead local
worker leases may be removed; active matching leases and all unknown,
malformed, foreign, mismatched, symlink and directory entries are preserved.
Durable content-addressed raw is never removed. Cleanup receipts are returned
through existing pipeline process results, worker status/stop outcomes and runtime
`cleanup_error/cleanup_pending`;
unlink failures remain visible and are retryable.

## TDD evidence

### RED

Before the production transient boundary existed, importing the new behavior
test failed during collection with:

```text
ModuleNotFoundError: No module named 'src.extraction.transient'
```

This was the expected missing-production-boundary failure. The test file was
then kept as the behavioral contract.

### GREEN

```text
./.venv/bin/python -m pytest -q tests/test_task6m_transient_lifecycle.py --tb=short
8 passed in 0.96s
```

The eight cases cover bounded job/lease naming, terminal and idempotent
cleanup, active/expired leases, malformed/unknown/symlink/directory safety,
unlink `PermissionError` visibility and retry, two-worker isolation, formal
pipeline adapter dispatch, and a real subprocess SIGKILL followed by restart
pipeline reconciliation. The crash case observes a marker created by the
formal `_execute_internal_snapshot` path; it does not hand-write a marker as
its primary proof. The durable raw object's existence and SHA-256 are checked
after reconciliation.

## Regression and static verification

```text
./.venv/bin/python -m pytest -q \
  tests/test_task6m_transient_lifecycle.py \
  tests/test_automatic_memory_resume.py \
  tests/test_automatic_memory_adapters.py \
  tests/test_extraction_worker.py \
  tests/test_automatic_memory_runtime.py \
  tests/test_automatic_memory_scheduler.py --tb=short
150 passed, 3 warnings (runtime cleanup receipt assertion included)

./.venv/bin/python -m compileall -q src tests/test_task6m_transient_lifecycle.py
PASS

git diff --check
PASS
```

The warnings are existing Starlette/httpx deprecation and Pydantic/duplicate
fixture warnings. No assertions were removed, skipped or weakened.

Acceptance sync and local handoff checks are required after this documentation
commit. `LOCAL_EXECUTION_TASK.md` remains `IDLE`; this task does not authorize
live 8766/8767, Artifact/release, Desktop, Production/Vault or owner-data
execution.

## Isolation, cleanup and rollback

All tests used pytest temporary roots. The real-crash test used only a
subprocess and temporary StateDB/raw/source/vault paths; its process is killed
and cleaned in `finally`, and its temporary root is owned by pytest. No
Production, configured Obsidian Vault, owner data, credentials or Artifact was
read or modified. Durable raw is intentionally retained within each test until
pytest cleanup so hash preservation is proven.

Rollback is limited to reverting product/test commit
`1901628eee197e3d71d7e070c41c9e586d5468de` and this documentation/report
commit. It must not touch formal memory, raw evidence, Vault, Qdrant or owner
configuration.

## Remaining gate

Fresh independent Task6 review and the final packaged Task6 validation remain
outstanding. This report makes no release, Artifact, live-service, owner or
Phase 1 completion claim.
