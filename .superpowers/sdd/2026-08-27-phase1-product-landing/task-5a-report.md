# Task 5A — Owner Work API foundation

## Scope

This bounded slice reuses the existing `lingji_state.db` WorkStore and authenticated Local Control API. It adds history pagination, chronological timeline projection, and idempotent pending-action resolution. It does not add a task store, queue, memory capability, retrieval/vector behavior, UI, Artifact, live 8766, Production/Vault access, or owner data handling.

## TDD evidence

- Baseline: `7d4e4e1bbeeaf24f5000bac2944a1e6c3502bc48`.
- RED: `./.venv/bin/python -m pytest -q tests/test_work_control_api.py tests/test_task8_work_fact.py` — 4 behavioral failures, no collection errors.
- Product/tests commit: `f799b8aed526b52b259a360b7162ceef9b86b0a3`.
- GREEN focused matrix: `./.venv/bin/python -m pytest -q tests/test_work_control_api.py tests/test_task8_work_fact.py tests/test_work_store.py tests/test_work_control_service.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_transition_matrix.py` — 36 passed, 2 warnings.

## Implemented behavior

- `GET /api/work/history?limit=&offset=` is authenticated and bounds `limit` to 1–100, preserves stable `work_id`, and reports `total`/`has_more` from the durable store.
- Timeline reads preserve event IDs and return chronological events after restart.
- `POST /api/work/pending-actions/{action_id}/resolve` is authenticated, returns 404 for an unknown action, and safely replays an already resolved action.
- Friendly phase/result/time/source/next-actor fields are additive to history items; raw IDs and details remain available in the existing fact payload.
- Existing current/pending/timeline projections and all transition matrix tests remain green.

## Verification and boundaries

`py_compile`, `git diff --check`, acceptance sync, and local handoff are required after the evidence/doc commit. No real service, packaged build, Artifact, Production/Vault or owner data was touched; `LOCAL_EXECUTION_TASK.md` remains `IDLE`. Independent review is required before Task 5B or any broader Task 5 UI work is accepted.
