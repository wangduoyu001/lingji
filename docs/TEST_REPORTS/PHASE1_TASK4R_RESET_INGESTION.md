# Phase 1 Task 4R-Reset Task 1 — SourceReadModel ingestion order

## Scope and identity

- Task: Task 1 only, SourceReadModel ingestion-order contract.
- Base: `ec268045004647ae1187abe747e70f2e37bdce9f`.
- Product commit: `fde9059487cd549c14938f547d07ee2bdef54784` (`feat: add ingestion order evidence contract`).
- Documentation commit: recorded by the follow-up docs commit.
- Out of scope: Tasks 2–6, evaluator/fixtures/thresholds, retrieval, Task 4R2, 100k, Artifact, Desktop, Production, Vault and physical acceptance.

## Implemented contract

- Added immutable, exact, case-sensitive `ExternalMessageKey` and `ResolvedMessageRef`, exported from `src.sources`.
- Added SourceReadModel schema v2 with nullable ingestion batch/ordinal fields and deterministic index; v1 migration is additive, transactional and leaves old rows NULL; unknown versions fail closed.
- Added batch-scoped ordinal assignment and replay-safe stable-row updates. Legacy no-batch upserts preserve an existing owner/ordinal.
- Structured sink now passes one execution batch ID and threads the next ordinal across every structured source.
- Added complete-batch validation and exact-field `list_ingestion_messages()` pagination without content, metadata, privacy or credentials; existing newest-first `list_messages()` shape remains unchanged and hides batch fields.

## TDD evidence

Tests were modified/created before product implementation. Authentic RED command:

```text
./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py
```

RED result:

```text
ERROR collecting tests/test_task4_reset_ingestion_order.py
ImportError: cannot import name 'ExternalMessageKey' from 'src.sources'
```

The failure was caused by the missing Task 1 API; no product implementation existed at that point.

## Verification results

| Command | Result |
|---|---|
| Focused Task 1 tests | `30 passed in 0.50s` |
| Required regression tests | `111 passed, 2 warnings in 6.44s` |
| Fixture corpus SHA-256 | `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94` |
| Fixture questions SHA-256 | `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612` |
| `git diff --check` | PASS |
| `scripts/check_acceptance_sync.py` | PASS (`product-impacting files: 0` after product commit) |
| `scripts/check_local_execution_handoff.py` | PASS |

Warnings are pre-existing: a duplicate synthetic ZIP member warning and a Pydantic class-based-config deprecation warning. No Artifact, UI, Production/Vault, 4R2, 100k or physical acceptance was run.

## Cleanup and rollback

All tests used temporary SQLite/pytest paths only. No owner data, Production, Vault, Artifact or frozen fixture was modified. Rollback is the two Task 1 commits; no destructive cleanup was performed.
