# Phase 1 Product Landing — Task 3 Repair Round 2 FINAL Report

Date: 2026-08-27
Branch: `codex/phase1-automatic-memory`
Base: `3edbfc8`
Product/test commit: `7058da0`
Evidence artifact commit: `b83232d`

## Verdict

`IMPLEMENTED_FOCUSED_PASS` for the four final Task 3 Repair Round 2 findings, subject to synthetic/local verification only. No live 8766, Artifact/release, Production, configured Vault, owner data, or UI acceptance was performed.

## TDD evidence

The five focused tests were added before implementation. The exact behavioral RED command was:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round2.py --tb=short
5 failed in 0.75s
```

The failures covered CRLF/BOM frontmatter denial, cross-source Generic AI History identity persistence, 30% and 70% pause/resume Work Fact counts, and the required Round 1 three-commit attribution. No existing tests were deleted, weakened, skipped, or replaced.

## Repairs

### CRLF/BOM bounded frontmatter

The Obsidian scope reader now recognizes exactly `---\n` and `---\r\n`, with or without UTF-8 BOM, before reading bounded frontmatter lines. It retains the 8192-byte cap, fails closed for malformed or unclosed frontmatter, preserves `lingji_memory: false` precedence, and does not consume body sentinels.

### Automatic Generic AI History source namespace

For requests marked `options["automatic_memory"]`, Generic AI History identity material is namespaced by the already-authorized payload `source_id`. Same-source replay remains stable and idempotent; distinct authorized sources with identical bytes persist separate structured source, conversation, and message rows with source provenance. Requests without the automatic-memory option retain the existing direct/manual identity behavior.

### Pause/resume Work Fact counts

Runtime Work Fact projection now waits for the durable scan to be terminal and uses the completed scan's truthful `total`/`progress` (or existing reconciliation `discovered`) instead of reducing a resumed scan to only newly queued/reused rows. The existing queued/reused evidence remains unchanged, and terminal scan reports are still released from `_scan_reports`.

### Round 1 evidence identity

The authoritative Round 1 report and acceptance entry now explicitly identify product/test `f2f7312`, evidence artifact `4e5d744`, and metadata correction `95cfc90`.

## Verification

Focused final repair tests:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round2.py --tb=short
5 passed in 0.86s
```

Task 3 repair and directly affected source tests:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round2.py tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_snapshot.py tests/test_extraction_worker.py tests/test_extraction_idempotency.py tests/test_automatic_memory_adapters.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py tests/test_obsidian_memory_scope.py tests/test_structured_ingestion.py --tb=short
223 passed, 7 warnings in 14.83s
```

The historically disclosed Task 2 scheduler timing boundary passed in this run and remains unchanged; it is not credited as repaired. The two warning categories are existing HTTPX/Starlette and Pydantic/deprecation or fixture warnings.

Additional gates:

- `./.venv/bin/python -m compileall -q src tests/test_automatic_memory_repair_round2.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py`: pass.
- `git diff --check 3edbfc8..HEAD`: pass after the final docs artifact and metadata update.
- `./.venv/bin/python scripts/check_acceptance_sync.py`: pass.
- `./.venv/bin/python scripts/check_local_execution_handoff.py`: pass; `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## Changed files

Product/test commit `7058da0`:

- `src/automatic_memory/runtime.py`
- `src/extraction/adapters/generic_ai_history.py`
- `src/obsidian/memory_scope.py`
- `tests/test_automatic_memory_repair_round2.py`

Evidence/docs artifact:

- `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-1-report.md`
- `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-2-report.md`
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/PROJECT_STATUS.md`

## Boundaries and limitations

- No live 8766 service, Artifact/release build, real UI, owner observation, Production/Vault data, cloud, or external software mutation.
- No automatic promotion seam was invoked or enabled: `evaluate`, `promote`, `submit`, `reconcile_incomplete_projections`, and `rebuild_derived_projections` remain forbidden.
- No Task 2 lifecycle/timing repair, Vault publishing, retrieval/vector, quality, release, 100k, UI, second parser/store/queue/API/indexer, or new product feature was added.
- This is the final permitted Task 3 repair; any remaining Important finding blocks Task 3 and requires a boundary re-plan. No third repair was performed.
