# Phase 1 Product Landing — Task 1 Report

## Scope

- Task: Thin Quality Runner Reset and Authority Reconciliation
- Base: `5c3bed8f8a4fb77632b41ec7e0c23c8ebeb72a78`
- Product/test commit: `7b549ab63d752177a4572db8f78f4ea6d879f8aa`
- Branch: `codex/phase1-automatic-memory`
- Fixtures: unchanged synthetic corpus/questions only
- Out of scope: retrieval ranking, thresholds, questions, corpus, vectors, promotion behavior, Desktop, Production/Vault, 4R2 and 100k execution

## Implementation

`quality_gate.py` now admits one typed temporary Acceptance root, runs existing import/read-model/Gateway contracts inside it, and publishes only a finalized `QualityRunEnvelope`. Production settings and roots are not read by the runner. Missing/unavailable evidence remains `NOT_MEASURED`/nullable; measured failures remain `FAIL`; cleanup errors replace the pre-cleanup envelope. The obsolete functional wrapper and embedded FastMCP registration were removed. The public CLI publishes only after the temporary root exits. `validate.ps1` stops release before any 100k command/environment construction with `BLOCKED_4R2_REQUIRED`.

Historical round-5 takeover/activation tests were migrated to preserve rejection coverage and assert the current quarantine; no fixture candidate is auto-approved and no owner-review/promotion behavior was changed.

## Commands and evidence

1. RED command required by Task 6:
   `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py`
   Result: `17 failed, 25 passed, 1 warning` (behavioral failures for missing reset APIs/guards; no collection failure).
2. Initial Task1 GREEN:
   `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_runner.py tests/test_task4_reset_validation_guard.py`
   Result: `8 passed`.
3. Task6 runner regression command:
   `./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py tests/test_automatic_memory_acceptance_gate.py`
   Result: `252 passed`.
4. Fixture hashes:
   - corpus: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`
   - questions: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`
5. `./.venv/bin/python scripts/automatic_memory_quality_gate.py`
   Result: exit `1` by design after publishing `functional_status=NOT_EVALUATED`; no Production/Vault access.
6. `./.venv/bin/python -m py_compile ...` for changed Python files: PASS.
7. `git diff --check`: PASS.
8. `./.venv/bin/python scripts/check_acceptance_sync.py`: PASS (`product-impacting files: 5`).
9. `./.venv/bin/python scripts/check_local_execution_handoff.py`: PASS; current local task remains `IDLE`.

## Current verdict

Task1 code/tests are implemented and focused-tested. Official quality functional/phase status is intentionally `NOT_EVALUATED` until Task4R2 supplies MCP parity, semantic degradation, corruption isolation, measured context baseline, scale and required physical evidence. No Artifact, release, real UI, owner observation, Production/Vault or 100k test was run. These are known blockers, not silently converted to PASS.

## Cleanup and rollback

Only pytest temporary roots were used and removed by the context manager. No owner data was touched. Roll back product/test commit `7b549ab...` and the separate documentation commit if needed; do not touch Vault, raw evidence, formal memory, Qdrant or owner settings.
