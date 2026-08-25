# Phase 1 Automatic Memory — Task 2 Report

## Status

Implemented in the isolated `codex/phase1-automatic-memory` worktree from baseline `2cae375dc62a6445059316a36b9a1408a3400a86`.

## RED / GREEN

- RED: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py` — 9 failures during the initial run because `src.automatic_memory.snapshot` and `checkpoint` did not exist. The test imports were then made collection-safe and the failures remained feature-specific (`production module is absent`).
- GREEN: the same focused command — `9 passed`.
- Task 1 and extraction regression command — `38 passed`.
- Expanded extraction/control regression command — `25 passed, 1 warning`.
- Combined automatic-memory/extraction keyword run — `68 passed, 2 warnings`.
- Full pytest — `581 passed, 11 skipped, 2 unrelated baseline/environment failures`:
  - `tests/test_p2_08_p2_09_integration.py::test_desktop_uses_shared_polling_and_shadow_dashboard_without_execution_controls` (pre-existing desktop assertion mismatch outside Task 2).
  - `tests/test_second_brain.py::SecondBrainTests::test_second_brain_is_not_in_original_start_chain` (the test invokes unavailable executable `python`; this environment exposes `.venv/bin/python`/`python3`).

## Design and transaction boundary

- `ConsistentSnapshot` re-reads the existing Task 1 source/grant state on every attempt, confirms owner authorization is active, rejects symlinks, directories and root escapes, and performs stat-before → fsynced temporary copy → SHA-256 → stat-after. Size, mtime and inode changes delete the temporary and retry up to three attempts. Stable content is atomically committed into `storage/raw/<sha256>` through the existing extraction sink helper.
- Source files are only read. The implementation does not use `copy2` or otherwise change source bytes, mtime, mode, or owner.
- `build_snapshot_idempotency_key` binds `source_id + normalized relative path + sha256`; queue admission uses this key after raw commit. Existing queue uniqueness and content-addressed sink behavior converge repeated scans without duplicate jobs/objects.
- `ResumeToken` and `CheckpointStore` persist cursor, source sentinel, lease ID, attempt and recovery JSON in the existing `automatic_memory_scans` row. State schema migration is additive for existing Task 1 databases (`source_sentinel`, `lease_id`, `attempt`).
- `SnapshotJobRunner` obtains a lease, consumes only the constructor-injected path provider, sorts by normalized relative path, checkpoints only after raw commit and queue admission, supports deterministic `none`/`30%`/`70%`/`after-lease` controlled interruption, releases leases, and resumes strictly after the last confirmed cursor.

## Changed files

- `.superpowers/sdd/2026-08-26-phase1-automatic-memory/task-2-report.md`
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- `src/automatic_memory/__init__.py`
- `src/automatic_memory/models.py`
- `src/automatic_memory/source_registry.py`
- `src/automatic_memory/snapshot.py`
- `src/automatic_memory/checkpoint.py`
- `src/extraction/idempotency.py`
- `src/extraction/sink.py`
- `src/storage/state_db.py`
- `tests/test_automatic_memory_snapshot.py`
- `tests/test_automatic_memory_resume.py`

## Security and scope checks

- `./.venv/bin/python scripts/check_acceptance_sync.py` — PASS.
- `./.venv/bin/python scripts/check_local_execution_handoff.py` — PASS; local task remains `IDLE`.
- `git diff --check` — PASS.
- Secret-pattern and developer-absolute-path scans over changed source/tests — no findings.
- No real chats, Vault, third-party AI directories, Artifact, or local acceptance task were accessed or changed.

## Commit

- Commit: `1fd786f6079671420ac1ec512f55f0a4b7e18d5e` (`feat: make automatic memory snapshots resumable`).

## Concerns

- Full-suite failures listed above are outside Task 2 and need separate baseline/environment follow-up; they were not weakened or changed.
- Windows-specific directory fsync behavior is handled as an allowed platform fallback; the atomic rename remains the commit boundary.
