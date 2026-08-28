# Phase 1 Automation and UI Gate — Task 6

Status: `IN_PROGRESS / NOT_ACCEPTED`

This is the sole Task 6 evidence authority. It is Acceptance-only evidence from
temporary roots; it is not Artifact, release, live 8766/8767, Production/Vault,
or owner acceptance.

The historical interim sections below retain their original timestamps and
pre-closeout dispositions; the Task 6C closeout at the end is the current
authority for the final automated status and raw crash receipts.

Task6C Repair Round 1 is currently blocked by the fresh failure recorded at the
end of this report; the earlier Task6C PASS text is retained as historical
evidence only and is superseded by that disposition.

## Identity and bounded repair

- Base: Task 6A final review `22aae07be9accf7d56a4273e8d45a521b2323dab`, accepted for Task 6.
- Diagnostic review: `361733b3c660e1b5dc36e5500e1f2436da41572e`; this is Task 6 Repair Round 1, not Task 6A.
- Product/test commits: `04eb1d3` (durable scan identity), `b6e8c77` (reconciliation event identity), `31f40a3` (packaged evidence harness).
- The test launches `run_packaged_control_api.py` and drives the authenticated loopback API. Every wait binds source + durable scan identity + trigger reason; no list-first fallback remains.
- Acceptance env sets existing `LINGJI_EXTRACTION_STALE_AFTER_SECONDS=30` and the settings-equivalent `EXTRACTION_STALE_AFTER_SECONDS=30`; no production default or DB lease is modified.

## RED and focused evidence

The required RED first failed with `AttributeError: ReconciliationReport.scan_id` in
the race/old-scan regression. After the bounded scheduler/runtime fix:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_runtime.py tests/test_automatic_memory_repair_round1.py
52 passed
./.venv/bin/python -m pytest -q tests/integration/...::test_qdrant_outage_uses_formal_retrieval_orchestration_with_lexical_fallback
1 passed (focused helper only; not Task 6 scenario 8 evidence)
```

One clean Acceptance root completed with the following raw persisted evidence
(the second fresh root is repeatability only; same-root idempotency is measured
inside each run):

| Scenario | Result and measured evidence |
|---|---|
| 1 metadata-only discovery/body-read guard | PASS: 3 discovered metadata records; StateDB sources `0`, raw `0` before authorization. No body is opened by discovery. |
| 2 authorization + startup scan | PASS: exact scan/work identity; discovered `1`, queued `1`, structured source/conversation/message `1/1/1`, memory `0`; terminal queue `0`; Work Fact outcome `completed`, next actor `system`. |
| 2 same-root same-bytes idempotency | PASS: second exact scan report queued `0`, reused `1`; source/conversation/message/memory identity sets unchanged; duplicates `0/0/0/0`; raw SHA set unchanged. |
| 3 file event | PASS: watcher trigger reason `event`, exact durable scan identity, latency `0.124s` (`<=30s`). |
| 4 suppressed event / reconciliation | PASS: runtime pause then resume; no manual scan POST; production Cron reason `reconciliation`, exact scan identity, terminal after the legal 60-second scheduler floor. |
| 5 30%/70% crash + restart | PASS: two fresh rounds used 20-file clean roots, killed the actual sidecar PID at persisted 6/20 and 14/20 barriers within the explicit two-item batch window, and recovered the same durable scan through startup reconciliation. All four receipts completed 20/20 with 20 jobs and zero duplicates. |
| 6 pause/resume/revoke/expiry | PASS in clean run: paused/resumed states persisted; expiry returned source `expired` and truthful incomplete report; revoke returned `revoked` and disabled source jobs. |
| 7 corrupt isolation | PASS: corrupt source scan terminal with extraction job `failed`; healthy source scan terminal with extraction job `completed`; source identities isolated. Work Fact identity is bound to each scan. |
| 8 Qdrant unavailable + lexical fallback | PASS: packaged ingestion evidence was queried through formal orchestration with injected semantic-client failure; lexical hit and degraded diagnostics were both observed. No retrieval/design change was made. |
| 9 sleep/wake equivalent | PASS in clean run: mtime clock jump + process restart; startup reconciliation reason and exact scan identity terminal. |
| 10 recursive non-interference | PASS in clean run: third-party sentinel diff `{}`; Vault diff `{}` after explicit bootstrap-directory allowlist. Each sentinel records relative path, SHA-256, size, mtime_ns, mode and symlink target. |

### Task 6L lexical landing (Repair Round 1)

Task 6L product/test commit `5258ecef98e2b58dfb9c12af585a4fbd44c260dd` closes the
structured-evidence lexical projection gap using the existing `lingji_memory.db`
`memory_documents`/FTS path. Automatic source lifecycle transitions from StateDB are
projected through the existing SourceRegistry listener into read-model/evidence status;
revoke, expiry, and restart therefore fail closed for current Gateway, Hybrid, MCP and
ContextPack retrieval while history/as_of retains the raw/structured evidence. Generic
automatic source identity is stable across changed raw snapshots, so v1→v2 updates
replace one evidence projection and same-byte replay is idempotent. Raw citation,
message role and sequence are included in the formal evidence citation.

Focused repair evidence: lexical tests `9 passed, 1 warning`; focused aggregate `57
passed, 1 warning`; review matrices `46 passed, 2 warnings`, `36 passed, 1 warning`,
and `75 passed, 1 warning`; packaged Qdrant lexical helper `1 passed, 1 warning`.
These are Acceptance-only synthetic fixture results. They do not convert this Task 6
authority from `IN_PROGRESS / NOT_ACCEPTED`: Task 6H heartbeat, final crash matrix,
and independent Task 6 review remain outstanding, and no live service, Artifact,
Production/Vault, or owner acceptance was run.

Clean-run final persisted counts: StateDB sources `4`, queued `0`; structured
source/conversation/message/memory `4/4/4/0`; duplicate counts
`0/0/0/0`. The run saved `logs/packaged.stdout.log` and
`logs/packaged.stderr.log`, PID/port/child inventory, and a cleanup receipt with
port rebind verified. Temporary roots were removed after evidence extraction.

## Task 6S architecture re-plan (2026-08-28)

Task6L's fresh architecture re-plan is recorded in
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6s-report.md`.
Product/tests commit `5fb2966` injects the existing StateDB-backed
`SourceAuthorityResolver` into formal Gateway/Hybrid composition and retains
content-hash evidence versions in the existing `memory_documents` projection.
Task6S focused tests are `8 passed`; Task6L lexical tests remain `9 passed`.
This does not change this authority's `IN_PROGRESS / NOT_ACCEPTED` status: Task6H
heartbeat, packaged crash matrix, live/Artifact/owner acceptance and fresh
independent review remain outstanding.

Task6S Repair Round 1 product/tests commit `9692cf7` closes the three current
structured-evidence bypasses identified by independent review `1816d361`: current
and why Hybrid results are never served from a stale authority-unsafe cache;
active orphan projections are archived during the existing structured sync while
history is retained; and ContextPack linked raw-message evidence uses the same
batch StateDB resolver before append. Task6S remains `NOT_ACCEPTED` pending a fresh
review, Task6H heartbeat, and packaged crash evidence.

## Task 6H durable heartbeat

Task6H is an independent bounded observability closeout. The existing
`StateDatabase` now contains one mutable `automatic_memory_heartbeats` row per
scheduler `instance_id + generation`, with UTC `heartbeat_at`, lifecycle
`state`, `reason`, and `last_error`. The existing Cron scheduler thread invokes
the heartbeat callback at a bounded cadence (default at most 5 seconds), while
its reconciliation polling and SQLite claim cadence remain independent.

`/api/automatic-memory/runtime` reads that same durable source and returns
`scheduler_heartbeat_at`, computed UTC `scheduler_heartbeat_age`,
`scheduler_heartbeat_reason`, `scheduler_heartbeat_instance`, generation, state
and last error. Pause continues to refresh a `paused` heartbeat; clean stop
writes `stopped` and no longer updates. Future timestamps, stale age over 10s,
thread/write/read failures are degraded/fail-closed and recover on the next
successful heartbeat. A restarted runtime receives a new instance and never
reuses an old instance's running row. Active scans touch their existing Work
Fact `work_items.updated_at` directly without appending event rows; idle
heartbeats do not create Work Fact or event rows.

RED was reproduced by the new focused suite when heartbeat cadence/source was
absent (`3 failed`). GREEN is:

```text
./.venv/bin/python -m pytest -q tests/test_task6h_heartbeat.py
8 passed
```

Measured focused evidence: idle heartbeat age stayed `<=1s` with a `0.1s`
test cadence; the same instance row was updated in place; active Work Fact
event count did not change. Active touch/write failures now persist heartbeat
`degraded` with reason and last error, do not terminate scheduler/scans, and
recover on the next successful refresh; idle runtimes with no active Work Fact
do not report this failure. The Desktop DTO carries heartbeat timestamp,
instance, generation, state and last error, while source-page copy distinguishes
degraded/stopped/paused/running/unknown. With a `0.05s` heartbeat cadence and
the normal reconciliation poll set to 60s, a 0.25s run made one scheduler claim
(asserted `<=2`), demonstrating that heartbeat wakeups do not run
reconciliation at high frequency. Task2 lifecycle/API regression was `50
passed, 1 warning`; control / packaged API regression was `21 passed, 6
warnings`. The packaged crash 30/70 terminal scan identity mismatch is an
external Task6 gate and was not changed by this Task6H repair.

This does not change the authority's `IN_PROGRESS / NOT_ACCEPTED` status:
packaged crash matrix, full two-run evidence, live/Artifact/owner acceptance
and fresh independent Task6 review remain outstanding.

The packaged two-clean-root command, rendered Desktop memory E2E, Task2–5
regressions, compileall, diff-check, acceptance sync and local handoff remain
required before any future acceptance claim. Any skipped or blocked core
scenario is failure; this report makes no release or owner-acceptance claim.

## Task 6C final deterministic crash-recovery closeout (2026-08-28)

Task6C test-only commit `6eb469fefafe0a33e6ac65f765c7663741883811` corrected
the acceptance harness after a real RED of `1 failed, 1 passed, 1 warning`:
the prior `2 != 1` terminal identity assertion mixed the original crashed scan
with a later audit scan, killed a dummy process, and raced an unconditional
manual POST against startup reconciliation. The bounded harness now kills the
actual sidecar PID at a persisted progress/total barrier, waits for the
existing `run_on_start` lease recovery, records any bounded fallback, and
pauses immediately at the original terminal state.

Fresh full packaged gate runs (each includes both clean 30% and 70% roots and
all ten scenarios) were:

```text
2 passed, 1 warning, 265.89s
2 passed, 1 warning, 266.73s
```

The four raw crash receipts are:

| round | target | source_id | original scan_id | killed PID | recovery PID | barrier | terminal | fallback | jobs | duplicates |
|---|---:|---|---|---:|---:|---:|---|---|---:|---|
| 1 | 30% | `src-9d075cefb0ab4a3186bc869835794c23` | `scan-a5d21ae042164427a7dccbcddd72e37a` | 45100 | 45102 | 6/20 | completed 20/20 | false | 20 | 0 |
| 1 | 70% | `src-6b6131db26f5466aacf9a40f30a08ebc` | `scan-57b23a1429744ff89fe68bcf14c642f4` | 45108 | 45110 | 14/20 | completed 20/20 | false | 20 | 0 |
| 2 | 30% | `src-7403e7ca55304e309e9c5c296c73d898` | `scan-ca34a2632b1b420997343ea4463e0fd4` | 45117 | 45119 | 6/20 | completed 20/20 | false | 20 | 0 |
| 2 | 70% | `src-0342722c0e984a27b948eebce89e3460` | `scan-7eace87d949042b3b598c92b2f002686` | 45132 | 45134 | 14/20 | completed 20/20 | false | 20 | 0 |

All ten scenarios were raw `PASS` in both runs, including Task6S formal
lexical/Qdrant degradation evidence and Task6H heartbeat age `<=10s`. The
parity comparison used logical source/conversation/message/version/memory
identity sets, raw hashes, job identities/statuses, Work Fact outcome, queued
`0`, duplicate `0`, and original scan progress/total; random source and scan
IDs were not compared across roots. Runtime was paused at terminalization so
any subsequent periodic audit scan was counted separately, never as a domain
duplicate. Each root also verified PID/child/port/log/temp cleanup.

Regression evidence: Task6H/S/A plus scheduler/checkpoint/leases/cron/startup
recovery `155 passed, 2 warnings`; Desktop build, runtime/source/work-fact/
memory-review smokes, rendered memory E2E, compileall, `git diff --check`,
acceptance sync, and local handoff all passed. The only code commit in this
closeout is test-only; the companion report is
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6c-report.md`.

This status is automated Acceptance evidence only. It makes no release,
Artifact, live 8766/8767, Production/Vault, or owner acceptance claim.
`LOCAL_EXECUTION_TASK.md` remains `IDLE`; fresh independent security review is
still required.

## Task 6C Repair Round 1 disposition (current)

The fresh review `3fd8059da4ed10b8a1fcd0581793bd0fb2d177ee` supersedes the
historical closeout above. The first `-x` rerun failed after real sidecar crash,
startup recovery, terminal `20/20`, runtime pause, and recovery-sidecar stop:
`storage/raw/.automatic-memory-<random>.json` remained in the transient marker
inventory (`2,640,287` bytes). Existing `ConsistentSnapshot` cleanup does not
reclaim this marker. This is a product cleanup defect, not a safe parity-harness
adjustment; the attempted uncommitted harness repair was discarded.

Current authority is therefore `IN_PROGRESS / NOT_ACCEPTED` with I1 blocked.
I2–I6 are not claimed as accepted by this report. No product change, release,
Artifact, live service, Production/Vault, or owner acceptance is claimed.

## Task 6V packaged closeout (2026-08-28, current)

Task6R product HEAD `684398e2b56447203ff6b77b4e93cae2c07b38f2` adds terminal
snapshot-owned temporary cleanup through the existing `ConsistentSnapshot`
reconcile seam. Task6R focused lifecycle coverage is `6 passed`.

The existing packaged harness was tightened only in integration/acceptance
tests: transient marker inventory now classifies complete snapshot-owned names;
raw evidence is restricted to verified 64-hex content-addressed objects;
cross-root parity compares normalized natural identity/status sets plus message
and version hashes; cleanup receipts use measured child/PID/port evidence; and
crash recovery waits for the measured durable lease barrier before production
startup reconciliation. Desktop rendered readiness uses DOM load plus the
existing landing heading rather than `networkidle` because authenticated
polling keeps network activity open.

Fresh complete packaged invocations from independent temporary roots:

```text
./.venv/bin/pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short -x
2 passed, 1 warning, 294.47s
2 passed, 1 warning, 295.59s
```

Both invocations cover ten scenarios and 30%/70% real sidecar crash/restart;
the original durable scan reaches `20/20`, transient inventory is zero,
raw hashes and logical source/scan/job/Work Fact/structured identities have
exact parity, fallback is false, duplicate/queued counts are zero, and child,
port, log and temporary cleanup are measured. Packaged Gateway/Hybrid, formal
MCP/ContextPack, lexical semantic-degradation, revoke/expiry current
fail-closed, history/as-of, evidence version supersession, and heartbeat
instance/generation evidence pass. Focused Task6H covers active Work Fact
failure/degraded/recovery.

The Task6V focused matrix is `376 passed, 3 warnings`; Desktop build, runtime,
source/repair, Work Fact, memory-review smokes and rendered E2E pass. Compile,
diff, acceptance-sync and local-handoff checks pass. Current automated
disposition is `AUTOMATED_ACCEPTED / READY_FOR_TASK7` only. This does not claim
release, Artifact, live 8766/8767, Production/Vault, or owner acceptance;
`LOCAL_EXECUTION_TASK.md` remains `IDLE`.
