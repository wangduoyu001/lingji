# Task 6M — Automatic-memory transient lifecycle (Repair Round 1)

Date: 2026-08-28  
Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
Baseline: `8cc4d4aabce5a09e7db3754ed9197e33e0b5bf2a`  
Reviewed implementation: `8dd877a6117f82f1b9bc3d8a1c785e5355aea56f`
Independent review: `b65f81d659f787e349d545f51c4ddb94af770d4b`
Repair product/test commit: `4b51392fe448472e9099978ff2528f742dff887b`

## Scope and disposition

This single authorized Repair Round 1 addresses only review I1/I2/I3/I5 and
M1/M2 at the existing extraction pipeline/worker/runtime and Desktop boundary.
Task 6 remains `IN_PROGRESS / NOT_ACCEPTED`; I4 fresh packaged 30/70
validation is deferred to a new Task6V and is not represented as a pass.

The bounded task closes the Task 6C defect in which
`_execute_internal_snapshot` left `.automatic-memory-*.json/jsonl/md` adapter
dispatch hard links after a real process crash. It does not change Task 6's
packaged harness, retrieval, quality gate, promotion, discovery or API surface;
the only UI change is consumption of the existing runtime fields in the
existing MemorySourcesPage. Task 6 remains `IN_PROGRESS / NOT_ACCEPTED`.

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

Legacy `.automatic-memory-{32hex}{suffix}` markers are removable only when a
same-directory 64hex raw file has matching SHA-256 filename and marker/raw
lstat identity proving a hard link. v1 terminal/released/expired/dead-worker
cleanup likewise requires a valid direct-child content-addressed raw and
marker/raw hard-link identity. A second lstat immediately before unlink keeps
identity changes; queue/SQLite/stat/unlink failures remain in the existing
inventory for retry. `MemorySourcesPage` consumes runtime cleanup fields and
shows only `临时文件清理失败：灵机会自动重试，可重试。` (no path/job/lease data).

## TDD evidence

### RED (repair)

Against the reviewed implementation, the repair behavior tests first produced
the following RED:

```text
8 passed, 4 failed
```

The four failures were legacy proof, non-hardlinked/wrong-lease proof, queue
RuntimeError containment and identity-change protection. The test file remains
the behavioral contract.

### GREEN (repair)

```text
.venv/bin/python -m pytest tests/test_task6m_transient_lifecycle.py tests/test_automatic_memory_runtime.py -q
31 passed, 1 warning

cd desktop/lingji-control && npm run test:memory-sources
automatic-memory-sources-smoke: PASS

cd desktop/lingji-control && npm run build
TypeScript/Vite build PASS
```

The lifecycle cases cover bounded job/lease naming, terminal and idempotent
cleanup, active/expired leases, malformed/unknown/symlink/directory safety,
unlink `PermissionError` visibility and retry, two-worker isolation, formal
pipeline adapter dispatch, and a real subprocess SIGKILL followed by restart
pipeline reconciliation. The crash case observes a marker created by the
formal `_execute_internal_snapshot` path; it does not hand-write a marker as
its primary proof. The durable raw object's existence and SHA-256 are checked
after reconciliation.

## Regression and static verification

```text
.venv/bin/python -m pytest -q \
  tests/test_task6m_transient_lifecycle.py tests/test_automatic_memory_snapshot.py \
  tests/test_automatic_memory_resume.py tests/test_extraction_queue.py \
  tests/test_extraction_worker.py tests/test_automatic_memory_runtime.py \
  tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_adapters.py \
  tests/test_structured_evidence_lexical.py tests/test_structured_ingestion.py \
  tests/test_automatic_memory_scheduler.py tests/test_task6h_heartbeat.py \
  tests/test_task6s_source_authority_versions.py tests/test_task8_extraction_work_lifecycle.py \
  tests/test_task8_work_fact.py tests/test_task8_work_transition_matrix.py
250 passed, 3 warnings

./.venv/bin/python -m compileall -q src tests/test_task6m_transient_lifecycle.py
PASS

git diff --check
PASS
```

The warnings are existing Starlette/httpx deprecation, Pydantic deprecation and
duplicate fixture warnings. No assertions were removed, skipped or weakened.

`.venv/bin/python -m compileall -q src tests` and `git diff --check` passed.
Acceptance sync and local handoff checks passed after this documentation commit.

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
`4b51392fe448472e9099978ff2528f742dff887b` and this documentation/report
commit. It must not touch formal memory, raw evidence, Vault, Qdrant or owner
configuration.

## Remaining gate

The independent review's authorized I1/I2/I3/I5/M1/M2 scope is implemented and
focused-tested. I4 fresh packaged 30/70 remains outstanding for new Task6V, and
Task6 final validation remains outstanding. This report makes no release,
Artifact, live-service, owner or Phase 1 completion claim.
