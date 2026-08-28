# Task 6L — Durable Lease Ownership Receipt

Date: 2026-08-28 (Asia/Shanghai)
Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
Base: `3fadc0996915d1e57e57f717f27b620df86318e6`
Product/tests commit: `4fd2386`

## 1. Status

```text
Task 6L: IMPLEMENTED_FOCUSED_PASS
Task 6M: FAIL / BLOCKED_AT_REPAIR_CAP (historical disposition unchanged)
Task 6: IN_PROGRESS / NOT_ACCEPTED
Task 6V packaged 30/70: DEFERRED
live / Artifact / release / Production / Vault / owner acceptance: NOT_TESTED
```

Task6L is a new bounded architecture completion after Task6M's repair cap. It
does not reopen or relabel Task6M and adds no user-facing capability or second
authority.

## 2. Implementation

- `extraction_jobs.last_claim_lease_fingerprint` is a nullable, idempotent
  compatibility migration. Successful claim writes SHA-256 of the existing
  random lease token in the same SQLite transaction. Complete, fail, release,
  cancel and stale release clear only current lease fields; the latest claim
  fingerprint survives. Retry and forced terminal re-enqueue clear the old
  generation receipt before a new claim.
- The queue's internal `ownership_receipt()` returns only status, input path,
  worker timing and boolean ownership results. Normal service/MCP DTOs remove
  plaintext `lease_token` and durable fingerprint fields.
- v1 transient reconciliation hashes the marker lease segment and requires
  durable fingerprint plus same-directory content-addressed raw hard-link
  identity. Running entries additionally require current lease equality.
  Terminal/queued/retrying/dead/expired wrong-lease, NULL-fingerprint and old
  generation markers remain preserved. Legacy UUID markers retain Task6M's
  strict raw proof.
- Root checks, directory iteration, lstat, raw hashing/open, queue reads and
  unlink are fail-closed at the reconciliation boundary. Receipts contain only
  stable allowlisted reason codes and generic counts; no exception text, path,
  marker name, job ID, lease or token is included. Existing pipeline/worker/
  runtime cleanup pending retry remains the observation path.
- Existing rendered Desktop owner flow now drives cleanup pending on and off,
  checks the generic Chinese retry notice, and asserts no fixture secret or
  error detail reaches the DOM. No new page/API was added.

## 3. TDD and verification evidence

RED was observed before implementation:

```text
tests/test_task6l_durable_lease_receipt.py: 8 failed
```

GREEN and regression results:

```text
./.venv/bin/python -m pytest -q tests/test_task6l_durable_lease_receipt.py
11 passed

./.venv/bin/python -m pytest -q tests/test_task6l_durable_lease_receipt.py tests/test_task6m_transient_lifecycle.py tests/test_automatic_memory_runtime.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py tests/test_automatic_memory_scheduler.py tests/test_task6h_heartbeat.py tests/test_task6s_source_authority_versions.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_fact.py tests/test_task8_work_transition_matrix.py tests/test_structured_evidence_lexical.py tests/test_structured_ingestion.py
218 passed, 2 warnings

cd desktop/lingji-control && npm run test:memory-sources-repair
PASS
cd desktop/lingji-control && npm run test:memory-sources
PASS
cd desktop/lingji-control && npm run build
PASS (tsc/vite; existing dynamic-import warnings)
cd desktop/lingji-control && npm run test:e2e:memory
PASS (rendered cleanup_pending notice appears and disappears)

./.venv/bin/python -m compileall -q src tests/test_task6l_durable_lease_receipt.py tests/test_task6m_transient_lifecycle.py
PASS
git diff --check
PASS
./.venv/bin/python scripts/check_acceptance_sync.py
PASS
./.venv/bin/python scripts/check_local_execution_handoff.py
PASS
```

## 4. Scope, cleanup and limitations

All tests used pytest temporary roots or the existing Desktop fake server. No
live 8766/8767 service, Artifact, release build, Production data, configured
Vault, owner data or credentials were accessed. No persistent acceptance
fixture, process or port was intentionally left running.

The packaged 30%/70% crash/restart/stop gate remains a separate Task6V task and
was not rerun. This report does not claim a release, Artifact, real-machine,
Production/Vault or owner acceptance result. Task6M's final review remains
`BLOCKED_AT_REPAIR_CAP` and is not modified.

## 5. Changed files

Product/tests commit `4fd2386`:

```text
src/extraction/queue.py
src/extraction/transient.py
src/control/service.py
src/mcp/extraction_submission.py
tests/test_task6l_durable_lease_receipt.py
tests/test_task6m_transient_lifecycle.py
desktop/lingji-control/tests/e2e_owner_memory_flow.mjs
```

Documentation synchronization is in the follow-up docs/report commit and
updates the existing phase-1 plan, project status, code map and acceptance
change log. `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` remains `IDLE`.
