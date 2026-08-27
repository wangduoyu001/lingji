# Phase 1 Product Landing — Task 1 Repair Round 2 Closeout

## Scope and identity

- Task: Thin Quality Runner Reset and Authority Reconciliation
- Review range head supplied by the independent review: `d1c0185887e450945c5eb607aa7199b835cd2483`
- Original base: `5c3bed8f8a4fb77632b41ec7e0c23c8ebeb72a78`
- Product/test commits: `2b99cc53d493929a0e2e75c0f79d6834355fb7dc`, `50cc0e0`, `5f75e3af9b2269519337de68db6a688bd4e654f0`
- Authority docs commit: `3414101d8fe30033aaea66eaa2cf615d580ad515`
- Prior report evidence commit: `d1c0185887e450945c5eb607aa7199b835cd2483`
- Fixtures: unchanged synthetic corpus/questions only
- Out of scope: 4R2, retrieval ranking, promotion policy, vectors, Desktop/UI, Production/Vault, Qdrant and 100k execution

## Repair Round 2 implementation

The final repair restores the historical round-5/takeover rejection assertions and the end-to-end SQLite storage scan, migrating activation checks to the explicit owner-approval API while retaining quarantine for ordinary and redacted candidates. Acceptance admission now checks actual mode bits plus root/child read-traverse capability, cleanup inventory uses lexical `lstat` existence, and measured functional failures remain `FAIL` for gate exceptions, `PASS`, malformed and bogus verdicts. Gateway serialization compares `EvidenceState.READY` explicitly; cleanup publication uses a fixed allowlist with a stable generic fallback. A formal Python release preflight boundary is called by the PowerShell 5.1 release entry and authorizes scale callbacks only after readiness.

## Review finding disposition

| Finding | Disposition |
|---|---|
| C1 | Closed: historical round-5/takeover behavior and the original end-to-end persisted-order, promotion/link, rollback, sentinel, readiness and storage scans are restored from `5c3bed8` and migrated to current APIs; no helper-absence or enum-only substitute remains. |
| I1 | Closed: `AcceptanceRoots` checks root, storage, vault, output and lease marker mode bits and performs real directory listing/read checks; mode-000 probes fail at admission. |
| I2 | Closed: `verify_acceptance_cleanup()` uses `os.path.lexists()` and detects dangling symlink residue. |
| I3 | Closed: measured functional `FAILED` is authoritative over raise, `PASS`, bogus and malformed gate outcomes, with stable reason codes and preserved report evidence. |
| I4 | Closed: `run_release_preflight()` is the formal Python sequencing boundary; spy tests prove blocked 100k environment/command callbacks are both zero, and the release entry invokes the Python preflight before any scale path. |
| I5 | Closed: this report records component commits and the review-range head only; no current-HEAD or pending self-reference is used. |
| I6 | Closed: the final matrix command explicitly includes `tests/test_task4_reset_promotion_transaction.py` and records the complete count. |
| M1 | Closed: gateway readiness status is serialized only when `readiness.gateway_selection is EvidenceState.READY`. |
| M2 | Closed: cleanup failure publication accepts only fixed internal codes; unknown/path/token-bearing values map to `UNTRUSTED_BLOCKED_REASON`. |

## RED/GREEN and verification evidence

Repair-targeted RED after restoring the historical assertions:

```text
./.venv/bin/pytest -q tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/evaluation/test_automatic_memory_end_to_end.py
5 failed, 34 passed
```

Repair-targeted GREEN after the minimal API/admission/finalizer fixes:

```text
./.venv/bin/pytest -q tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/evaluation/test_automatic_memory_end_to_end.py
150 passed in 54.63s
```

Complete Task 1–5 reset matrix (including the required promotion transaction suite):

```text
./.venv/bin/pytest -q tests/test_task4_reset_ingestion_order.py tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py tests/test_automatic_memory_acceptance_gate.py tests/test_task4_reset_promotion_transaction.py
336 passed in 65.44s
```

The original pre-transaction reset command was also rerun on the final tree (the added Round2 coverage increases its count from the historical 252):

```text
./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py tests/test_automatic_memory_acceptance_gate.py
282 passed in 71.83s
```

Additional evidence:

- `./.venv/bin/python scripts/automatic_memory_quality_gate.py --check-4r2`: expected exit `1`, `BLOCKED_4R2_REQUIRED`; no 100k execution.
- `./.venv/bin/python -m py_compile src/automatic_memory/quality_gate.py src/automatic_memory/quality_evidence.py scripts/automatic_memory_quality_gate.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/evaluation/test_automatic_memory_end_to_end.py`: PASS.
- Fixture corpus SHA-256: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`.
- Fixture questions SHA-256: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- `git diff --check`, `git diff 1d401cc..HEAD --check`: PASS before the report-only docs commit.
- `scripts/check_acceptance_sync.py` and `scripts/check_local_execution_handoff.py`: PASS; local task remains `IDLE`.

## Current verdict and limits

Repair Round 2 closes the one Critical, six Important and two Minor findings in the reviewed range. The quality runner remains intentionally `functional_status=NOT_EVALUATED` / `phase_status=NOT_EVALUATED` until 4R2 supplies its evidence. No Artifact, UI, owner observation, Production/Vault, Qdrant or 100k run was performed. Temporary pytest roots and synthetic SQLite/Vault fixtures were cleaned; no owner data was touched. Round 2 is final; do not open a third repair round.
