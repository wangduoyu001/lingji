# Phase 1 Product Landing — Task 1 Repair Round 1 Report

## Scope and identity

- Task: Thin Quality Runner Reset and Authority Reconciliation
- Original base: `5c3bed8f8a4fb77632b41ec7e0c23c8ebeb72a78`
- Original product/test commit: `7b549ab63d752177a4572db8f78f4ea6d879f8aa`
- Repair product commit: `2b99cc53d493929a0e2e75c0f79d6834355fb7dc`
- Repair authority/docs commit: `3414101d8fe30033aaea66eaa2cf615d580ad515`
- Final minimal repair commit: `50cc0e0` (`fix: restore runner readiness enum boundary`)
- Current HEAD: `50cc0e0` (`codex/phase1-automatic-memory`)
- Report commit: pending this docs commit; report does not self-reference its SHA
- Fixtures: unchanged synthetic corpus/questions only
- Out of scope: retrieval ranking, thresholds, questions, corpus, vectors, promotion behavior, Desktop, Production/Vault, 4R2, 100k execution and Artifact/UI/owner acceptance

## Repair implementation

The first repair (`2b99cc`) closes the review boundary: unmeasured MCP/context evidence is not constructed as an `EvaluationReport`; Acceptance roots require resolved temporary ancestry, an exact lease token and owner check; historical round-5 rejection coverage is restored; measured functional failures remain `FAIL` across gate exceptions; release performs an executable `--check-4r2` preflight; CLI verifies the complete temporary cleanup inventory; the 100k protected-output helper is present; and the legacy optional raw-report path is removed. `3414101` records the repaired authority metadata in the acceptance/project/module docs.

During closeout, the CLI exposed one additional real defect: `run_quality_gate()` reconstructed serialized readiness strings as plain strings, causing the strict finalizer to return `INVALID_EVIDENCE` for an otherwise valid reset run. `50cc0e0` restores `EvidenceState` enum values before finalization. This is the only additional product change and does not enter 4R2/retrieval/promotion/vector/UI scope.

## Review finding disposition

All first-review findings are closed by `2b99cc`/`3414101`, with the enum boundary correction in `50cc0e0`:

| Finding | Disposition |
|---|---|
| C1: synthetic MCP success/counts and context baseline entered evaluator report | Closed: evaluator report is `None` until measured 4R2 fields; raw envelope omits those numeric fields. |
| C2: forgeable Acceptance root/lease admission | Closed: resolved temp ancestry, exact lease token, and POSIX owner are validated; setup failures clean up. |
| C3: historical round-5 rejection tests deleted | Closed: rejection coverage is restored in the round-5 final/takeover test files. |
| I1: gate exception downgraded measured failure | Closed: measured functional failure remains `FAIL` even when the gate raises. |
| I2: release guard was static-only | Closed: release invokes the executable `--check-4r2` preflight before any 100k path. |
| I3: CLI lacked post-cleanup inventory verification | Closed: `verify_acceptance_cleanup()` runs after the temporary context exits. |
| I4: latent missing `_reject_protected_output` | Closed: helper exists and is called after the readiness guard. |
| I5: optional legacy raw-report path remained | Closed: `acceptance_roots` is required and only `QualityRunEnvelope` is returned. |
| I6: stale authority SHAs | Closed: docs record `2b99cc`, `3414101`, and current HEAD; final report records `50cc0e0`. |
| M1: setup validation could leak its root | Closed: root creation and setup validation are inside the cleanup-protected `try/finally`. |

## RED/GREEN and verification evidence

Repair-targeted RED/GREEN for the additional enum boundary:

```text
RED:
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_runner.py::test_runner_restores_readiness_enums_before_finalizing_envelope
1 failed in 3.81s

GREEN:
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_runner.py::test_runner_restores_readiness_enums_before_finalizing_envelope
1 passed in 3.81s
```

The original Task 6 RED evidence remains `17 failed, 25 passed, 1 warning` (no collection error), and the initial repair implementation was independently reviewed against the listed findings. Fresh closeout runs on final HEAD:

```text
./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py tests/test_automatic_memory_acceptance_gate.py
268 passed in 19.29s

Review-targeted subset (runner/readiness/release/historical rejection):
129 passed in 9.59s
```

The quality CLI was run with a temporary repository output path. It exited `1` as designed because functional status is `NOT_EVALUATED`; the published envelope asserted `functional_status=NOT_EVALUATED`, `phase_status=NOT_EVALUATED`, `readiness.mcp_parity=not_measured`, `readiness.context_baseline=not_measured`, and no `INVALID_EVIDENCE`. The temporary output was removed after inspection.

Additional checks:

- Fixture corpus SHA-256: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`.
- Fixture questions SHA-256: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- Changed-file `py_compile`: PASS.
- `git diff --check` and `git diff 1d401cc..HEAD --check`: PASS.
- `scripts/check_acceptance_sync.py`: PASS; no uncommitted product-impacting files.
- `scripts/check_local_execution_handoff.py`: PASS; `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## Current verdict and limits

Task 1 repair findings are closed by the tested code path; the final quality functional/phase status remains intentionally `NOT_EVALUATED` until Task 4R2 supplies MCP parity, semantic degradation, corruption isolation, measured context baseline, scale and required physical evidence. No Artifact, release, real UI, owner observation, Production/Vault, Qdrant or 100k execution was run. These are out-of-scope/known blockers, not converted to PASS.

Only pytest temporary roots and one temporary output report were used and removed. No owner data was touched. Rollback the repair product commits and this separate report/docs commit if needed; do not touch Vault, raw evidence, formal memory, Qdrant or owner settings.
