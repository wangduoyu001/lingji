# Task 6C — Deterministic Crash-Recovery Receipt

Status: `PASS_AUTOMATED / READY_FOR_TASK7` in the sole authority
`docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`.

This is an Acceptance-only bounded gate. It used isolated temporary roots and
real `run_packaged_control_api.py` sidecar subprocesses over random loopback
ports. It did not use Artifact, live 8766/8767, Production/Vault, owner data,
or owner acceptance.

## Scope and RED

The product baseline was Task6H accepted head `c1cd4453e407afc160e509c9fb1e165845577872`.
The test-only implementation is `6eb469fefafe0a33e6ac65f765c7663741883811`
(`test: make Task6 crash recovery receipt deterministic`). No product source
change was made for Task6C.

The required RED was reproduced before the bounded harness correction:

```text
tests/integration/test_automatic_memory_packaged_flow.py --tb=short
1 failed, 1 passed, 1 warning, 126.96s
AssertionError: terminal identity lengths 2 != 1
```

Diagnosis was a harness identity/race error: the old matrix mixed the crashed
scan with a later periodic audit scan, killed a dummy process, and unconditionally
POSTed a replacement scan after restart. It was not evidence of a product
duplicate. The final harness kills the actual sidecar PID at a persisted
progress/total barrier, waits for production `run_on_start` lease recovery,
uses manual POST only as a bounded fallback, and pauses immediately after the
original scan reaches terminal state.

## GREEN evidence

Two fresh complete packaged runs were executed:

```text
./.venv/bin/python -m pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short
2 passed, 1 warning, 265.89s
2 passed, 1 warning, 266.73s
```

Each run executes the ten scenarios and two clean crash roots (30% and 70%).
The raw scenarios were all `PASS`: metadata-only discovery; authorization and
startup scan; file event; suppressed-event reconciliation; 30%/70% crash
restart; pause/resume/revoke/expiry; corrupt-source isolation; Qdrant outage
with formal lexical fallback; sleep/wake equivalent; and recursive
non-interference. Task6S lexical/Qdrant evidence and Task6H heartbeat age
`<=10s` were asserted in the packaged flow.

The four dedicated fresh-root crash receipts below preserve the requested
actual identities and measured barrier. `fallback_used=false` means production
startup reconciliation recovered the original durable scan without manual POST.
Every root was removed after evidence extraction and cleanup verification.

| round | crash target | source_id | original scan_id | sidecar PID killed | recovery PID | kill progress/total | terminal | fallback | jobs | duplicates |
|---|---:|---|---|---:|---:|---:|---|---|---:|---|
| 1 | 30% | `src-9d075cefb0ab4a3186bc869835794c23` | `scan-a5d21ae042164427a7dccbcddd72e37a` | 45100 | 45102 | 6/20 | completed 20/20 | false | 20 | 0 |
| 1 | 70% | `src-6b6131db26f5466aacf9a40f30a08ebc` | `scan-57b23a1429744ff89fe68bcf14c642f4` | 45108 | 45110 | 14/20 | completed 20/20 | false | 20 | 0 |
| 2 | 30% | `src-7403e7ca55304e309e9c5c296c73d898` | `scan-ca34a2632b1b420997343ea4463e0fd4` | 45117 | 45119 | 6/20 | completed 20/20 | false | 20 | 0 |
| 2 | 70% | `src-0342722c0e984a27b948eebce89e3460` | `scan-7eace87d949042b3b598c92b2f002686` | 45132 | 45134 | 14/20 | completed 20/20 | false | 20 | 0 |

The kill barrier stayed within the explicit two-item batch window. Both roots
had identical logical terminal outcomes: source/conversation/message/version/
memory identity sets, raw content hashes, job natural identities/statuses,
Work Fact outcome, queued `0`, and duplicate counts `0`. The original durable
`scan_id` completed; no replacement scan took ownership. Any later periodic
audit was isolated by pausing runtime after terminalization and was not counted
as a domain duplicate.

## Regression and hygiene gates

```text
Task6H/S/A + scheduler/checkpoint/leases/cron/startup recovery: 155 passed, 2 warnings
Desktop build: PASS
Desktop runtime/memory-sources/work-fact/memory-review smokes: PASS
Rendered Desktop memory E2E: PASS (e2e_owner_memory_flow)
compileall: PASS
git diff --check: PASS
check_acceptance_sync.py: PASS
check_local_execution_handoff.py: PASS
```

The focused source-authority lexical fixtures use an explicit current UTC
timestamp so their existing temporal contract is deterministic; no production
default was changed. Process/port/log/temp cleanup receipts verified sidecar
exit, no child residue, log preservation, port rebind, and temporary-root
removal. `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

This report does not claim release, Artifact readiness, live service readiness,
Production/Vault safety approval, or owner acceptance. Fresh independent
security review remains required; no further repair is authorized in this gate.
