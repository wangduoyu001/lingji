# P2-08 / P2-09 Integration Test Report

## Scope

This report covers the combined integration of:

- P2-09A Runtime Truth and Configuration Alignment
- P2-09B Canonical Idempotency and MCP Queue Wiring
- P2-09C Desktop Polling Data Layer
- P2-09D Desktop UX and Auto Review SHADOW Dashboard
- P2-08A Auto Review Deterministic Core
- P2-08B Local AI Reviewer and SHADOW API

## Merge sequence

The following pull requests were merged into `feature/second-brain-memory` in dependency-safe order:

1. PR #24, merge commit `93b16f76c4fe0148f93cdfab8dc85dcf2c36f1ee`
2. PR #25, merge commit `c0129ab069a14a1d6cd0556ff0999c5968f24484`
3. PR #26, merge commit `1914bd12a74ed2afe98fb5f15430c6a7917d6bda`
4. PR #27, merge commit `62d0fcb10d5ad7d31cdef2333778fd6184fc3f55`
5. PR #28, merge commit `95190d219b43e59dad982ac4b68c63f290f9b81a`
6. PR #29, merge commit `9aed67d38b50394d4319c7002a37106c37d2140a`

PR #28 and PR #29 were retargeted from their stacked dependency branches to `feature/second-brain-memory` only after their base PRs were merged. GitHub recalculated both as mergeable before merging.

## Pre-integration CI evidence

Each source PR completed the repository GitHub Actions suite before merge. The suite included, where applicable:

- Python 3.11 unit tests
- Python 3.12 unit tests
- Windows unit tests and compile checks
- Desktop smoke tests
- React/Vite production build
- Tauri configuration validation
- MCP server creation smoke test
- Browser capture extension smoke test
- Obsidian plugin smoke test

The final P2-09D head `5ac2a0664fdbc1f1d28a05d0523a7ef6d50bb905` passed the complete test workflow, including the Windows job.

## Combined configuration verification

After all six merges, the integrated branch was inspected and confirmed to retain both sets of configuration:

- primary embedding model: `bge-m3`
- fallback embedding model: `nomic-embed-text`
- Auto Review mode default: `OFF`
- Auto Review local AI default: disabled
- Control API port: `8766`

The Auto Review merge did not overwrite the runtime-truth embedding defaults.

## Combined behavior verification

`tests/test_p2_08_p2_09_integration.py` verifies:

1. Runtime and Auto Review settings coexist after merge.
2. Auto Review SHADOW decisions never report a mutation.
3. ACTIVE remains rejected.
4. Auto Review routes are registered on the existing 8766 application.
5. No approve, reject, delete, execute or ACTIVE-enablement Auto Review route exists.
6. Codex Work Report and Web Capture MCP tools remain queue-first.
7. Pipeline and Queue use the same canonical idempotency material.
8. Desktop navigation contains five groups and the Auto Review page.
9. The Auto Review dashboard uses the shared polling hook.
10. The dashboard contains no execution endpoint and clearly states its SHADOW-only boundary.

## Authority guarantees

The combined tree preserves these boundaries:

- `MemoryReviewService` remains the owner review facade.
- `MemoryLifecycleService` remains the only lifecycle writer.
- Auto Review does not fabricate owner confirmation.
- Auto Review does not write Core Memory, candidates, Obsidian or Qdrant.
- MCP Work Reports are durable review inputs, not approvals.
- Desktop SHADOW controls do not expose execution actions.
- Unknown runtime values remain distinguishable from measured zero values.

## Integration CI status

Status at report creation: `INTEGRATION_TESTS_ADDED_AWAITING_GITHUB_ACTIONS`.

This report is committed on `work/p2-08-p2-09-integration-verification`. The pull request for this branch must pass the complete GitHub Actions suite before it is merged.

## Real-machine acceptance still required

GitHub-hosted tests cannot replace the following checks on the owner's Windows machine:

1. RTX 4060 telemetry success and failure paths.
2. Real `bge-m3` primary and `nomic-embed-text` fallback behavior.
3. Qdrant dimension mismatch and lexical fallback behavior.
4. Local Ollama Auto Review primary/fallback model roles.
5. 8766 token authentication from the Tauri application.
6. Desktop layout, page switching and hidden-window polling.
7. Verification that SHADOW evaluation changes no candidate, Obsidian file or Qdrant vector.

## Final classification

`IMPLEMENTED_MERGED_TO_FEATURE_BRANCH_AWAITING_INTEGRATION_CI_AND_REAL_MACHINE_ACCEPTANCE`
