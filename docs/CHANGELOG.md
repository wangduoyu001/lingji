# CHANGELOG.md — LingJi (灵机) Project Changelog

> Format: [ISO date] Description (Author/Reference)

## 2026-07-20

- Complete real Windows P1-05 acceptance on commit `9ab3c55074b0e56dac9ac8adccba934627bedd90`.
- Validate Ollama 0.32.0 with `bge-m3` at an actual dense-vector dimension of 1024.
- Validate in-memory and temporary embedded-disk Qdrant with full 2/2 vector coverage.
- Validate `/api/memory/status`, `/api/vector/status`, `/api/vector/coverage` and `/api/brain/status` against live data.
- Record focused Phase 1 suites as passed and full repository results as `244 passed, 2 known pre-existing failures, 9 optional skips`.
- Add `docs/TEST_REPORTS/P1_05_LOCAL_ACCEPTANCE_SUMMARY.md` and finalize the P1-05 report and project status.
- Migrate the compatibility Ollama embedding behavior into `src/model_center/embedding.py` with provider, fallback, batch and verified-state contracts.
- Migrate Qdrant search/index/diagnostic capabilities into `src/retrieval/qdrant_provider.py` with Workspace isolation.
- Add `MemoryIndexCoordinator` for lexical-first, semantic-degraded-safe synchronization.
- Wire Embedding, Qdrant, HybridRetriever and MemoryIndexCoordinator into the formal MemoryGateway runtime.
- Add truthful `MemoryStatisticsService` and atomic workspace status snapshots.
- Add authenticated `/api/memory/status`, `/api/vector/status` and `/api/vector/coverage` endpoints on Local Control API port 8766.
- Fix Brain Status false-zero behavior; unknown memory/vector counts now remain explicit unknown values.
- Route MCP-written documents through coordinated lexical/vector indexing instead of the former SQLite-only side path.
- Add isolated P1-05 local acceptance script with temporary acceptance Workspace and in-memory Qdrant.
- Add unified immutable `WorkspaceContext` and `WorkspaceResolver` for production/acceptance resources.
- Add physical path and Qdrant collection isolation validation, including Windows `C:` drive rejection.
- Add explicit workspace wiring seam to the formal `src` MemoryGateway bootstrap without migrating existing callers.
- Add directory-independent lexical Memory Capability Contract adapter and tests.
- Add P0-03 implementation and test report.
- Fix conftest.py environment variable escapes (OBSIDIAN_VAULT_PATH, SECOND_BRAIN_OBSIDIAN_DIR).
- Update test results: 175 passed, 9 skipped for new tool modules.
- Update PROJECT_STATUS.md with latest commit and test metrics.
- Update second_brain_tools_review.md with actual integration test results.
- Add Obsidian CLI abstraction layer (`second_brain/obsidian_cli.py`) with subprocess, type-safe config and security guards.
- Add LingJi Tools service layer (`second_brain/lingji_tools.py`) with unified tool service and standardized response format.
- Add comprehensive unit tests for both modules.
- Add E2E brain status acceptance test (`e2e_brain_status.mjs`).
- Add tools review report (`docs/TEST_REPORTS/second_brain_tools_review.md`).

## 2026-07-19

- Add ObsidianCLI integration tests with encoding, timeout, dry-run, and safety.
- Add LingJiTools service layer with 17 methods and unit tests.
- Add LingJi Tool Service report and Obsidian CLI audit documents.

## 2026-07-16

- Add native PySide6 Windows desktop console for second brain.
- Add dual workspace production and acceptance runtime isolation.
- Add acceptance automation for desktop validation.
- Add fixed-script watcher controls for independent API/watcher start and stop.
- Desktop defaults to acceptance workspace; headerless API remains production.
- Create pre-upgrade backup before second-brain development.

## 2026-07-15

- Add isolated second-brain memory service on `feature/second-brain-memory`.
- Add embedded Qdrant as local vector cache without requiring Docker.
- Add SQLite schema for sources, conversations, messages, memories and knowledge documents.
- Add FastAPI server on `127.0.0.1:8765` with health and memory endpoints.
- Add bounded watcher with three configured roots.
- Add Ollama embedding with bge-m3 primary and nomic-embed-text fallback.
- Add `AGENTS.md` with project configuration and disk rules.
- Initial worktree setup from upstream `lingji.git` master branch.
