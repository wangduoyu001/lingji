# Task 5A Repair Round 1 — Owner Work API

## Review basis and scope

Independent review report: `task-5a-review.md` at evidence/docs commit `522d41ba42534ea9c00992acf20e6980ad28b454`, reviewing product `f799b8aed526b52b259a360b7162ceef9b86b0a3`. This was the single authorized repair round and addressed only I1 stale owner next action and I2 generic source summary. No new API family, store, queue, UI, memory/RAG/vector, Task 2/3, Artifact, live 8766, Production/Vault or owner data was touched.

## TDD and verification

- RED: `./.venv/bin/python -m pytest -q tests/test_work_control_api.py` — 3 behavioral failures, no collection errors: stale owner next actor after resolve, concurrent convergence, and generic source summary.
- Product/tests commit: `5e71cda68edfb86eac99804bc66fbfb6540bcb9c`.
- Focused GREEN: `./.venv/bin/python -m pytest -q tests/test_work_control_api.py tests/test_task8_work_fact.py tests/test_work_store.py tests/test_work_control_service.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_transition_matrix.py` — 40 passed, 2 warnings.
- Broader regression GREEN: `./.venv/bin/python -m pytest -q tests/test_work*.py tests/test_task8*.py tests/test_capture*.py tests/test_automatic_memory_work_fact.py` — 102 passed, 2 warnings.

## Changes

- `resolve_pending_action` now selects, marks resolved, and conditionally deletes only the matching `(work_id, action_id, actor='owner')` next action in one existing StateDatabase transaction. Concurrent/replayed calls converge; a newer system next action remains intact; restart/current/history/pending agree.
- Friendly history source uses the existing WorkItem title as a readable label, returns exact `source_id` only as secondary diagnostic, and returns null for an un-sourced work. No source type or path is inferred.

## Boundaries

`compileall`, `git diff --check`, acceptance sync and local handoff are required after the evidence/doc commit. `LOCAL_EXECUTION_TASK.md` remains `IDLE`; no real service, packaged build, Artifact, Production/Vault or owner acceptance was run. This repair is final; any remaining Important finding blocks acceptance and requires re-planning rather than another patch.
