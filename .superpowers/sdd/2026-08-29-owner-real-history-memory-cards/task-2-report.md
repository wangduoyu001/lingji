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
