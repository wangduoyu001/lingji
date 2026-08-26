# Phase 1 Task 8 — Work Fact Transition Closeout

This acceptance report is the repository-facing companion to the complete execution report at:

`.superpowers/sdd/2026-08-26-phase1-automatic-memory-followup/task-1-report.md`

## Verdict

```text
Product implementation: PASS
Focused Python regression: PASS (32 passed, 2 existing warnings)
Desktop work-fact script: PASS
Desktop production build: PASS
Acceptance sync: PASS
Local execution handoff: PASS
Real Desktop/Artifact/owner acceptance: NOT_RUN (LOCAL_EXECUTION_TASK.md is IDLE)
```

Product commits: `2f833aa` (`fix: unify work fact terminal transitions`), `31a14a4` (`fix: harden work fact transition persistence`).

## Scope and root cause

Callback and crash replay previously wrote the same Work Fact through separate multi-call paths. A callback success could therefore coexist briefly with an unresolved failure owner action until replay. The new `WorkStore.apply_extraction_transition` performs timestamp arbitration, stable-ID event/action writes, pending resolution, and outcome/failure projection in one existing StateDatabase transaction. Bridge completion/failure, retrying lifecycle callback, and terminal replay all delegate to it. Review round 1 additionally makes event selection UTC-aware/fail-closed, migrates legacy pending rows to one unique action ID, reopens resolved owner-failure rows, and registers the existing Desktop smoke.

## Evidence

```text
Initial RED: ./.venv/bin/python -m pytest -q tests/test_task8_work_transition_matrix.py
             12 failed — apply_extraction_transition absent
Initial GREEN: same command
               12 passed
Repair RED: same matrix command
            3 failed, 12 passed — UTC event selection and pending SQL uniqueness failures
Repair GREEN: same matrix command
              15 passed
Regression: ./.venv/bin/python -m pytest -q tests/test_capture_work_bridge.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_fact.py tests/test_work_control_api.py tests/test_work_control_service.py tests/test_task8_work_transition_matrix.py
           32 passed, 2 existing warnings
Compile/diff: py_compile PASS; git diff --check PASS
Node exact requested command: PASS — npm run test:work-fact; existing smoke prints `work-fact-smoke: PASS`
Node build: PASS — npm run build
Acceptance gates: check_acceptance_sync.py PASS; check_local_execution_handoff.py PASS
```

The matrix covers new→retrying, new→failed, failed→retrying, failed→completed without reopening, retrying→completed, repeated terminal transitions, callback/replay ordering, restart/replay, older failure after completed, malformed timestamps, and equal timestamp precedence. The lifecycle test proves immediate callback failure→success resolves owner pending before any projector/restart/reconciliation.

## Limitations

- No Artifact, real installation, UI click-through, runtime port, reboot, or owner observation was run. The local task remains IDLE.
- Existing deprecation/Vite warnings remain; no new warning category was observed.
