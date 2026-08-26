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
