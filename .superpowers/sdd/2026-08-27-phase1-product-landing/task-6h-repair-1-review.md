# Task 6H Repair Round 1 — Final Independent Review

## Review identity and boundary

- Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Branch: `codex/phase1-automatic-memory`
- Reviewed HEAD: `80d75c6ecedfbb5a4875f20962ab6c366f276927`
- Repair product/tests: `229ad16` (`fix: persist work heartbeat failures`)
- Initial review: `8daf700f4dd5dbea90e32305a67c764420b147d7`
- Review range: `8daf700f4dd5dbea90e32305a67c764420b147d7..80d75c6ecedfbb5a4875f20962ab6c366f276927`
- Product repair range inspected: `229ad16^..229ad16`; only the approved Task6H active-work heartbeat failure seam and its direct UI/test coverage were considered.
- No product changes were made by this review. Only this report is added and committed.
- `LOCAL_EXECUTION_TASK.md` is `IDLE`; no live 8766/8767, Artifact, Production/Vault, owner data, or owner acceptance was used.

## Verdict

```text
Spec: PASS
Quality: PASS
Critical: 0
Important: 0
Minor: 0
Disposition: ACCEPT_HEARTBEAT_FOR_TASK6
Task 6: NOT_ACCEPTED (external gates remain)
```

The sole approved Repair Round 1 finding (active Work Fact touch/write failure
was previously hidden as healthy `running`) is closed. The heartbeat seam is
acceptable for Task6 composition. The packaged crash 30%/70% terminal identity
count mismatch remains a Task6 packaged-matrix blocker and is not a Task6H
finding: this heartbeat diff contains no scan admission, reconciliation claim,
or retry path.

## Spec review

### Active Work Fact failure isolation and recovery — PASS

`AutomaticMemoryRuntime._touch_active_scan_work()` attempts every running scan
independently, records failures with the source/scan identity, and continues to
touch other sources. It raises only after all active scans have been attempted.
`AutomaticMemoryScheduler._heartbeat_tick()` catches that callback error,
persists the existing instance heartbeat as `degraded` with an explanatory
`reason` and `last_error`, and does not re-raise into the existing Cron loop.
The next successful tick writes `running` and clears the error. The focused
source-isolation test proves the healthy source still refreshes its Work Fact;
the recovery test proves the scheduler returns green.

### Durable/API/UI truthfulness — PASS

The heartbeat remains one mutable StateDB row per scheduler instance. Runtime
status reads that same row and exposes timestamp, computed age, instance,
generation, state, reason and last error. The authenticated API returns these
fields, including the `degraded` failure state. Desktop DTOs carry the fields,
and the Memory Sources summary distinguishes degraded, stopped, paused,
running-with-a-real-age, and unknown states without a healthy fallback.

### Idle, lifecycle and stale-instance boundaries — PASS

Focused coverage confirms idle heartbeat persistence/refresh without Work Fact
or event creation, pause continuity, stopped terminal state, fresh instance
identity after restart, stale/future timestamp degradation, DB write
failure/recovery, and no event growth. The Task6A lifecycle seams confirm
concurrent stop/start serialization and stale watcher/Cron cleanup boundaries.

### Heartbeat cadence and scheduler safety — PASS

The callback is configured on the existing Cron scheduler thread. Heartbeat
wakeups do not call reconciliation or claim scans. The focused cadence test
observed at most two claims during a 0.25s run with a 0.05s heartbeat and a
60s reconciliation poll. The packaged probe returned a real UTC timestamp and
instance/generation with `running`; a 0.6s CPU sample was 5.3%. No scheduler,
watcher, or scan was killed by a callback failure.

## Verification evidence

| Check | Fresh result |
|---|---|
| Task6H focused | `tests/test_task6h_heartbeat.py` → `8 passed` |
| Required 82 regression | listed runtime/scheduler/watcher/runtime-flow/work-fact/obsidian/control/work API/Task8/Task6H tests → `82 passed, 2 warnings` |
| Task6A lifecycle seams | three repair seam tests → `3 passed` |
| Desktop build | `npm run build` → PASS |
| Desktop smokes | `test:runtime`, `test:memory-sources`, `test:work-fact`, `test:memory-review` → all PASS |
| Packaged heartbeat focused | real `PackagedSidecar` probe → UTC timestamp, age `0.041s`, instance/generation, `running` |
| Packaged CPU probe | 0.6s sidecar sample → `5.3%` |
| Packaged integration matrix | `1 failed, 1 passed, 1 warning`; only crash 30%/70% count assertion failed (`2` scans vs `1`) |
| Compile | `python -m compileall` → PASS |
| Diff check | `git diff --check 8daf700..HEAD` → PASS |
| Acceptance sync | PASS (`changed files: 6`, `product-impacting files: 0`) |
| Local handoff | PASS; local task remains `IDLE` |

The packaged integration failure is at
`tests/integration/test_automatic_memory_packaged_flow.py:745-749`, where the
existing Task6 crash matrix compares 30% and 70% terminal identity counts.
The failure is `2 == 1` for scan identities. Review of `229ad16` shows only
the heartbeat callback error handling, active Work Fact touching, DTO fields,
and UI status mapping; it cannot create an extra scan or alter reconciliation
identity. This remains in the final Task6 blocking list and is not counted as
a Task6H Critical/Important finding.

## Contract matrix

- Active Work Fact touch/write failure is source-isolated: **PASS**.
- Failure is durably projected as `degraded` with reason/error: **PASS**.
- Scheduler/Cron and scans continue after callback failure: **PASS**.
- Subsequent successful refresh recovers to `running`/green: **PASS**.
- Idle has no active Work Fact/event growth or false degradation: **PASS**.
- Other sources still refresh when one source fails: **PASS**.
- Instance/generation and stale-instance isolation: **PASS**.
- Pause and clean stop heartbeat states: **PASS**.
- Concurrent stop/restart lifecycle serialization: **PASS** in Task6A regression.
- Future/stale timestamp and DB read/write fail-closed behavior: **PASS**.
- Heartbeat cadence does not increase reconciliation/claim cadence: **PASS**.
- API authentication and heartbeat fields: **PASS**.
- Desktop degraded/stopped/paused/running/unknown copy: **PASS**.
- Packaged crash 30%/70% terminal identity parity: **BLOCKED in Task6**, not caused by this heartbeat repair and not a Task6H finding.

## Cleanliness and scope

- Product source/tests were not modified by this review.
- Temporary pytest roots and packaged sidecars exited and were removed by the
  test harness; no LingJi-owned process or 8766/8767 listener remains.
- No Artifact, release build, live owner service, Production/Vault, owner data,
  or network upload was used.
- Existing warnings are dependency deprecations only.

## Final disposition

```text
Reviewed HEAD: 80d75c6ecedfbb5a4875f20962ab6c366f276927
Repair product/tests: 229ad16
Spec: PASS
Quality: PASS
Critical: 0
Important: 0
Minor: 0
Disposition: ACCEPT_HEARTBEAT_FOR_TASK6
Task 6: IN_PROGRESS / NOT_ACCEPTED
Task6 external blocker: packaged crash 30%/70% terminal identity mismatch
Release/Artifact/live service/Production/Vault/owner acceptance: NOT_TESTED
Local task: IDLE
```
