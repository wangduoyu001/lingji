# Task 2 Report — Packaged automatic-memory runtime

## Verdict

`IMPLEMENTED_FOCUSED_PASS` for the Task 2 lifecycle/composition scope. This report does not claim Task 3 snapshot consumption, adapter dispatch, terminal extraction, Work Fact projection, Desktop onboarding, Artifact, Production, Vault, or owner acceptance.

## Identity

- Base: `5510b4f27b8fd0567f4fd89a7f5ba2f65635bb77`
- Product/tests commits: `cbee300` (`feat: compose packaged automatic memory runtime`), `c415f5a` (`fix: preserve runtime cleanup on scheduler stop errors`), `bc34b9d` (`fix: harden automatic memory runtime lifecycle`), and `593b7d0` (`fix: close packaged runtime repair boundaries`)
- Evidence/docs commits: `a716b7cf0aef8227dc6268295bfd89aeff5a773d`, `2200c52c5d0a0d764e4545e25bd29c7431a61ffb`, and `8e7e07393cd86ec90a84f5a82e561b7801cedd6f`.
- Branch: `codex/phase1-automatic-memory`

## Scope delivered

- Added `AutomaticMemoryRuntime` as the single packaged owner of the existing Extraction Worker and AutomaticMemory Scheduler. Scheduler remains the owner of watcher and CronScheduler.
- Reused the canonical state path and injected the pipeline queue wrapper into the control service; mismatched state/queue paths fail closed.
- Added authenticated `/api/automatic-memory/runtime` status projection. Scheduler heartbeat age is deliberately `null` with an explicit unavailable reason because the existing scheduler has no trustworthy idle heartbeat source.
- Wired packaged control startup and shutdown. Runtime starts before uvicorn and stops before `GovernedLocalControlService.close()`.
- Runtime composition contains no calls to the five quarantined background promotion seams.

## Commands and results

- RED: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py` with placeholder runtime: `3 failed, 14 passed`; the initial import-only attempt produced a collection error before the placeholder was added.
- GREEN focused: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_control_api.py tests/test_capture_api.py` → `54 passed, 2 warnings`.
- Desktop smoke: `npm run test:runtime` (cwd `desktop/lingji-control`) → `runtime-sidecar-smoke: PASS`.
- Real temporary composition probe: one uvicorn call at `127.0.0.1:8766`; runtime start/stop completed; temporary state and memory DBs stayed under the temporary root.
- Static checks: `py_compile` PASS; `git diff --check` PASS; `./.venv/bin/python scripts/check_acceptance_sync.py` PASS; `./.venv/bin/python scripts/check_local_execution_handoff.py` PASS.

## Limits / not measured

- `LOCAL_EXECUTION_TASK.md` remains `IDLE`; no packaged Artifact, service, UI, Production/Vault, 8766 live server, release build, or owner observation was performed.
- Task 2 intentionally uses an empty path-provider placeholder because authorized enumeration and `automatic_memory_snapshot` consumption belong to Task 3. A queued snapshot must not be described as terminally extracted by this task.
- Existing worker/scheduler classes do not provide a trustworthy idle heartbeat; no fake timestamp or heartbeat daemon was added.
- Full/release validation and the independent Luna review remain for the root agent.

## Repair Round 1

- Review: `task-2-review.md`, head `2200c52c5d0a0d764e4545e25bd29c7431a61ffb`; findings addressed: I1 startup/stop cleanup, I2 live authorization attachment, I3 executable real packaged composition coverage, I4 surviving watcher/worker truthfulness, M1 never-started pause status.
- Additional product commit: `bc34b9da3427906810a46e32fcccd6d5efe4f680`; docs/report commit follows separately.
- RED: new lifecycle/dynamic-authorization/surviving-thread tests failed with `5 failed, 6 passed` on the prior implementation.
- Repair GREEN: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py` → `27 passed, 6 warnings`; broader scheduler/worker/resume regression → `106 passed, 6 warnings`; final focused after all repair changes → `106 passed, 6 warnings`.
- Repair scope remains Task 2 only. No discovery, snapshot consumer, adapter dispatch, Work Fact, UI, promotion, Artifact, Production, Vault, or owner acceptance work was performed.

## Repair Round 2 (final)

- Review: `task-2-repair-1-review.md`; only I5 and I3 were changed. No third repair round is planned.
- I5: source revocation disables persisted scheduler jobs first, performs only a bounded 100 ms watcher join, retains uncooperative watcher survivors in the running map, exposes per-source cleanup errors through runtime status, records an audit event when possible, and allows whole-runtime stop to retry and recover. A raising registry observer cannot hide this status.
- I3: runtime construction now fails closed unless `state_db`, `queue`, `pipeline.queue`, `registry.state_db`, and `scheduler.state_db` all expose paths resolving to the same canonical file. Mismatch tests use `a.db` and `b.db`.
- Wrapper composition test: `run_packaged_control_api.main()` runs in an independent subprocess with real environment configuration, lifecycle monitor, pipeline, service, runtime, scheduler, worker, registry and persisted jobs; only `uvicorn.run` is replaced. Normal and injected scheduler-start-failure paths assert canonical DB/queue paths, real scheduler/worker thread ownership, and sidecar cleanup after child exit.
- Round2 focused GREEN: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py` → `32 passed, 6 warnings`.
- Runtime/scheduler/watcher/state/worker/promotion-sentinel matrix: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_watcher.py tests/test_extraction_worker.py tests/test_state_db_scheduler.py tests/test_automatic_memory_resume.py tests/test_auto_memory_promotion.py` → `167 passed, 6 warnings`.
- Broader matrix: adding `tests/test_promotion_recovery_matrix.py` → `181 passed, 1 failed, 6 warnings`; the pre-existing `test_recovery_case_06_restart_after_link_commit_activates_after_verification` still returns `rolled_back` instead of `VISIBLE_ACTIVE`. No promotion source or test changed in this round, so this is recorded as an unrelated baseline limitation rather than repaired under Task2.
- Desktop smoke: `npm run test:runtime` (cwd `desktop/lingji-control`) → `runtime-sidecar-smoke: PASS`.
- Static checks: `./.venv/bin/python -m compileall -q src run_control_api.py run_packaged_control_api.py tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py` and `git diff --check` → PASS.
- No Artifact, Production, Vault, 8766 live server, UI, Task3 snapshot consumer/adapter/terminal extraction, or promotion background call was added. `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## Round2 delivery identity

- Product/tests commit: `593b7d0` (`fix: close packaged runtime repair boundaries`).
- Documentation/report commit: recorded separately after acceptance-sync and local-handoff rechecks.
