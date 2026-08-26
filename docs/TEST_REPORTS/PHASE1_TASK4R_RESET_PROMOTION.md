# Phase 1 Task 4R-Reset / Task 5 — Promotion Evidence

## Identity and boundary

- Base: `c0a812efa440cf416821afc30643f2655729dd44`
- Product commit: `055c463` (`refactor: make promotion provenance visibility atomic`)
- Report commit: recorded by the documentation commit containing this report.
- Scope: typed promotion provenance, preparing/active derived projection lifecycle, atomic SourceReadModel links, stable StateDB promotion events and leases, temporal visibility hardening, and persistence audit.
- Out of scope: Production/Vault, owner data, runner/CLI, frozen evaluator/fixtures/thresholds, retrieval ranking, Task 6/4R2/100k, Desktop, Artifact and real-machine acceptance.

## TDD evidence

The new `tests/test_task4_reset_promotion_transaction.py` was collected against the unchanged base and produced an authentic behavioral RED: `3 failed`, `0 collection errors`. Failures covered the legacy active writer bypass, missing batch-link API, and mapping provenance stringification. After implementation the same suite passed (`4 passed`); the focused promotion/context command passed (`58 passed`).

## Implemented and tested

- `PromotionProjectionState`, typed `ProvenanceRef`, resolved/result/evidence/audit contracts and canonical typed candidate refs.
- Exact message primary/external resolution with content-hash checking; source/conversation/evidence refs remain context-only.
- Additive `created_by_decision_id` link ownership migration; transactional batch link, verification and owner-filtered unlink.
- `prepare_derived_projection`, transactional activation recheck, decision-owned cleanup and raw active projection identity rows. Legacy `upsert_derived_projection` now fails closed rather than publishing active.
- Additive StateDB stable event ID/index, exact event lookup, terminal conflict detection, and promotion operation leases while retaining integer event IDs.
- `preparing`, `repair_required` and `rolled_back` are never effective in current/why/as_of temporal evaluation; current derived search also rechecks persisted status.
- Reconciliation returns shared `PromotionEvidence` and repairs complete/partial durable saga states where ownership is provable.
- `audit_promotion_persistence` computes missing/extra/duplicate IDs from raw derived rows and verified active evidence.

## Verification matrix

| Check | Result |
|---|---|
| Focused promotion/context | PASS — 58 passed |
| Source/memory/lifecycle/timeline direct regressions | PASS — 39 passed |
| Combined direct regression total | PASS — 97 passed, 2 existing warnings |
| `py_compile` modified product/tests | PASS |
| `git diff --check` | PASS |
| Fixture hashes | Preserved; no fixture files changed |
| Acceptance sync / local handoff | Pending documentation commit; local task remains IDLE |
| Real Artifact/UI/Production/Vault/owner observation | NOT_TESTED by rule |

## Durable-state evidence

- Stable promotion event IDs use `promotion:{decision_id}:{event_type}`; identical canonical payload retries reuse one row and conflicting payloads fail closed.
- Promotion links carry the stable decision owner only when created; reused NULL/foreign owners are preserved.
- Active visibility is committed only after exact canonical message/link/hash verification in the MemoryDB write transaction.
- Synthetic probes observed one projection, one exact link set and one activated terminal for repeated promotion. No production data was read or changed.

## Known limitations and decision boundary

- StateDB and MemoryDB are separate SQLite files; the implementation is a durable saga with lease/reconciliation, not cross-file ACID.
- `MemoryDatabase.fetch_memory()` remains a raw/history materializer; current-facing Gateway/retrieval predicates are the visibility boundary.
- No real-machine acceptance was authorized because `LOCAL_EXECUTION_TASK.md` is `IDLE`. This report does not claim acceptance, merge readiness, or owner confirmation.

## Cleanup

Only pytest-owned `tmp_path` SQLite fixtures were used. No runtime process, Artifact, Production/Vault data, user configuration, token, or persistent temporary evidence was touched.
