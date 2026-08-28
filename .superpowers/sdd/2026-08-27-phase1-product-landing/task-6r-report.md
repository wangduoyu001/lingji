# Task 6R — Snapshot-owned terminal cleanup

Date: 2026-08-28 (Asia/Shanghai)
Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
Baseline: `adb42d6710d286be0b7b930aba3cab6e9f6be7e9`

## Scope and disposition

This bounded repair closes the existing `snapshot-owned` staging-file lifecycle
gap after a real sidecar crash. Startup still preserves a marker while its scan
has an active, unexpired lease; after the resumed `SnapshotJobRunner` releases
or finalizes the scan, the same raw root is reconciled and the old marker is
removed. The change does not touch `.automatic-memory-v1` transient cleanup,
retrieval, UI, queue schema, or permanent raw objects.

`ConsistentSnapshot.reconcile_temporary_snapshots()` is now an explicit,
idempotent, machine-readable cleanup seam. It scans only direct children with
the bounded owned/legacy snapshot grammar, uses `lstat()` regular-file and
identity checks, preserves active/mismatched/unknown/malformed/symlink entries,
and returns only stable generic error codes. StateDB, root-scan, stat and unlink
errors fail closed and remain retryable. The legacy
`_cleanup_temporary_snapshots()` entry point remains as a compatibility wrapper.

`SnapshotJobRunner` invokes reconciliation after lease acquisition, pause,
failure, lease-loss release and terminal completion, and persists a generic
`last_error` when cleanup cannot complete. Runtime start/stop also invokes the
same seam and exposes cleanup failure through its existing cleanup status. A
completed scan with a cleanup error is recorded as a retryable snapshot Work
Fact failure rather than a clean success.

## TDD evidence

The new recovery test first failed against the baseline because the recovered
scan returned `completed` while the old marker still existed. After the
lifecycle wiring and explicit reconcile implementation, the focused Task 6R
suite passed `6` tests, including a real subprocess `SIGKILL`/restart case.

## Verification

```text
./.venv/bin/python -m pytest -q tests/test_task6r_snapshot_terminal_lifecycle.py
6 passed

./.venv/bin/python -m pytest -q \
  tests/test_task6r_snapshot_terminal_lifecycle.py \
  tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py \
  tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_runtime.py \
  tests/test_automatic_memory_runtime_flow.py tests/test_task6h_heartbeat.py \
  tests/test_task6l_durable_lease_receipt.py tests/test_task6m_transient_lifecycle.py \
  tests/test_task6p_queue_persistence_redaction.py \
  tests/test_task6s_source_authority_versions.py
179 passed, 2 existing deprecation warnings

./.venv/bin/python -m compileall -q src tests/test_task6r_snapshot_terminal_lifecycle.py
PASS

git diff --check
PASS
```

The focused tests cover active startup preservation, terminal completion,
pause, failure, real crash/restart, unlink failure and retry, StateDB/root
scan failures, bounded receipts, and preservation of durable raw content. No
live 8766/8767, Artifact, Production/Vault or owner data was used.

## Isolation and remaining gate

The pre-existing uncommitted Task6V change in
`tests/integration/test_automatic_memory_packaged_flow.py` was preserved and
is not part of this task's product/test changes. This task does not claim
Task6 acceptance, packaged 30/70 acceptance, release, Artifact, live service,
Production/Vault or owner acceptance. Task6 remains `IN_PROGRESS /
NOT_ACCEPTED` and Task6V remains pending rerun.
