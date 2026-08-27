# Phase 1 Automation and UI Gate — Task 6

Status: `IN_PROGRESS / NOT_ACCEPTED`

This is the sole Task 6 evidence authority. It is Acceptance-only evidence from
temporary roots; it is not Artifact, release, live 8766/8767, Production/Vault,
or owner acceptance.

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
| 5 30%/70% crash + restart | Implemented as real sidecar kill at persisted progress barrier; records scan_id, progress/total, snapshot and scheduler lease owner/expiry, exact recovered scan, terminal source/scan/job/raw/structured identity sets and counts. Latest exploratory run reached terminal states but was interrupted before a publishable matrix receipt; final Task6 remains NOT_ACCEPTED. |
| 6 pause/resume/revoke/expiry | PASS in clean run: paused/resumed states persisted; expiry returned source `expired` and truthful incomplete report; revoke returned `revoked` and disabled source jobs. |
| 7 corrupt isolation | PASS: corrupt source scan terminal with extraction job `failed`; healthy source scan terminal with extraction job `completed`; source identities isolated. Work Fact identity is bound to each scan. |
| 8 Qdrant unavailable + lexical fallback | BLOCKED: formal semantic-client failure injection and orchestration run, but packaged automatic-memory ingestion produces raw/structured read-model rows and no formal lexical `memory_documents`. The only available lexical hit is a pre-seeded Vault fixture and is explicitly rejected as self-proof. No retrieval/design change is authorized. |
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

## Heartbeat and limitations

Heartbeat is `NOT_MEASURED/BLOCKED`: `/api/automatic-memory/runtime` truthfully
reports `scheduler_heartbeat_age=null` with the existing unavailable reason.
Work Fact `updated_at` and terminal timestamps are not substituted for a live
heartbeat. A separate Task6H brief is required to add a trustworthy measured
source before this gate can pass.

The packaged two-clean-root command, rendered Desktop memory E2E, Task2–5
regressions, compileall, diff-check, acceptance sync and local handoff remain
required before any future acceptance claim. Any skipped or blocked core
scenario is failure; this report makes no release or owner-acceptance claim.
