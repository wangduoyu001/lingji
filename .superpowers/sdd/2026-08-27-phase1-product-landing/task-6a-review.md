# Task 6A Lifecycle Closeout — Independent Final Review

## 1. Review identity and scope

- Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Branch: `codex/phase1-automatic-memory`
- Reviewed `HEAD`: `bd194f51b5b774eb8815c683336fed115e11a735`
- Product/tests under review: `15eb4433c9d6c3ba218e89d50bec84987ad35915`
- Diff under review: `bd2ff43f3b3e5b856438c9f2e692f2b31e1c3602..bd194f51b5b774eb8815c683336fed115e11a735`
- Product scope observed: `src/automatic_memory/scheduler.py` and `tests/test_automatic_memory_runtime.py`; documentation/status updates are consistent with the bounded Task 6A description and do not claim Task 6, release, Artifact, live service, Production/Vault or owner acceptance.
- Review mode: read-only product review. No product file, test file, live port, Sidecar, Artifact, Production/Vault or owner data was changed or started. Only this ignored review report is written.

## 2. Verdict

```text
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 2
Minor: 0
Disposition: REPAIR_ROUND_1
```

The requested late-watcher happy path is implemented and covered by a real watcher thread plus `threading.Event`: a live survivor remains degraded/cleanup-pending, natural exit is observed, and a serialized retry reaches stopped. The closeout is not acceptable yet because the new retry path can erase unrelated cleanup evidence and skip a still-live Cron cleanup retry, and scheduler start is not serialized against stop. Both are directly within the required concurrent/accurate lifecycle contract.

## 3. Verified strengths

- The new regression uses `AutomaticMemoryScheduler` and `AutomaticMemoryWatcher` with a real backend thread and `threading.Event`; it does not mock the watcher return value to prove the target behavior.
- First stop/revoke preserves a surviving watcher and reports `degraded`, `cleanup_pending=true`, and a source-specific cleanup error. The watcher is only removed from `running_sources()` after its event seam is released and the thread exits naturally.
- Two concurrent retry/stop calls are serialized by `_stop_lock`; the tested late-exit case converges to runtime `stopped`, `running=false`, no cleanup errors and no surviving watcher.
- Existing packaged composition tests exercise real scheduler/worker/pipeline construction in a subprocess with only the Uvicorn network boundary replaced. Promotion-forbidden seams remain sentinel-protected.
- The diff stays within the approved product/test boundary; no second state machine, queue, API family, promotion path, discovery path, UI or data model was added.

## 4. Important findings

### I1 — Retry can mask unrelated source errors and leave a live Cron scheduler

**Location:** `src/automatic_memory/scheduler.py:99-120` and `src/automatic_memory/scheduler.py:122-156`.

The non-running retry branch calls `watcher.stop()`, but never retries `cron.stop()`. If the initial stop recorded a Cron cleanup failure, the second stop can observe no watcher survivors, execute `_source_cleanup_errors.clear()`, return successfully, and report a clean terminal state while the Cron component remains alive. A direct seam probe reproduced:

```text
first RuntimeError {'__scheduler__': 'cron still alive'} 1 True
final {} 1 True
```

The same unconditional `.clear()` also removes errors belonging to other sources (or non-watcher cleanup failures). A separate probe preloaded `{"src-a": "survivor-a", "src-b": "backend-b"}` and an empty watcher result; the method returned `{}`. This violates the explicit requirement to clear only the cleanup evidence reconciled by an empty survivor observation and to preserve other `source/error` state. It can produce a false `stopped`/`cleanup_pending=false` projection while an owned scheduler thread or unrelated cleanup problem remains.

**Required fix:** keep cleanup ownership per component/source; on retry re-run every previously failed owned cleanup (including Cron), only clear the specific error(s) whose resources were freshly observed gone, and retain unrelated source/error entries. Add a real-thread/Cron seam regression asserting a failed first Cron stop remains degraded until Cron cleanup succeeds.

### I2 — Scheduler start can race with stop and leave inconsistent lifecycle state

**Location:** `src/automatic_memory/scheduler.py:77-92` and `src/automatic_memory/scheduler.py:94-157`.

`_stop_lock` protects only `stop()`. `start()` does not acquire it. With a real `CronScheduler` and an event-blocked watcher stop, a concurrent `start()` can observe `_running=False` while the old stop is still cleaning up, set `_running=True`, and return while the existing Cron is still marked running. The old stop then stops that Cron instance. The observed final state was:

```text
during True True False
final True False False
```

Here `scheduler._running=True` but `cron.running=False`; the next status/runtime projection can claim a running scheduler despite no scheduler loop, and the next lifecycle call is no longer an exact serialized transition. This violates the required concurrent stop/retry/shutdown lifecycle serialization and can also interleave watcher attachment with the prior generation's cleanup.

**Required fix:** serialize `start()` with the same lifecycle gate as stop (or use one lock/state transition protocol), and add a real event-seam concurrency test proving no start can publish a new generation until the previous stop has fully resolved; assert no second watcher/cron and consistent final state.

## 5. Test and verification evidence

All commands below were run fresh on the reviewed worktree. Python tests used pytest temporary directories and test threads only; the Desktop smoke was a local static/composition check.

| Check | Result |
|---|---|
| Task 6A focused real-thread test | `1 passed, 1 warning` — `test_late_watcher_exit_clears_scheduler_cleanup_error_on_second_stop` |
| Task 2 lifecycle/packaged/watcher/worker/promotion matrix | `168 passed, 6 warnings` |
| Task 3 admission/runtime/control regression matrix | `197 passed, 7 warnings` |
| Task 5A backend contract matrix | `40 passed, 2 warnings` |
| Work/Task8/Capture/Work Fact regression | `102 passed, 2 warnings` |
| Packaged composition smoke | `npm run test:runtime` → `runtime-sidecar-smoke: PASS` |
| Compile check | `python -m compileall -q ...` → PASS |
| Diff check | `git diff --check bd2ff43..HEAD` → PASS |
| Acceptance sync | PASS (`changed files: 5`, `product-impacting files: 0`) |
| Local handoff | PASS |
| Worktree | clean at review and report preparation; `HEAD` is exact expected `bd194f5...` |

The existing warnings are dependency/lifecycle deprecations plus the known duplicate ZIP-member warning; no test was weakened or skipped by this review. No live `8766/8767`, Artifact, release build, Production/Vault or owner acceptance was run, as required.

## 6. Scope and contract assessment

- **Truthful watcher state:** PASS for the tested survivor and natural-exit path; the implementation does not report stopped while `running_sources()` still contains the survivor.
- **Late retry convergence:** PASS for the single-source watcher case; FAIL as a complete cleanup contract because Cron failure and unrelated source errors can be hidden (I1).
- **Concurrent retry/stop:** PASS for the tested two-stop retry; incomplete for cross-operation lifecycle serialization (I2).
- **Revoke/source isolation:** PASS for tested revoke admission/job disable and source-specific degraded reporting; I1 shows cleanup-error isolation is not complete.
- **Process-exit boundary:** Existing packaged-wrapper subprocess cleanup remains covered and was not changed; this review makes no new process-exit claim.
- **Promotion quarantine:** PASS in the existing sentinel matrix; no forbidden background promotion seam was called.
- **Architecture/scope:** PASS; the diff does not introduce a second state machine, polling loop, queue, API, permanent store or promotion bypass.
- **Evidence/documentation:** PASS for accurately keeping Task 6A implementation/focused status distinct from Task 6/release/Artifact/owner acceptance. This review does not treat the implementation report as independent acceptance.

## 7. Minimal repair boundary and retest

Repair only the lifecycle ownership in `src/automatic_memory/scheduler.py` and add real-thread/event regressions in `tests/test_automatic_memory_runtime.py` (or the directly owning scheduler test module). Do not modify discovery, adapters, snapshot consumer, Work Fact, UI, promotion, retrieval/vector, data models or API families.

Retest the focused Task 6A case plus:

1. failed Cron cleanup → retry must retry and remain degraded until no owned Cron/watcher resources survive;
2. two sources with independent cleanup errors → resolving one must not clear the other;
3. concurrent start/stop/retry/revoke/shutdown with event seams → no deadlock, no second watcher, serialized generation and consistent stopped/degraded truth;
4. the existing Task 2/3/4/5 matrices, packaged smoke, compileall, diff-check, acceptance sync and local handoff.

## 8. Final disposition

```text
Product/tests: 15eb4433c9d6c3ba218e89d50bec84987ad35915
Reviewed HEAD: bd194f51b5b774eb8815c683336fed115e11a735
Spec: FAIL
Quality: NEEDS_FIXES
Disposition: REPAIR_ROUND_1
Critical: 0
Important: 2
Minor: 0
Task 6: NOT_ACCEPTED
Release/Artifact/owner acceptance: NOT_TESTED / unclaimed
```
