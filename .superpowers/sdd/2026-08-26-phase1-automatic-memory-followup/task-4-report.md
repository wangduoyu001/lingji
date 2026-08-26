# Task 4 / 4R1 report

## Status

`DONE_WITH_CONCERNS`: 4R1 repaired measurement truthfulness and promotion provenance. The rejected initial draft did not follow RED-first; this remains explicitly recorded as `TDD_ORDER_NOT_MET`. This round added authentic RED tests for protected-tree sentinels, then GREEN.

## Evidence

- RED: `.venv/bin/pytest -q tests/evaluation/test_automatic_memory_gate_integrity.py` — collection failed because `quality_evidence` did not exist (`ModuleNotFoundError`).
- GREEN: `.venv/bin/pytest -q tests/evaluation/test_automatic_memory_gate_integrity.py tests/evaluation/test_automatic_memory_end_to_end.py tests/test_auto_memory_promotion.py` — `46 passed, 1 warning`.
- Frozen hashes unchanged: corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`; questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- The measured quality result remains FAIL for recall/citation; no retrieval or fixture tuning was performed.

## Scope limits

MCP/degradation/100k remain 4R2 and are not counted as newly proven by this round. LOCAL_EXECUTION_TASK remained IDLE; no Artifact, Production, Vault or owner/Mac evidence was used.

## Commits

- Code/tests: `fix: make automatic memory gate evidence truthful` (pending)
- Docs: `docs: record task4 gate repair evidence` (pending)
