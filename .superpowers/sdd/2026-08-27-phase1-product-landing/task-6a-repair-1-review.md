# Task 6A Repair Round 1 — Independent Final Review

## 1. Review identity and boundary

- Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Branch: `codex/phase1-automatic-memory`
- Expected reviewed HEAD: `93e653e6b46bee21e6db2587294e801996b887ae`
- Repair product/tests: `efde650e77a4ecda7f7266aefe48b29b9e8712de`
- Initial review: `9ed229461165b748066b9cba3d2ed169af43db56`
- Review range: `9ed229461165b748066b9cba3d2ed169af43db56..93e653e6b46bee21e6db2587294e801996b887ae`
- Product repair scope observed: `src/automatic_memory/scheduler.py` and `tests/test_automatic_memory_scheduler.py` only; the later `93e653e` changes are documentation/evidence only.
- Mode: independent read-only review. No product or test files were modified. Only this review report is added.

`LOCAL_EXECUTION_TASK.md` is `IDLE`; no live 8766/8767, Sidecar, Artifact, Production/Vault, owner data, or owner acceptance was started or accessed.

## 2. Final verdict

```text
Spec: PASS
Quality: PASS
Critical: 0
Important: 0
Minor: 0
Disposition: ACCEPT_FOR_TASK6
```

The two Important findings from the initial review are closed within the approved lifecycle boundary. No second Task6A repair is required or recommended.

## 3. I1 — exact cleanup ownership and truthful retry

### Verification

`AutomaticMemoryScheduler` now records cleanup failures by component owner in `_cleanup_error_parts`, while retaining the existing public `source_cleanup_errors` projection. Global stop/retry calls both `watcher.stop()` and `cron.stop()` on every attempt. Watcher-owned errors are cleared only after a fresh empty survivor observation; Cron-owned errors are cleared only after the Cron stop call succeeds and `cron.running` is false. A live Cron or any cleanup exception remains an error and raises instead of producing a stopped result. Source-level disable errors use `cron:<source_id>` and `watcher:<source_id>` ownership, and clearing one owner preserves other source/error entries.

The real seam test `test_cleanup_retry_retries_cron_and_preserves_unrelated_error` uses a real watcher thread held by `threading.Event` and a threaded Cron seam whose first `stop()` fails while remaining alive. It proves the first stop is degraded, the second stop retries Cron, and an unrelated source error survives resolution of the owned watcher/Cron cleanup. The late-watcher runtime regression separately proves a surviving watcher remains degraded/cleanup-pending until natural exit, then a retry converges to stopped.

Result: **PASS**.

## 4. I2 — lifecycle serialization and generation safety

### Verification

`start()` and `stop()` now share `_stop_lock`. Stop invalidates the previous lifecycle generation before measuring watcher/Cron cleanup; start cannot publish a new generation until that cleanup finishes. The event-seam test `test_scheduler_start_waits_for_inflight_stop_cleanup` holds a real watcher thread in stop, confirms concurrent start has not returned, releases the event, and then verifies both operations finish without deadlock, the new watcher/Cron are running, and there is only one source watcher. `test_scheduler_stop_after_start_is_serialized_and_idempotent` covers start/stop ordering and repeated stop.

The initial review's two interleavings were rerun through the three repair seams 10 consecutive times (`10/10` complete). No run observed inconsistent scheduler/Cron terminal state, duplicate watcher attachment, deadlock, or stale-generation callback damage. Existing `test_late_listener_from_previous_lifecycle_cannot_disable_restarted_scheduler` also remains green.

Result: **PASS**.

## 5. Fresh verification evidence

All commands below were run on the exact reviewed HEAD. Pytest used temporary test directories/threads only.

| Check | Fresh result |
|---|---|
| Repair seams (Cron retry, ownership, start/stop serialization) | `3 passed, 1 warning` |
| Task6A late-watcher regression plus repair seams | `4 passed, 1 warning` |
| Task2 lifecycle/packaged/watcher/runtime composition | `74 passed, 6 warnings` |
| Task2 broader runtime/state/resume/promotion-sentinel matrix | `172 passed, 6 warnings` |
| Task3 focused admission/runtime regression | `24 passed, 1 warning` |
| Task5A Work/API backend matrix | `40 passed, 2 warnings` |
| Direct affected Task3/4/5 and extraction matrix | `227 passed, 7 warnings` |
| `npm run test:runtime` | `runtime-sidecar-smoke: PASS` |
| `python -m compileall` (source, packaged entrypoints, affected tests) | PASS |
| `git diff --check 9ed2294..HEAD` | PASS |
| `scripts/check_acceptance_sync.py` | PASS (`changed files: 5`, `product-impacting files: 0`) |
| `scripts/check_local_execution_handoff.py` | PASS; handoff remains `IDLE` |

One earlier broad composite invocation had one timing-sensitive resume assertion fail; the named test passed in isolation and the same broad invocation passed on immediate rerun (`172 passed`). It did not reproduce as a repair defect and no test was changed or weakened.

## 6. Regression and contract matrix

- Late natural watcher exit: PASS; still-alive watcher remains degraded/cleanup-pending, later retry reaches stopped.
- Persistent Cron cleanup failure or live Cron: PASS; retry is attempted and stopped is not reported.
- Watcher/Cron/source error isolation: PASS; owner-specific clearing preserves unrelated entries.
- Concurrent stop/retry: PASS; serialized and idempotent.
- Start versus in-flight stop: PASS; start waits for cleanup and cannot publish an overlapping generation.
- Old lifecycle listener/generation: PASS; stale callback cannot disable a restarted scheduler.
- Revoke/unsupported/expired/degraded source transitions: PASS in existing lifecycle matrix; source watcher/job cleanup remains bounded and truthful.
- Scheduler shutdown and packaged process-exit/startup-failure cleanup: PASS in the packaged/runtime matrix; no process boundary implementation was changed by this repair.
- Promotion-forbidden background seams: PASS in existing sentinel matrix; no background promotion seam was called.
- Architecture/scope: PASS; no second queue, state machine, API family, store, poller, discovery, adapter, Work Fact, UI, promotion, retrieval, or vector path was introduced.

## 7. Documentation and acceptance boundary

The reviewed documentation correctly identifies `efde650e77a4ecda7f7266aefe48b29b9e8712de` as the sole authorized product/test repair and `93e653e6b46bee21e6db2587294e801996b887ae` as synchronized evidence/docs. It keeps Task 6A separate from Task 6, release, Artifact, live service, Production/Vault, and owner acceptance. Existing historical pass counts in the repair report are not treated as a substitute for the fresh commands above.

No live UI, Artifact, release build, Production/Vault, owner observation, or physical acceptance claim is made.

## 8. Final disposition

```text
Reviewed HEAD: 93e653e6b46bee21e6db2587294e801996b887ae
Repair product/tests: efde650e77a4ecda7f7266aefe48b29b9e8712de
Spec: PASS
Quality: PASS
Critical: 0
Important: 0
Minor: 0
Disposition: ACCEPT_FOR_TASK6
Task 6: NOT_TESTED / unclaimed
Release/Artifact/owner acceptance: NOT_TESTED / unclaimed
Local task: IDLE
```

This is the independent final review for the one authorized Task6A repair round. With zero Critical and Important findings, Task6A is accepted for Task6 composition; Task 6/release/Artifact/owner acceptance remain separate pending work.
