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

## Repair round 1 evidence

Repair base: `75b691b9b2f9ce2d65023db87b25fab7018d9f2b`.

The required adversarial probes were added before repair implementation. Authentic RED:

```text
./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py tests/test_capture_service.py
11 failed, 53 passed
```

The failures demonstrated the four review/root defects: migration DDL/index state survived an injected failure, fresh v2 marker survived incomplete initialization, the direct CaptureService sink double rejected the new kwargs (`links == 0`), malformed/invalid ordinal inputs escaped the read-model error contract, and a batch beginning at ordinal 1 was accepted.

Repair product commit: `f105bbf7fb1a96a078ccbbf71f440d3d6b1e5e68` (`fix: harden ingestion migration and validation`).

Repair GREEN:

```text
./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py tests/test_capture_service.py
64 passed in 0.59s
```

Prior regressions after repair: `111 passed, 2 warnings in 7.20s`. Repair added an explicit outer transaction plus nested migration savepoint, removed implicit `executescript()` transaction behavior, rejects non-negative ordinal starts unless exact integers, validates SQLite ordinal types as `SourceReadModelError`, requires complete batches to equal `0..N-1`, and updates the direct sink test double. Independent re-review and root verification remain required; Task 1 is not declared accepted.

## Cleanup and rollback

All tests used temporary SQLite/pytest paths only. No owner data, Production, Vault, Artifact or frozen fixture was modified. Rollback is the two Task 1 commits; no destructive cleanup was performed.
