# PR #60 1860fa17 cleanup authorization repair

- Product branch: `feature/unified-ai-memory-connectors`
- Product commit: pending
- Affected module: task-scoped acceptance cleanup policy.
- Risk level: P0

## Purpose

Authorize exactly `PR60-MEMORY-TRIAL-4161807c` for the active
`PR60-MEMORY-QUALITY-TRIAL-1860FA17` task. The task document requires that
old failed root to be cleaned before Day 0, but the product cleanup policy did
not include it.

## Boundaries

- No wildcard, parent-directory, or additional task-root authorization.
- No deletion is performed by this code change.
- Production data and neighboring task directories remain refused.

## Verification

- `python -m pytest -q tests/test_cleanup_acceptance_workspace.py` (`12 passed`)
- The exact task's cleanup command returned `DRY_RUN_READY` before the explicit
  execute request and then returned `PASS` after removing only the authorized
  legacy root.

## Out of scope

- Runtime, Desktop UI, connectors, memory content, and real-data import.
