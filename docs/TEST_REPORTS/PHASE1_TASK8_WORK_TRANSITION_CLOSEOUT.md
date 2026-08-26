# Phase 1 Task 8 — Work Fact Transition Closeout

This acceptance report is the repository-facing companion to the complete execution report at:

`.superpowers/sdd/2026-08-26-phase1-automatic-memory-followup/task-1-report.md`

## Verdict

```text
Product implementation: PASS
Focused Python regression: PASS (29 passed, 2 existing warnings)
Desktop work-fact script: BLOCKED (script absent from package.json)
Desktop production build: PASS
Acceptance sync: PASS
Local execution handoff: PASS
Real Desktop/Artifact/owner acceptance: NOT_RUN (LOCAL_EXECUTION_TASK.md is IDLE)
```

Product commit: `2f833aa` (`fix: unify work fact terminal transitions`).

## Scope and root cause

Callback and crash replay previously wrote the same Work Fact through separate multi-call paths. A callback success could therefore coexist briefly with an unresolved failure owner action until replay. The new `WorkStore.apply_extraction_transition` performs timestamp arbitration, stable-ID event/action writes, pending resolution, and outcome/failure projection in one existing StateDatabase transaction. Bridge completion/failure, retrying lifecycle callback, and terminal replay all delegate to it.

## Evidence

```text
RED: ./.venv/bin/python -m pytest -q tests/test_task8_work_transition_matrix.py
      12 failed — AttributeError: WorkStore.apply_extraction_transition absent
GREEN: same command
        12 passed
Regression: ./.venv/bin/python -m pytest -q tests/test_capture_work_bridge.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_fact.py tests/test_work_control_api.py tests/test_work_control_service.py tests/test_task8_work_transition_matrix.py
           29 passed, 2 existing warnings
Compile/diff: py_compile PASS; git diff --check PASS
Node exact requested command: BLOCKED — Missing script: test:work-fact
Node build: PASS — npm run build
Acceptance gates: check_acceptance_sync.py PASS; check_local_execution_handoff.py PASS
```

The matrix covers new→retrying, new→failed, failed→retrying, failed→completed without reopening, retrying→completed, repeated terminal transitions, callback/replay ordering, restart/replay, older failure after completed, malformed timestamps, and equal timestamp precedence. The lifecycle test proves immediate callback failure→success resolves owner pending before any projector/restart/reconciliation.

## Limitations

- `npm run test:work-fact` is not registered in the existing Desktop package and was not added because `package.json` is outside this task's allowed files.
- No Artifact, real installation, UI click-through, runtime port, reboot, or owner observation was run. The local task remains IDLE.
- Existing deprecation/Vite warnings remain; no new warning category was observed.
