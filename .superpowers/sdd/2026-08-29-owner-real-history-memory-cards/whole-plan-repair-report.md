# Whole-plan I1/I2 Repair Report

## Scope

- Baseline: `b67d1bbdcdd6cca92dce61a359eb37bae4694168` (clean).
- Product/tests commit: `8b7c37e6f87561b6013123abb2995a760174c15c`.
- Docs/evidence commit: pending (this report and the synchronized acceptance log).
- Scope was limited to `whole-plan-review.md` I1/I2. M1 (`PROJECT_STATUS`) was not changed.
- No live app, Acceptance environment, real chats, Production/Vault, Artifact, or owner data was accessed.

## TDD evidence

- RED I1: `npm run test:memory-sources` failed because `sourceMetadataEvidence` was not exported.
- RED I2: `python3 -m pytest -q tests/test_owner_memory_card_projector.py -k 'pagination_sorts or deterministic_tie' --tb=short` failed 2 tests: lexical ordering put `invalid` first and equal instants were not deterministically ordered as required.
- GREEN: the same I2 test command passed (`2 passed`); `npm run test:memory-sources` passed (`automatic-memory-sources-smoke: PASS`).

## Changes

- `memorySourcesApi.ts` now adapts nullable source metadata into owner-safe file count, byte count, and UTC time-range strings. `MemorySourcesPage.tsx` renders these four values only on the Codex source card; unknown values render `尚未获得` and no path, ID, body, or JSON is rendered.
- The rendered fixture and source adapter smoke cover exact measured values, unknown values, and metadata leakage boundaries.
- `OwnerMemoryCardProjector._sort_key()` parses `latest_evidence_at` through the shared timezone-aware parser, normalizes valid values to UTC instants, buckets invalid/unknown values behind valid evidence, and uses `memory_id` as deterministic tie-breaker. Tests cover mixed offsets, equal instants, invalid/unknown values, and pagination boundaries.

## Verification

| Check | Result |
|---|---|
| Whole-plan focused group 1 | PASS — `68 passed, 1 warning` |
| Whole-plan focused group 2 | PASS — `162 passed, 3 warnings` |
| `npm run test:memory-sources` | PASS |
| `npm run test:e2e:memory` | PASS — `e2e_owner_memory_flow: PASS` |
| `npm run test:smoke` | PASS — `23 scripts` |
| `npm run build` | PASS — 96 modules transformed; existing dynamic-import warnings only |
| `python3 -m compileall -q src tests` | PASS |
| `git diff --check` | PASS |
| `python3 scripts/check_local_execution_handoff.py` | PASS |
| `python3 scripts/check_acceptance_sync.py` | PASS — after adding the synchronized acceptance-log entry |

No product test failure remains in this scope. This report does not claim Mac release, live owner proof, or Phase 1 acceptance.
