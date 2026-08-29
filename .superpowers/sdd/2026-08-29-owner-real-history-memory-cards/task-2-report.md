# Task 2 — Owner Memory Card Projection

## Status

`IMPLEMENTED_FOCUSED_PASS`

The product/test commit is `213bc7e6df1d73584b5e960c00c3b476ab5e5533` (base
`30b6857074ab631a27e35d1644e49496bae08de6`). No live service, packaged app,
Acceptance data root, Production/Vault, real chat, or owner data was opened.

## Red → Green evidence

1. `python3 -m pytest -q tests/test_owner_memory_card_projector.py --tb=short`
   first failed during collection with `ModuleNotFoundError` because the
   unified projector did not exist; after implementation: **5 passed**.
2. `python3 -m pytest -q tests/test_owner_memory_card_api.py --tb=short`
   first returned **3 failures** with HTTP 404 because both routes were absent;
   after route registration: **3 passed, 1 warning**.

The projector tests cover active/derived, pending candidate, superseded with
replacement, missing timestamps, conflict/provenance mismatch, vector
unavailable, pending StateDB promotion evidence, unpromoted conversation cards,
bounded evidence and limit validation. API tests cover token protection,
filters/pagination, detail expansion and the 1..50 limit.

## Implementation

- Added `src/gateway/owner_memory_cards.py` with a read-only
  `OwnerMemoryCardProjector` and `OwnerMemoryCard` DTO.
- Added card methods to `MemoryInspectorFacade` and passed the existing optional
  StateDB through the control builder for read-only promotion-event projection.
- Added only `GET /api/memory/inspector/cards` and
  `GET /api/memory/inspector/cards/{memory_id}` to the authenticated 8766 API.
- Lists omit full evidence by default; detail evidence is capped at three
  previews of 240 characters each. Original message detail remains the existing
  source of full content.
- No database schema, index, queue, UI, or permanent truth source was added.

## Verification

| Command | Result |
|---|---|
| Task 2 projector + API tests | 8 passed, 1 warning |
| Inspector + temporal + promotion + structured evidence regressions | 94 passed, 2 warnings |
| Combined Task 2 + Inspector suite | 16 passed, 1 warning |
| `python3 -m compileall -q` affected modules | PASS |
| `git diff --check` | PASS |
| `python3 scripts/check_local_execution_handoff.py` | PASS (`IDLE`) |
| `python3 scripts/check_acceptance_sync.py` | PASS after docs commit |

The repository does not contain `./.venv/bin/pytest` and has no `python` alias;
the equivalent available interpreter was `python3`.

## Known limits / risk

- Cards are a projection of currently available read-model rows. A promotion
  event is shown as a pending candidate only when StateDB is supplied; it is
  never persisted by this feature.
- Vector status is reported from the existing snapshot/coverage service. A
  missing provider or incomplete snapshot remains unavailable/unknown and is
  never treated as complete.
- No real-machine, packaged, UI, owner-observation, or Acceptance run was
  authorized by the current `LOCAL_EXECUTION_TASK.md` (`IDLE`).

## Repair Round 1 (review `c180fda`)

### RED evidence

Added one focused behavior test for each review finding (I1–I7, M1–M2) and
ran `python3 -m pytest -q tests/test_owner_memory_card_projector.py --tb=short`.
The current implementation produced **9 failures, 5 passes**: unsupported
development fallback, rejected-event pending projection, global vector
complete, truncated provenance, lexical timestamp max, archived source current,
malformed conversation timestamp current, unknown-evidence no-op, and malformed
vector-count exception.

### GREEN implementation

Product/tests commit: `0f657cc`.

- Development/conclusion content now requires verified message evidence; event
  payload lines are never treated as evidence.
- Promotion events retain their actual pending or terminal state, newest event
  wins, and rejected events do not become confirmation cards.
- Vector state uses the existing per-memory chunk `semantic.exists` seam; absent
  provider, missing chunks, and existence errors fail closed.
- All provenance refs are checked for identity/content hash; only the returned
  preview is capped to three items and `evidence_count` reflects all refs.
- Shared timezone-aware `parse_instant` determines latest evidence and malformed
  or missing times remain unknown. Archived sources are treated as unavailable.
- Unknown evidence/provenance leads to a review action. `source_id` is also
  accepted as an API filter alias.

### Round1 verification

| Command | Result |
|---|---|
| `tests/test_owner_memory_card_projector.py` | 14 passed |
| Task2 + Inspector/temporal/promotion/source regression matrix | 100 passed, 2 warnings |
| `tests/test_promotion_recovery_matrix.py::test_recovery_case_06_restart_after_link_commit_activates_after_verification` | 1 pre-existing baseline failure (`ROLLED_BACK` vs `VISIBLE_ACTIVE`); unchanged test and outside Task2 diff |
| affected `compileall` | PASS |
| `git diff --check` | PASS |

No live 8766/8767, Desktop, Artifact, Acceptance, Production/Vault, real chat,
or owner data was accessed. The repair is ready for final fresh verification;
the known promotion recovery baseline failure remains explicitly reported and
was not changed or hidden.

### Final-HEAD fresh verification

At final HEAD (`0f657cc` product + docs commit below), the focused pair returned
**17 passed, 1 warning** and the direct Inspector/permission/temporal/promotion/
source matrix returned **83 passed, 2 warnings**. Together these are **100
passed, 3 warnings**. The unchanged promotion recovery case 06 still returned
the known **1 baseline failure** (`ROLLED_BACK` vs `VISIBLE_ACTIVE`). Affected
compileall, diff-check, acceptance-sync, and local-handoff all passed; no
live/owner data path was run.
