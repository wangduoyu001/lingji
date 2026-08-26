# Task 4R-Reset Task 2 Report

## Result

Implemented Task 2 on branch `codex/phase1-automatic-memory`, based on `597df6711f5e0584fccd6991065177f111bc3746`.

Product/tests commit: `9a942d3` (`fix: separate import identity from content dedup`).

Documentation/report commit: this documentation commit; its SHA is intentionally not self-referenced.

## Changed files

- `src/automatic_memory/quality_evidence.py`: exact import-audit dataclasses, batch-scoped positional comparison, stable duplicate summary, deterministic intentional content groups, and `build_expected_import_rows()`.
- `src/automatic_memory/quality_gate.py`: shared expected-row helper, explicit batch ID, read-only persisted message matching, truthful audit field use, and removal of fixture metadata mutation/`fixture_fact_id` candidate metadata.
- `src/automatic_memory/__init__.py`: public helper export.
- `tests/evaluation/test_task4_reset_import_audit.py`: adversarial audit contract and 145-row Generic History integration coverage.
- `tests/evaluation/test_automatic_memory_gate_integrity.py`: exact new audit API regression.
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`: Task 2 acceptance scope and cleanup/rollback requirements.
- `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_IMPORT_AUDIT.md`: detailed evidence.

## Evidence

- Authentic RED: focused collection failed with missing `ContentHashGroup` before product implementation.
- Focused GREEN: `20 passed in 0.55s`.
- Task 1 regression: `64 passed in 0.63s`.
- Frozen Generic History: `145/145`, all seven match counters `145`, stable duplicate total `0`, exactly `5` intentional groups.
- Fixture hashes exact: corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`; questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- `py_compile`, `git diff --check`, acceptance sync and local handoff all PASS.

## Deferred historical incompatibilities

`test_task4r1_round5_final_red.py` and `test_task4r1_takeover_red.py` retain the rejected pre-reset API. The direct caller run recorded `14 passed, 3 failed, 1 warning`; failures are old positional constructors, old positional/`list_messages()` audit calls, and a deliberately superseded sentinel/readiness assertion. They remain visible for Task 6 migration and were not hidden with aliases, skips, or deleted tests.

No frozen acceptance PASS is claimed. Task 3–6 and 4R2 evidence remain out of scope; `LOCAL_EXECUTION_TASK.md` remains IDLE. The worktree is expected to be clean after the documentation commit.
