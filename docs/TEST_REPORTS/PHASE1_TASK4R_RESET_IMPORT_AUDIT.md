# Phase 1 Task 4R-Reset Task 2 — Stable Import Audit

## Scope

Base: `597df6711f5e0584fccd6991065177f111bc3746`
Product commit: `9a942d3` (`fix: separate import identity from content dedup`)

This change implements only the batch-scoped stable import audit, intentional content-hash groups, and the quality-harness read-only persisted-message matcher. Fixture labels are no longer written to imported source rows or candidate metadata. Task 3 selector/identity registry, Task 4 readiness, Task 5 promotion state machine, Task 6 runner reset, 4R2, scale, Artifact, Production, Vault, and owner acceptance remain deferred.

## Authentic RED

Before product changes, the required focused command was run:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_automatic_memory_gate_integrity.py
```

Result: collection failed with `ImportError: cannot import name 'ContentHashGroup' from src.automatic_memory.quality_evidence`. This was the expected missing-new-contract failure; no production implementation was present before the RED run.

## GREEN and regression evidence

Focused GREEN:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_automatic_memory_gate_integrity.py
20 passed in 0.55s
```

Task 1 regression:

```text
./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py tests/test_capture_service.py
64 passed in 0.63s
```

Direct quality-evidence caller coverage:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py
14 passed, 3 failed, 1 warning
```

The three failures are deliberately retained historical rejected-test incompatibilities: old positional `ExpectedImportedRow` construction, old positional/`list_messages()` audit invocation, and the rejected runner's sentinel/readiness expectation. They are deferred to Task 6 migration; no compatibility aliases were added to weaken the new contract. The current end-to-end caller itself passes.

## Frozen Generic History import audit

The real frozen corpus pipeline persisted one explicit ingestion batch and was audited through `list_ingestion_messages()` only:

```text
expected_rows=145
actual_rows=145
ordered_external_key_matches=145
role_matches=145
sequence_matches=145
timestamp_matches=145
content_hash_matches=145
source_matches=145
conversation_matches=145
stable_duplicates.total=0
intentional_content_hash_groups=5
```

Each intentional group has two distinct composite external identities, and corpus-only fact/citation identity checks remain distinct. The audit is read-only; the adversarial snapshot test includes `fixture_*` metadata and proves it is unchanged. Equal content is therefore recorded as an intentional group, not a stable duplicate.

Frozen fixture hashes were unchanged:

```text
bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94  tests/evaluation/fixtures/automatic_memory_corpus.jsonl
338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612  tests/evaluation/fixtures/automatic_memory_questions.jsonl
```

No current quality PASS or frozen acceptance verdict is claimed; Task 4 evidence is incomplete and later reset tasks own the remaining gate.

## Repair round 1

Repair base: `5839fc329a7790da0256809723509c8c5a59407c`
Repair product commit: `81b1c8d` (`fix: harden composite import audit identity`)

Authentic repair RED, before repair product edits:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_automatic_memory_gate_integrity.py
8 failed, 22 passed
```

The eight failures covered composite matcher API/ambiguity, empty message primary ID readiness, malformed pagination totals/offset/limit/progress, and the non-progressing empty page. Repair GREEN:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_automatic_memory_gate_integrity.py
30 passed in 0.81s
```

The matcher now binds corpus records to expected rows by evaluation-only fact ID and resolves exact `(source_external_id, conversation_external_id, message_external_id)` keys; duplicate expected or persisted composite bindings fail closed. Empty internal source/conversation/message IDs cannot satisfy readiness. Shared ingestion pagination validation rejects total drift, echoed offset/limit mismatch, overrun, final count mismatch and non-progress.

The frozen 145-row test replays the same execution ID and proves the second audit remains `145/145`, all seven counters `145`, stable duplicates `0`, groups `5`, primary message IDs unchanged, and source/conversation/message counts unchanged.

## Verification and cleanup

```text
python -m py_compile ...quality_evidence.py ...quality_gate.py ...__init__.py ...test_task4_reset_import_audit.py ...test_automatic_memory_gate_integrity.py  PASS
git diff --check  PASS
python scripts/check_acceptance_sync.py  PASS
python scripts/check_local_execution_handoff.py  PASS
```

Tests use temporary SQLite/storage/vault roots only. No Production or owner Vault data was accessed or modified. `LOCAL_EXECUTION_TASK.md` remains `IDLE`; no Artifact, 100k, 4R2, or physical acceptance was run.

## Known limitations and rollback

- Historical Task 4R1 RED files remain intentionally incompatible with the exact Task 2 API and are not deleted or skipped.
- The old fixture-label selector helpers remain for the later Task 3 migration boundary; this task removes fixture metadata writes from the import/promotion path only.
- Rollback is the product commit `9a942d3` and this documentation commit; no owner data or Production/Vault state is involved.
