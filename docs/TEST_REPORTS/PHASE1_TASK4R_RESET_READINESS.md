# Phase 1 Task 4R-Reset — Readiness Envelope

## Scope

This change implements only the Task 4 evidence primitives: four-state readiness,
the immutable frozen-gate finalizer, explicit-root protected-tree snapshots and
the low-level atomic JSON writer. The existing quality runner return type and
lifecycle remain unchanged for the later Task 6 migration.

## TDD evidence

- RED (before product implementation): `tests/evaluation/test_task4_reset_readiness.py`
  failed during collection with `ImportError: cannot import name 'EvidenceState'`.
- GREEN focused: `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_readiness.py`
  — **12 passed**.
- Frozen-gate regression: `./.venv/bin/python -m pytest -q tests/test_automatic_memory_acceptance_gate.py tests/evaluation/test_automatic_memory_gate_integrity.py`
  — **46 passed**.
- Current e2e visibility: `tests/evaluation/test_automatic_memory_end_to_end.py` — **20 passed, 1 warning**.
- Historical Task4R1 visibility (unchanged, intentionally not migrated):
  `test_task4r1_round5_final_red.py test_task4r1_takeover_red.py` — **8 failed, 7 passed**;
  failures are expected compatibility gaps deferred to Task 6.

## Contract evidence

- Readiness has exactly 13 `EvidenceState` fields. Invalid/non-enum states fail
  closed; incomplete functional evidence makes zero gate calls and yields three
  `NOT_EVALUATED` statuses.
- Complete functional evidence calls the injected frozen gate exactly twice;
  the first call is an owner/reboot-100 functional copy with empty blocked
  reasons, and the second is the original report.
- Frozen threshold misses remain measured `FAIL`; a `FAILED` readiness field
  combined with frozen `PASS` is contradictory and fails closed.
- Mac release states produce `PASS`/`FAIL`/`BLOCKED` only after measured
  functional evidence; Windows cannot block Mac and reports
  `WINDOWS_AFTER_MAC` until Mac passes.
- Sentinel pollution is numeric only for strict integer/count-consistent
  evidence. Root IDs and entry keys use SHA-256 identifiers and never expose
  configured paths. Missing, symlinked, special, unreadable or raced trees are
  typed fail-closed errors.
- Atomic publication requires an existing real parent, rejects protected or
  symlink paths, uses unique same-directory exclusive temporary files, flushes
  and fsyncs before replacement, and removes invocation-owned residue on
  failure.

## Integrity checks

- Frozen corpus SHA-256: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`.
- Frozen questions SHA-256: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- `git diff --check`: PASS.
- `python3 scripts/check_acceptance_sync.py`: PASS.
- `python3 scripts/check_local_execution_handoff.py`: PASS.

## Limitations / deferred work

Task 6 still owns runner fail-closed publication and cleanup inventory,
AcceptanceRoots, public envelope return/lifecycle migration, historical caller
migration, release/100k guards and physical Production/Vault evidence. No
Production/Vault, Artifact, MCP parity, degradation, corruption, scale or
owner/reboot evidence was attempted here.

## Commits

Product/tests: `a4201f078be7918dc2369cd9c7c023b209b3053a`
(`fix: gate quality on complete evidence readiness`). Documentation:
`9788356d3d26fae5f0e8431ccf41827397b5c976`
(`docs: record task4 reset readiness`).
