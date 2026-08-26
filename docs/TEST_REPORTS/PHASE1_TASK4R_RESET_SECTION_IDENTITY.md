# Phase 1 Task 4R-Reset Task 3 — Typed ContextPack Section Identity

## Scope and boundary

- Base: `24a0920414508e29cabda262bd68e120c9c880fe`
- Product commit: `42963167b4ea925152d15a1ff5d782ac5e038bb9`
- Scope: typed in-memory `MessageIdentity`/section identities, immutable evaluation registry, expectation-blind ContextPack selector, and real quality-Gateway integration.
- Explicitly not run or changed: Task 4 readiness, Task 5 promotion state machine, Task 6 runner reset/4R2, 100k, Artifact, Production, Vault, retrieval query/ranking/filter tuning, frozen evaluator/questions/fixtures/thresholds, or physical acceptance.

## Authentic RED

Before product implementation, the required focused command was run against the base after creating the new test and before creating `evidence_identity.py`:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_automatic_memory_end_to_end.py
ERROR collecting ...test_task4_reset_section_identity.py
ModuleNotFoundError: No module named 'src.automatic_memory.evidence_identity'
1 error during collection
```

This was the expected missing typed API failure, not a fabricated assertion or skipped test.

## GREEN and regression evidence

Focused command:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_automatic_memory_end_to_end.py
13 passed, 1 warning in 2.86s
```

Task 3 regression command from the brief:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_automatic_memory_gate_integrity.py tests/test_automatic_memory_context_pack.py tests/test_permanent_memory_gateway.py tests/test_automatic_memory_mcp.py tests/test_mcp_server.py
58 passed, 1 warning in 1.27s
```

The warning is the existing Pydantic class-based-config deprecation. No test was skipped, deleted, weakened, or relabeled.

Coverage includes all three memory section kinds without message IDs; raw full identity, missing/mismatched/hash/unknown/contradictory identities; duplicate canonical sections; memory-plus-linked-raw citation enrichment; distinct-fact limits and validation beyond the limit; malformed packs and invalid limits; unknown/conflicting promotion bindings; immutable registry maps; and expectation mutation isolation. The quality end-to-end path builds one registry after import/promotion and selects real Gateway/MCP sections with the typed selector.

## Frozen inputs and checks

```text
automatic_memory_corpus.jsonl
bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94

automatic_memory_questions.jsonl
338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

The questions hash above is recorded from the repository authority and must be re-read by the root agent; the implementation does not modify either frozen file. `git diff --check` passed. `scripts/check_acceptance_sync.py` passed after the acceptance log entry, and `scripts/check_local_execution_handoff.py` passed (`LOCAL_EXECUTION_HANDOFF: PASS`).

## Historical compatibility boundary

`tests/evaluation/test_task4r1_takeover_red.py` and `test_task4r1_round5_final_red.py` still reference the rejected `build_prequery_identity_map`/`select_gateway_evidence` helpers. They are intentionally left as visible historical incompatibilities for Task 6 migration, per the brief; no compatibility aliases were retained.

## Limitations and workspace state

- Quality evidence remains an automated focused measurement only; no real Production/Vault or owner acceptance was attempted.
- The docs commit SHA is the commit carrying this report and acceptance-log entry; root should record it from `git rev-parse HEAD` after commit.
- Final clean-tree evidence must be taken after the docs commit and local ignored report write.

## Repair round 1 (product `db9e26e`)

Independent review found five Important defects and one explicit Minor. Before repair, new adversarial tests produced authentic RED:

```text
focused: 5 failed, 19 passed, 1 warning
```

The repair requires the real production raw citation mapping and exact equality for all five identity fields, rejects contradictory composite representations, calls the typed selector once per Gateway question while leaving MCP parity `NOT_MEASURED`, preserves citation IDs using the corpus citation set, and rejects surrounding whitespace in canonical kind/identity strings. Additional tests cover limits 0/1/2, enrichment/order, validation beyond limit, unknown/contradictory links, >200 rows, all-question expectation mutation, and read-only fixture-label snapshots.

After repair:

```text
focused: 25 passed, 1 warning
brief regression: 58 passed, 1 warning
historical deferred Task4R1 pair: 5 failed, 10 passed, 1 warning
```

The historical failures are expected rejected old-selector/API/readiness incompatibilities and remain deferred to Task 6. The existing Pydantic class-based-config deprecation warning remains. Frozen corpus/questions were unchanged; hashes remain the values recorded above. Product commit: `db9e26e`; docs commit: recorded by `git rev-parse HEAD` after this report update.

## Repair round 2 (product `c724ec9`)

Repair Round 2 addressed independent review I6/I7 and M2. The added adversarial suite first produced RED (`7 failed, 25 passed, 1 warning`); after correcting the test's SourceReadModel page size, the real storage assertion exposed fixture-driven supersession data in MemoryDatabase relationships. The runner now rejects unknown selector fact/citation IDs before scoring and publication, validates every populated internal/external/corpus composite representation as three exact strings without normalization, and leaves lifecycle replacement writes to the real application workflow rather than the fixture evaluator.

```text
focused: 32 passed, 1 warning in 7.65s
brief regression: 58 passed, 1 warning in 1.11s
historical deferred Task4R1 pair: 5 failed, 10 passed, 1 warning
```

The real temporary import/promotion snapshot queries SourceReadModel messages, MemoryDatabase document relationships and StateDatabase candidate metadata; no fixture/evaluator IDs, `fixture_*` keys, expected/forbidden labels or fixture lifecycle overrides appear in those persisted metadata/relationship fields. Frozen fixture hashes remain unchanged. Product commit: `c724ec9`; docs commit: recorded by `git rev-parse HEAD` after this update.

## Repair round 3 (product `b2e2bfa`)

Repair Round 3 addressed independent review I8: the real import/promotion path previously persisted frozen `fact_id` values as production memory identities and bound those same labels into the registry. Before the product change, the new real-storage test produced authentic RED:

```text
focused: 1 failed, 32 passed, 1 warning
```

The test keeps the real `run_quality_gate()` import/promotion path, introspects every table and persisted column/value in the temporary SourceReadModel/MemoryDatabase/StateDatabase SQLite stores, rejects every frozen fact/citation label and evaluator-only structural marker, and positively requires non-empty derived documents, message-memory links, active promotion events, and an in-memory opaque-to-fact registry bridge. User-authored message bodies are retained as evidence; evaluator-marker assertions exclude only body fields and FTS content projections so legitimate prose discussing a marker is not misclassified as metadata.

The minimal repair derives `LJ-MEM-<sha256 hex>` IDs from production source/conversation/message/content-hash inputs, passes those IDs through `ReviewCandidate`, real derived projection writes, links, and StateDatabase events, and passes the in-memory `{opaque_memory_id: fact_id}` bridge to `build_identity_registry`. The fixture-named extractor version was replaced with the neutral `automatic-memory-v1`; no generic promotion state machine or retrieval behavior changed.

```text
focused GREEN: 33 passed, 1 warning
brief regression: 58 passed, 1 warning
historical deferred Task4R1 pair: 5 failed, 10 passed, 1 warning
```

Frozen fixture hashes remain unchanged:

```text
bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94  tests/evaluation/fixtures/automatic_memory_corpus.jsonl
338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612  tests/evaluation/fixtures/automatic_memory_questions.jsonl
```

`py_compile`, cumulative `git diff --check`, acceptance sync and local handoff checks pass after the docs commit. No frozen fixture/evaluator/threshold, retrieval ranking/query/filter/order, Task 4–6/4R2, MCP parity, 100k, Artifact, Production, Vault or local acceptance task was entered. The only unresolved items are the deliberately deferred historical Task4R1 incompatibilities and the existing Pydantic deprecation warning.

## Repair round 4 (product `bea44958440a5a556d9ae2a6229db54bd80a4c7f`)

Repair Round 4 addressed independent review I9/I10 only. Before product changes, the new tests produced authentic RED:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_automatic_memory_end_to_end.py
2 failed, 41 passed, 1 warning
```

The I9 failure demonstrated that identical production identity inputs across distinct facts could overwrite `promotion_bindings` without an error. The I10 failure demonstrated scanner false negatives from recursively dropping `content`/`text` keys and from checking only raw JSON text. The minimal repair now precomputes the full promotion batch as a one-to-one `(opaque_memory_id, fact_id)` plan before constructing the promotion service or candidates; duplicate opaque IDs and duplicate fact bindings fail closed before any real persistence.

The scanner now retains raw values, decodes JSON strings and Unicode escapes, recursively inspects parsed objects without deleting keys, always checks frozen fact/citation labels even in body columns, and applies evaluator-marker exceptions only to explicit physical body locations. Known scalar candidate body text in the promotion event envelope is recognized as body data only at its fixed schema location; nested `content`/`text` objects and metadata/event keys remain fully checked. Direct tests cover nested structured markers, Unicode-escaped fact/citation labels, legitimate body prose, metadata/event marker failures and body-column label failures. The real runner continues to inspect every table/column/value in the temporary SourceReadModel/MemoryDatabase/StateDatabase stores and proves non-empty documents, links, active event and bridge.

```text
focused GREEN: 47 passed, 1 warning
brief regression: 58 passed, 1 warning
historical deferred Task4R1 pair: 5 failed, 10 passed, 1 warning
```

Frozen fixture hashes remain unchanged:

```text
bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94  tests/evaluation/fixtures/automatic_memory_corpus.jsonl
338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612  tests/evaluation/fixtures/automatic_memory_questions.jsonl
```

`py_compile`, cumulative `git diff --check`, acceptance sync and local handoff checks pass after the docs commit. Generic promotion, frozen fixtures/evaluator/thresholds, retrieval ranking/query/filter/order, Task 4–6/4R2, MCP parity, 100k, Artifact, Production, Vault and local acceptance task remain untouched. Remaining limitations are the historical deferred incompatibilities and the existing Pydantic deprecation warning.
