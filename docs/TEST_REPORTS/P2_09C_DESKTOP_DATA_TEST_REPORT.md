# P2-09C Desktop Data Test Report

## Environment

Changes were written through the GitHub connector on `work/p2-09c-desktop-data`. No local Node, npm, browser or Tauri runtime was attached to this conversation.

## Test coverage added

`desktop/lingji-control/scripts/polling-data-smoke.mjs` verifies that:

- the polling hook contains cancellation, in-flight protection, recursive timeout scheduling, visibility handling, failure state and success timestamps;
- Brain Status normalization preserves `null` unknown values;
- genuine measured zero values remain zero.

The smoke is registered in the existing `run-smoke-suite.mjs`, so the normal desktop build runs it before TypeScript and Vite compilation.

## Page coverage

- Brain Status uses the shared contract and no longer defaults unknown GPU utilization to zero.
- Jobs uses the shared polling hook and retains previous data on refresh errors.

## Execution status

Status at document creation: `TESTS_ADDED_NOT_EXECUTED`.

GitHub Actions must execute the existing desktop smoke/build jobs. Required manual checks remain:

1. switch rapidly between pages and verify requests are aborted;
2. hide and restore the window and verify polling pauses/resumes;
3. stop the 8766 service and verify old data remains with an error/stale indicator;
4. restore the service and verify backoff recovers;
5. verify a real measured GPU zero differs visually from unavailable telemetry.

## Contract SHA

`4222daf432134b8d77d5e7b514c258022d5ed4a8`

## Backend/data impact

- Python backend changed: no.
- Database schema changed: no.
- Auto Review UI changed: no.
- App/navigation changed: no.

## Final commit

Record the final PR head after CI-driven corrections.
