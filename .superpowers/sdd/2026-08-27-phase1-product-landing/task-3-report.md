# Phase 1 Product Landing — Task 3 Report

Date: 2026-08-27  
Branch: `codex/phase1-automatic-memory`  
Product/test commit: `bc3636a` (`feat: connect automatic memory ingestion to work facts`)  
Evidence/docs commit: pending

## Verdict

`IMPLEMENTED_FOCUSED_PASS` for the authorized discovery → extraction → Work Fact slice. This is a code-level and synthetic-fixture result only. It is not Artifact, release, real UI, owner, Production, or Vault acceptance.

## Scope delivered

- Metadata-only source discovery with explicit `available`, `not_found`, `consent_required`, `unsupported`, and `unavailable` states. Discovery does not read candidate chat bodies.
- Fail-closed path policy rejecting filesystem root, whole home, sensitive credential/auth/token/cookie/private database paths, symlink escape, uncontrolled recursion, inactive sources, and unknown source kinds.
- Allowlisted enumeration for authorized sources only. Obsidian enumeration reuses managed-path/frontmatter semantics from `src.obsidian.discovery`; ordinary notes remain unread.
- Internal `automatic_memory_snapshot` jobs now carry source/scan/file identity, are consumed by the existing extraction queue, pipeline, registry, and adapters, and reach terminal success or failure. Malformed jobs fail closed.
- Existing ChatGPT, Codex, generic AI-history, and Claude adapter boundaries are reused; no parser, store, queue, API, or config center was duplicated.
- Extraction writes existing raw/Vault and structured read-model rows for source, conversation, and message records. A source failure is isolated from other sources.
- Stable `automatic-memory:{scan_id}` Work Fact identity records start, progress, success/failure, retry/next actor information through existing WorkStore/projector/bridge paths.
- Authenticated 8766 router coverage includes discovery, authorized scans, summary/counts/progress/error/next action, and authorize/revoke/scan/pause/resume/retry actions.

## TDD evidence

The first implementation test run had import-collection errors for the not-yet-created modules. Those tests were corrected to assert the expected missing-module RED condition. The behavioral RED was then recorded with:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py --tb=short
14 failed in 11.1s
```

The existing tests in `tests/test_automatic_memory_obsidian.py` were restored unchanged after review caught an accidental replacement; the new managed enumeration case was appended. The original ordinary-scope and `MemoryDatabase` import-cycle regressions remain present.

## Verification

Focused Task 3 plus directly affected worker coverage:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py
24 passed, 1 warning
```

Runtime, packaged API, scheduler/resume, snapshot, worker, idempotency, adapters, Task 3, Obsidian, and control API regression matrix:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_snapshot.py tests/test_extraction_worker.py tests/test_extraction_idempotency.py tests/test_automatic_memory_adapters.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py --tb=short
195 passed, 1 deselected, 7 warnings. The one deselected case is the pre-existing `test_daily_integrity_job_runs_without_event`; the unfiltered matrix reproduces its baseline failure because the scheduler clamps `integrity_seconds` to one second. Task 2 explicitly excludes this stale scheduler cleanup/timing edge, so no Task 2 code was changed.
```

Additional gates run for this change:

- `./.venv/bin/python -m compileall -q src run_control_api.py run_packaged_control_api.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_obsidian.py`: pass.
- `git diff --check`: pass.
- `./.venv/bin/python scripts/check_acceptance_sync.py`: `PASS: product changes are accompanied by docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`.
- `./.venv/bin/python scripts/check_local_execution_handoff.py`: `PASS`; task remains `IDLE`.

## Files changed

Product/test commit `bc3636a` changes:

- `src/automatic_memory/discovery.py`
- `src/automatic_memory/path_policy.py`
- `src/automatic_memory/__init__.py`
- `src/automatic_memory/checkpoint.py`
- `src/automatic_memory/runtime.py`
- `src/automatic_memory/source_registry.py`
- `src/control/automatic_memory_api.py`
- `src/extraction/pipeline.py`
- `src/extraction/queue.py`
- `tests/test_automatic_memory_control_api.py`
- `tests/test_automatic_memory_obsidian.py`
- `tests/test_automatic_memory_discovery.py`
- `tests/test_automatic_memory_runtime_flow.py`
- `tests/test_automatic_memory_work_fact.py`

Evidence/docs changes are this report, `docs/MODULES/CODE_MAP.md`, `docs/PROJECT_STATUS.md`, and `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`.

## Boundaries and known limitations

- `LOCAL_EXECUTION_TASK.md` is `IDLE`; no live 8766 server, Artifact build/install, real UI, Production/Vault, owner data, cloud, or third-party software action was performed.
- Task 2 stale scheduler cleanup-state behavior was not changed; degraded/needs-restart remains truthful and is not reported as stopped.
- No automatic promotion seam was invoked or enabled. `AutoMemoryPromotionService.evaluate`, `promote`, `submit`, `reconcile_incomplete_projections`, and `rebuild_derived_projections` remain outside this task.
- Unknown/unsupported source formats fail closed with an evidence-bearing failure; no release or 100k/4R2 claim is made.
