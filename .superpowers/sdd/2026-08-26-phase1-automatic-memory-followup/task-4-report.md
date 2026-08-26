# Task 4 / 4R1 report

## Status

`DONE_WITH_CONCERNS`: 4R1 repaired part of measurement truthfulness and restricted provenance links. The rejected initial draft did not follow RED-first; this remains explicitly recorded as `TDD_ORDER_NOT_MET`. This round added authentic RED tests for protected-tree missing-root handling, then GREEN.

## Evidence

- RED: `.venv/bin/pytest -q tests/evaluation/test_automatic_memory_gate_integrity.py` — collection failed because `quality_evidence` did not exist (`ModuleNotFoundError`).
- GREEN: `.venv/bin/pytest -q tests/evaluation/test_automatic_memory_gate_integrity.py tests/evaluation/test_automatic_memory_end_to_end.py tests/test_auto_memory_promotion.py` — `46 passed, 1 warning`.
- Frozen hashes unchanged: corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`; questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- The measured quality result remains FAIL for recall/citation; no retrieval or fixture tuning was performed.
- Round 2 RED: missing protected root test failed (`DID NOT RAISE`). Round 2 GREEN: `47 passed, 1 warning`.
- Round 3 RED: persisted audit initially returned zero role/hash matches for a duplicated external ID; Round 3 GREEN: `.venv/bin/pytest -q tests/evaluation/test_automatic_memory_gate_integrity.py tests/evaluation/test_automatic_memory_end_to_end.py tests/test_auto_memory_promotion.py` — `48 passed, 1 warning`.

## Scope limits

MCP/degradation/100k, corruption isolation and baseline reduction remain 4R2 and are explicitly NOT_EXECUTED; they are not counted as measured PASS. LOCAL_EXECUTION_TASK remained IDLE; no Artifact, Production, Vault or owner/Mac evidence was used.

## Commits

- Code/tests: this round commit follows below.
- Docs: this round commit follows below.

## Round-4 takeover evidence (base `f9bf190`, code commit `8743356`)

The rejected initial draft remains explicitly `TDD_ORDER_NOT_MET`; this takeover did not relabel that history. The new tests were authored and run against the base before the repair:

```text
Command: ./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_takeover_red.py
Result: 7 targeted defects failed, 2 baseline safety checks passed (the runner test adds one failure; the ambiguous-ref check already failed closed).
```

The six baseline failures were authentic defects: adapter projection fields were unsupported by `ImportedEvidenceAudit`; the pre-query identity-map API was absent; generic message provenance did not activate; multi-link compensation did not run; unreadable descendant errors were not fail-closed; and readiness isolation was absent. The seventh RED assertion was a baseline behavior already present and was retained as a GREEN integrity check rather than misreported as a defect.

The added runner-integration RED was independently reproduced on a detached `f9bf190` worktree:

```text
Command: /Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory/.venv/bin/python -m pytest -q tests/evaluation/test_takeover_runner_red.py
Result: 1 failed, 1 warning in 2.53s
Failure: KeyError: 'quality_evidence_readiness'
```

Round-4 implementation GREEN:

```text
Command: ./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_takeover_red.py
Result: 9 passed, 1 warning in 2.49s

Command: ./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_takeover_red.py tests/evaluation/test_automatic_memory_gate_integrity.py tests/evaluation/test_automatic_memory_end_to_end.py tests/test_auto_memory_promotion.py
Result: 57 passed, 1 warning in 5.37s
```

The repair now captures adapter-produced external source/conversation/message IDs and hashes before persistence, compares them to persisted rows (including extra/missing/duplicate/order/role/sequence/hash/source/conversation), builds the selector map before question execution without writing fact/citation labels into imported rows, validates selected evidence fail-closed, resolves unambiguous generic/source/conversation/evidence references to message primary IDs, and compensates every link plus projection on later-link failure. Protected-tree capture receives every configured root and records missing/unreadable roots as unavailable evidence instead of filtering them. The 4R1 readiness envelope reports `functional_status=NOT_EVALUATED` and does not call either acceptance gate until 4R2 fields exist.

Fresh gate envelope observation: import `145/145`, role/order `145/145`, production pollution `0`; configured `vault` is absent and is recorded as `missing protected root: vault`; MCP/degradation/context-baseline/scale are `NOT_MEASURED`/4R2. Frozen corpus/questions hashes remain unchanged as listed above. No Artifact, Production/Vault, owner, reboot, or 4R2 evidence was used.
