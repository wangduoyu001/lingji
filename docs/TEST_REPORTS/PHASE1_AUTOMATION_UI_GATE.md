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

Clean-run final persisted counts: StateDB sources `4`, queued `0`; structured
source/conversation/message/memory `4/4/4/0`; duplicate counts
`0/0/0/0`. The run saved `logs/packaged.stdout.log` and
`logs/packaged.stderr.log`, PID/port/child inventory, and a cleanup receipt with
port rebind verified. Temporary roots were removed after evidence extraction.

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
