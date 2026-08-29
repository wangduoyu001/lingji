# Task8E Owner-Plain UI Repair Round 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist optional automatic-memory scan counts as real nullable evidence and project the same evidence shape through StateDB, ScanRun, Local Control API, and owner-facing Desktop UI.

**Architecture:** Keep the existing `automatic_memory_scans` table and scan lifecycle. Add nullable `queued_count`/`reused_count` columns, write them atomically only from completed measured scan results, and preserve NULL for failed, paused, crashed, legacy, or unmeasured rows. A single backend projector will produce list/summary/detail/action DTOs with `queued`, `reused`, and `counts_present`; Desktop will consume that presence contract without guessing.

**Tech Stack:** Python 3.12, SQLite, dataclasses, FastAPI, pytest, React/TypeScript, Playwright rendered fixture.

## Global Constraints

- Do not modify watcher strategy, add functionality, or touch live/Acceptance/Production/Vault data.
- Preserve old database rows as NULL after additive migration; never introduce a default zero for evidence columns.
- Keep internal arithmetic safe while preserving API presence semantics.
- Test-first: each new contract starts with a real failing test, then minimal implementation.
- Product/tests and docs/report are separate commits; final tree must be clean.

### Task 1: StateDB nullable count storage and migration

**Files:**
- Modify: `src/storage/state_db.py`
- Test: `tests/test_automatic_memory_source_registry.py` or a focused new backend test module

- [x] Add migration and CRUD assertions that old `automatic_memory_scans` schemas gain nullable `queued_count` and `reused_count`, existing rows remain NULL, and inserts/updates can persist explicit zero.
- [x] Run the focused test and observe RED on the missing columns/round-trip.
- [x] Add additive schema migration and parameterized scan writes without a `DEFAULT 0`.
- [x] Run migration/round-trip tests and confirm GREEN.

### Task 2: ScanRun and registry evidence boundary

**Files:**
- Modify: `src/automatic_memory/models.py`, `src/automatic_memory/source_registry.py`
- Test: focused source-registry tests

- [x] Add tests for registry-created scans and legacy rows proving NULL remains optional, explicit zero is present, and positive counts survive model conversion.
- [x] Run tests to obtain RED against required optional fields and evidence metadata.
- [x] Change `ScanRun.queued`/`reused` to optional values and make `_scan` derive `counts_present` from nullable persisted columns; keep unrelated fields compatible.
- [x] Run focused tests GREEN.

### Task 3: Reliable completion measurement and failure preservation

**Files:**
- Modify: `src/automatic_memory/scheduler.py`, `src/automatic_memory/source_registry.py`, and the existing snapshot completion seam only as required
- Test: scheduler/snapshot focused tests

- [x] Add tests covering completed empty scan (`0` present), positive scan, paused/failed/unmeasured NULL, and restart persistence; include 30%/70% failure paths.
- [x] Run tests and confirm RED because current completion paths do not persist optional counts.
- [x] Pass measured `queued`/`reused` through one atomic completion update; use NULL for incomplete/error paths and safe zero only for internal arithmetic.
- [x] Run focused scheduler/snapshot tests GREEN.

### Task 4: Unified Local Control API projector

**Files:**
- Modify: `src/control/automatic_memory_api.py`
- Test: `tests/test_automatic_memory_control_api.py` and rendered backend fixture support

- [x] Add API contract tests asserting list, summary.latest, detail, and action responses share count/presence semantics for NULL, explicit zero, and positive values.
- [x] Run contract tests to obtain RED from raw-row/asdict shape divergence.
- [x] Implement one scan DTO projector and route every scan response through it while preserving existing fields and timestamps.
- [x] Run API tests GREEN.

### Task 5: Backend-driven rendered parity and Desktop compatibility

**Files:**
- Modify: `desktop/lingji-control/src/pages/memorySourcesApi.ts`, `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`, `desktop/lingji-control/src/pages/OverviewPage.tsx`, `desktop/lingji-control/src/pages/memorySourcesTypes.ts`, existing rendered test fixture
- Test: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`

- [x] Add a fake backend scan DTO generated from the same response shape (not a hand-added UI-only marker) for missing, explicit zero, positive, and incomplete states; assert Home/list/detail parity and Chinese unknown rendering.
- [x] Run rendered E2E to obtain RED before adapting to the formal DTO.
- [x] Keep the existing shared presence helper, adapt it to the formal projector contract, and remove any fixture-only assumption.
- [x] Run E2E, 23-script smoke, and build GREEN.

### Task 6: Regression, docs, and commits

- [x] Run focused backend, Task2/3/4/5 direct regressions, compileall, diff-check, acceptance sync, and local handoff.
- [x] Update `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`, `docs/PROJECT_STATUS.md`, and `.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md` with Round4 RED/GREEN evidence and scope boundaries.
- [x] Commit product/tests separately from docs/report, verify clean status, and report exact SHAs and remaining owner observation only.
