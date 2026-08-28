# Task 6L Independent Review — Durable Lease Ownership Receipt

- Date: 2026-08-28 (Asia/Shanghai)
- Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Reviewed HEAD: `880bd8c1beeddfda0b0c76752038ca7da521adfe`
- Product/tests: `4fd2386`, `382091b`
- Prior context: `3fadc09`, `task-6m-final-review.md`
- Scope: read-only product/test review; only docs are deliverables

## Verdict

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Task 6L: NOT_ACCEPTED
Task 6: IN_PROGRESS / NOT_ACCEPTED
Critical: 0
Important: 1 (I1)
Minor: 0
Disposition: one bounded Repair Round 1 required
Task6M: FAIL / BLOCKED_AT_REPAIR_CAP (unchanged)
```

Task6L closes durable ownership proof, strict transient cleanup identity, and
receipt redaction for the formal Control/MCP/UI paths. It does not satisfy the
explicit requirement that ordinary queue reads hide plaintext lease tokens and
durable fingerprints: low-level `get()` and `list()` still return both fields.

## Fresh verification

All commands ran against the exact reviewed HEAD. No product or test file was
modified.

```text
Task6L + Task6M/runtime/snapshot/resume/queue/worker/scheduler/6H/6S/Task8/structured regression:
218 passed, 2 warnings
Task6L focused subset: 11 passed
Desktop test:memory-sources-repair: PASS
Desktop test:memory-sources: PASS
Desktop build (tsc/vite): PASS (existing dynamic-import warnings)
Desktop rendered test:e2e:memory: PASS
compileall: PASS
git diff --check 3fadc09..HEAD: PASS
check_acceptance_sync.py: PASS
check_local_execution_handoff.py: PASS
```

## Requirement matrix

| Requirement | Result | Evidence |
|---|---|---|
| Nullable old-DB migration/idempotence/default-null | PASS | Focused migration test and static `_ensure_columns` review |
| Claim + SHA-256 receipt same transaction | PASS | `BEGIN IMMEDIATE`, claim update and digest assertion |
| Claim failure no receipt; concurrent single winner | PASS | Conditional update/rollback; two queue-instance thread probe: one claim, one `None` |
| Complete/fail/release/release-stale/cancel semantics | PASS | Focused and affected queue/worker lifecycle matrix |
| Retry/force/re-enqueue/generation cannot authorize old marker | PASS | Reset tests; old generation marker survives new claim |
| Ordinary queue `get/list/stats` hide lease material | **FAIL — I1** | `get/list` expose both fields; `stats` is safe |
| Control API/Capture/MCP/logs/Work Fact/Desktop hide lease material | PASS for tested public paths | Public DTO wrappers and rendered DOM checks |
| Minimal parameterized internal ownership API | PASS | `ownership_receipt(job_id, fingerprint)`, `WHERE job_id = ?`, booleans/timing/path only |
| Strict job + marker hash + raw hardlink proof | PASS | SHA-256 marker, durable receipt, direct-child content-addressed raw identity |
| Wrong lease same inode terminal/queued/retrying/running preserved | PASS | Fresh four-status probe: all four preserved as `lease_mismatch` |
| Matching released/terminal delete; NULL preserve | PASS | Fresh matching probe removes; NULL fingerprint gives `lease_unverifiable` |
| Dead/expired, same-raw multi-job and reclaim isolation | PASS | Existing lifecycle suite and fresh affected regression |
| Root/iterdir/lstat/open/hash/queue/unlink Exception failures | PASS | Fresh secret-path probes return generic receipt and preserve safely; no new BaseException catch |
| Allowlisted, path/name/job/lease/token-free receipt | PASS | `PermissionError('/private/secret/token=abc')` probe produces reason/count only |
| Pipeline/worker/runtime degraded + recovery | PASS | Runtime regression and rendered notice appears/disappears |
| Legacy/TOCTOU/raw/source/Vault safety | PASS | Legacy hardlink, identity swap, SIGKILL/restart, raw hash tests; no live/Vault data |
| Rendered UI cleanup pending and fixture DTO consistency | PASS | Fake-8766 rendered flow drives on/off notice and DOM redaction |
| No second DB/queue/fact source or scope expansion | PASS | Existing queue column and bounded reconciliation only |

## I1 — Ordinary queue reads expose lease token and fingerprint

**Severity:** Important; blocks Task6L acceptance.

`_SQLiteExtractionQueueBase.get()` and `.list()` return `_parse_row()` from
`SELECT *` (`src/extraction/queue.py:525-547`), including
`lease_token` and `last_claim_lease_fingerprint`. `list_page()` and
`get_by_idempotency_key()` have the same raw shape. Control `jobs/job/status`,
Capture DTOs and MCP `durable_job_response` strip these keys, but ordinary queue
reads remain unsafe under the locked Task6L requirement.

Fresh probe against a claimed temporary job:

```text
queue.get():  ["last_claim_lease_fingerprint", "lease_token"]
queue.list(): ["last_claim_lease_fingerprint", "lease_token"]
queue.stats(): []
```

Expected: ordinary queue projections expose public job facts only; lease
material stays in worker/pipeline internals and the minimal ownership predicate.
Actual: direct queue reads expose both plaintext and durable lease material.

Required repair boundary: provide a clearly private raw-read seam for worker
lease operations and make ordinary `get`, `list`, `list_page` and equivalent
queue projections omit both fields, including nested public projections where
applicable. Preserve worker claim/complete/fail behavior; add direct queue and
API/MCP regressions. Do not add another queue/database or weaken ownership.

## Security and scope

- No live 8766/8767, release, Artifact, Production/Vault, owner data or real
  credentials were accessed. `LOCAL_EXECUTION_TASK.md` remained `IDLE`.
- The Desktop fake server used a fixture token only for local authenticated test
  calls; rendered body excluded `secret` and `cleanup_scan_failed`.
- Product/tests remain unchanged after verification. Task6M remains
  `FAIL / BLOCKED_AT_REPAIR_CAP`; this review does not reopen it.

## Final disposition

```text
Reviewed HEAD: 880bd8c1beeddfda0b0c76752038ca7da521adfe
Product/tests: 4fd2386, 382091b
Verdict: FAIL / NEEDS_FIXES
Task 6L: NOT_ACCEPTED
Critical: 0
Important: 1 (I1 ordinary queue get/list leak)
Minor: 0
Repair authorization: one bounded Repair Round 1 only
Task 6: IN_PROGRESS / NOT_ACCEPTED
```
