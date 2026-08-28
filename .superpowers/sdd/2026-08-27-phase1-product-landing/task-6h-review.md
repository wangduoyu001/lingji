# Task 6H — Independent Fresh Review

## Review identity and boundary

- Worktree: `codex/phase1-automatic-memory`
- Reviewed HEAD: `b40c2eba51184b508e52721ff4bd45554c22ab87`
- Product/tests under review: `191c90fc41bfc281cffcb2e4bda434ea01a636c3`
- Product diff: Task6H changes in `src/automatic_memory/runtime.py`,
  `src/automatic_memory/scheduler.py`, `src/scheduler/cron.py`,
  `src/storage/state_db.py`, `src/work/store.py`, the runtime API and
  `tests/test_task6h_heartbeat.py`; HEAD additionally contains only the
  synchronized evidence/docs commit.
- Review mode: independent read-only review. No product or test files were
  changed. Only this report is added and committed.
- No live 8766/8767 owner service, release Artifact, Production/Vault, owner
  data or owner acceptance was used.

## Verdict

```text
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 2
Minor: 1
Disposition: REPAIR_ROUND_1
Task 6: NOT_ACCEPTED
```

The bounded heartbeat implementation is present and the focused unit contract
passes. It is not acceptable as a Task6 gate because the mandated packaged
crash 30%/70% matrix fails, and an active Work Fact heartbeat callback failure
is silently reported as a healthy running scheduler.

## Verified strengths

- `CronScheduler._loop` invokes the heartbeat callback from its existing
  scheduler-owned thread; no second idle heartbeat service or queue was added.
- Production composition defaults the heartbeat interval to 5 seconds and
  clamps test/custom values to `<=5`; a real packaged subprocess returned a
  UTC heartbeat timestamp, computed age, `instance_id`, generation and
  `running` state over authenticated loopback HTTP.
- One mutable `automatic_memory_heartbeats` row is stored in the existing
  `StateDatabase`; the focused tests prove in-place refresh, pause continuity,
  clean stopped state, restart instance isolation, stale/future timestamp and
  DB write failure degradation/recovery, and no idle Work Fact/event growth.
- Reconciliation claim cadence remains separate from heartbeat cadence. The
  focused cadence test observed at most two claims during a 0.25s run with a
  0.05s heartbeat and 60s poll interval.
- Existing lifecycle serialization and startup-cleanup tests remain green;
  no second scheduler or duplicate watcher path was introduced.
- Authenticated API, Desktop contract smokes, rendered owner E2E, compile,
  diff and acceptance synchronization checks passed below.

## Important findings

### I1 — Packaged crash 30%/70% terminal identities are not equivalent

**Severity:** Important (P1)
**Evidence:** `tests/integration/test_automatic_memory_packaged_flow.py:745-749`

Fresh execution of the required cross-process packaged command:

```text
./.venv/bin/python -m pytest -q \
  tests/integration/test_automatic_memory_packaged_flow.py --tb=short
→ 1 failed, 1 passed, 1 warning in 127.30s
```

The real `run_packaged_control_api.py` subprocesses started successfully and
completed the scan/lease recovery path, but the final matrix assertion found
30% recovery with 2 terminal scan IDs versus 70% recovery with 1. The 30%
root contained the original manual scan plus a second terminal reconciliation
scan; the 70% root contained one reconciliation scan. This violates the
Task6 scenario requiring crash at 30% and 70% to restart to identical terminal
counts, even though job/raw/structured counts were otherwise complete.

**Required fix:** make the crash recovery/startup reconciliation path reuse or
serialize the durable scan identity so both crash positions converge to the
same terminal scan/work identity and counts. Re-run the full packaged command
twice from clean Acceptance roots; any skipped or mismatched matrix remains a
failure.

### I2 — Active Work Fact heartbeat callback failure is swallowed

**Severity:** Important (P1)
**Location:** `src/automatic_memory/scheduler.py:240-245`

`_heartbeat_tick()` catches an exception from `heartbeat_work_callback` and
only assigns the in-memory `_heartbeat_reason`. The next successful
`_write_heartbeat("running")` clears that reason, while `heartbeat_status()`
only overrides the persisted row when `_heartbeat_last_error` is set. Thus an
active Work Fact update failure is neither persisted nor projected as
degraded. A direct fresh probe that injected a failing callback printed:

```text
running None None
```

The runtime therefore continues to advertise `running` with no heartbeat
reason/error even though `work_items.updated_at` did not refresh. This violates
the requirement that active Work Fact `updated_at` be real and failures not be
presented as healthy success.

**Required fix:** treat a failed active-work refresh as a durable degraded
heartbeat (with `reason` and `last_error`) and recover only after a subsequent
successful refresh; add a focused test asserting no false healthy status and
that event rows remain unchanged.

## Minor finding

### M1 — Desktop DTO does not carry the new heartbeat fields and has a broad status fallback

`desktop/lingji-control/src/pages/memorySourcesTypes.ts:60-69` models only
heartbeat age/reason, not the API's timestamp, instance, generation, state and
last-error fields. `MemorySourcesPage.tsx:128` displays “后台状态持续更新” for
any runtime state other than exactly `degraded`, including `stopped` or an
unknown value. The API itself is truthful and source cards use neutral
`尚未获得`/`需要检查` labels, so this is a non-blocking contract/evidence gap
for the bounded Task6H change; it should be corrected or explicitly excluded
before owner-facing heartbeat diagnostics are claimed.

## Fresh verification evidence

| Check | Result |
|---|---|
| Task6H focused | `tests/test_task6h_heartbeat.py` → `6 passed` |
| Required 80 regression | `80 passed, 2 warnings` |
| Task6A lifecycle repair seams | `3 passed, 1 warning` |
| Packaged cross-process wrapper tests | `2 passed` |
| Required packaged crash/two-run flow | `1 failed, 1 passed, 1 warning`; I1 |
| Desktop contract smokes | runtime, memory-sources, work-fact, memory-review → all PASS |
| Desktop rendered E2E | `e2e_owner_memory_flow: PASS` |
| Desktop TypeScript/Vite build | PASS; Vite emitted only existing chunk warnings |
| Cross-process runtime heartbeat probe | PASS: authenticated packaged process returned running UTC heartbeat with age/instance/generation |
| Python compileall | PASS |
| `git diff --check 191c90f..HEAD` | PASS |
| `scripts/check_acceptance_sync.py` | PASS (`changed files: 6`, `product-impacting files: 0`) |
| `scripts/check_local_execution_handoff.py` | PASS; local task remains IDLE |
| Worktree after evidence cleanup | clean before adding this report |

All test fixture roots and packaged subprocesses created by this review were
terminated/removed. No LingJi-owned process, live port, Artifact, Production
data, Vault or owner configuration was touched.

## Contract matrix

- Same existing Cron scheduler thread / no second service: **PASS**.
- Default cadence `<=5s`, computed age and non-fixed timestamp: **PASS** in
  focused and packaged status probes.
- `instance_id + generation`, restart isolation and stale/clock-jump handling:
  **PASS** in focused tests.
- Pause heartbeat / stopped terminal state / concurrent start-stop lifecycle:
  **PASS** in focused and Task6A lifecycle matrices.
- Startup cleanup, DB read/write fail-closed and recovery: **PASS** in existing
  runtime/lifecycle tests and Task6H write/read seams.
- Heartbeat does not run reconciliation at heartbeat frequency and idle event
  rows do not grow: **PASS**.
- Active Work Fact refresh without event growth: **PASS** on success path;
  **FAIL** on callback failure because I2 hides the failure.
- Existing StateDB/schema compatibility and authenticated loopback API:
  **PASS** for the exercised existing-DB and API matrices.
- Unknown/degraded UI honesty: **MINOR GAP** (M1); API/source-state failure
  labels are truthful, but the runtime DTO/UI does not expose all heartbeat
  fields and has a broad stopped/unknown fallback.
- Secret/auth/scope regression: **PASS** in the 80-case and packaged wrapper
  matrices; no credentials or owner data were exposed.

## Final disposition

```text
Reviewed HEAD: b40c2eba51184b508e52721ff4bd45554c22ab87
Product/tests: 191c90fc41bfc281cffcb2e4bda434ea01a636c3
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 2
Minor: 1
Disposition: REPAIR_ROUND_1
Task 6: NOT_ACCEPTED
Release/Artifact/live service/Production/Vault/owner acceptance: NOT_TESTED
```
