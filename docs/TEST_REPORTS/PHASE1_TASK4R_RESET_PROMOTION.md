# Phase 1 Task 4R-Reset / Task 5 — Promotion Evidence

## Identity and boundary

- Initial Task 5 base: `c0a812efa440cf416821afc30643f2655729dd44`
- Repair 1 base: `263ca2df2beb720b046897cf3c6960731567a34e`
- Initial product commit: `055c4637f2d1c8e7283cdeb39161c23f7e5ef042` (`refactor: make promotion provenance visibility atomic`)
- Repair product commit: `b5d7a482787c47137ea8f12458939f100098e524` (`fix: complete promotion recovery invariants`)
- Report commit: recorded by the documentation commit containing this report.
- Scope: typed promotion provenance, preparing/active derived projection lifecycle, atomic SourceReadModel links, stable StateDB promotion events and leases, temporal visibility hardening, and persistence audit.
- Out of scope: Production/Vault, owner data, runner/CLI, frozen evaluator/fixtures/thresholds, retrieval ranking, Task 6/4R2/100k, Desktop, Artifact and real-machine acceptance.

## TDD evidence

The initial Task 5 suite recorded `3 failed`, `0 collection errors` against its unchanged base. Repair Round 1 added C1–C3/I1–I5 behavior tests and recorded `7 failed`, `0 collection errors` against unchanged repair base `263ca2df...`; failures covered cross-entity terminal conflict, active-link repair, approval saga, legacy/typed provenance, scanner, and forged external identity. After repair the same repair suite passed (`42 passed`).

## Implemented and tested

- `PromotionProjectionState`, typed `ProvenanceRef`, resolved/result/evidence/audit contracts and canonical typed candidate refs.
- Exact message primary/external resolution with content-hash checking; source/conversation/evidence refs remain context-only.
- Additive `created_by_decision_id` link ownership migration; transactional batch link, verification and owner-filtered unlink.
- `prepare_derived_projection`, transactional activation recheck, decision-owned cleanup and raw active projection identity rows. Legacy `upsert_derived_projection` now fails closed rather than publishing active.
- Additive StateDB stable event ID/index, exact event lookup, terminal conflict detection, and promotion operation leases while retaining integer event IDs.
- `preparing`, `repair_required` and `rolled_back` are never effective in current/why/as_of temporal evaluation; current derived search also rechecks persisted status.
- Reconciliation returns shared `PromotionEvidence` and repairs complete/partial durable saga states where ownership is provable.
- `audit_promotion_persistence` computes missing/extra/duplicate IDs from raw derived rows and verified active evidence.
- Repair invariants: terminal exclusivity is decision-keyed; active reconciliation verifies complete canonical parent/hash/relation/owner links and durably marks repair; owner approval uses lease/start/prepare/link/activate/terminal; event provenance supports exact event/hash happy and negative paths; stable payloads reject nested metadata, secrets, escaped/absolute paths, fixture/evaluator labels, exception text and NaN.

## Verification matrix

| Check | Result |
|---|---|
| Repair promotion transaction | PASS — 42 passed |
| Focused promotion/context | PASS — 84 passed |
| Task1–4/reset combined | PASS — 274 passed |
| Source/memory/lifecycle/timeline direct regressions | PASS — 39 passed |
| Fixture hashes | PASS — corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`; questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612` |
| `py_compile` modified product/tests | PASS |
| `git diff --check` | PASS |
| Acceptance sync / local handoff | Pending documentation commit; local task remains IDLE |
| Real Artifact/UI/Production/Vault/owner observation | NOT_TESTED by rule |

## Durable-state evidence

- Stable promotion event IDs use `promotion:{decision_id}:{event_type}`; identical canonical payload retries reuse one row and conflicting payloads fail closed.
- Promotion links carry the stable decision owner only when created; reused NULL/foreign owners are preserved.
- Active visibility is committed only after exact canonical message/link/hash verification in the MemoryDB write transaction.
- Synthetic probes observed one projection, one exact link set and one activated terminal for repeated promotion; lease claim/renew/release and injected start/prepare/link/activation failure paths were exercised. No production data was read or changed.

## Known limitations and decision boundary

- StateDB and MemoryDB are separate SQLite files; the implementation is a durable saga with lease/reconciliation, not cross-file ACID.
- `MemoryDatabase.fetch_memory()` remains a raw/history materializer; current-facing Gateway/retrieval predicates are the visibility boundary.
- No real-machine acceptance was authorized because `LOCAL_EXECUTION_TASK.md` is `IDLE`. This report does not claim acceptance, merge readiness, or owner confirmation.
- The repository has no standalone `tests/test_automatic_memory_temporal_hardening.py`; temporal coverage is provided by the repair matrix and existing Task7 timeline tests.

## Cleanup

Only pytest-owned `tmp_path` SQLite fixtures were used. No runtime process, Artifact, Production/Vault data, user configuration, token, or persistent temporary evidence was touched.
