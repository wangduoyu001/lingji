# CHANGELOG.md — LingJi (灵机) Project Changelog

> Format: [ISO date] Description (Author/Reference)

## 2026-07-20

- Add unified immutable `WorkspaceContext` and `WorkspaceResolver` for production/acceptance resources.
- Add physical path and Qdrant collection isolation validation, including Windows `C:` drive rejection.
- Add explicit workspace wiring seam to the formal `src` MemoryGateway bootstrap without migrating existing callers.
- Add directory-independent lexical Memory Capability Contract adapter and tests.
- Add P0-03 implementation and test report; full local memory regression remains pending.
- Fix conftest.py environment variable escapes (OBSIDIAN_VAULT_PATH, SECOND_BRAIN_OBSIDIAN_DIR)
- Update test results: 175 passed, 9 skipped for new tool modules
- Update PROJECT_STATUS.md with latest commit and test metrics
- Update second_brain_tools_review.md with actual integration test results
- Add Obsidian CLI abstraction layer (second_brain/obsidian_cli.py) — wraps official Obsidian.com CLI with subprocess, type-safe config, security guards
- Add LingJi Tools service layer (second_brain/lingji_tools.py) — unified tool service with frontmatter management and standardized response format
- Add comprehensive unit tests for both modules (test_lingji_tools.py, test_obsidian_cli.py)
- Add E2E brain status acceptance test (e2e_brain_status.mjs)
- Add tools review report (docs/TEST_REPORTS/second_brain_tools_review.md)

## 2026-07-19

- Add ObsidianCLI integration tests with encoding, timeout, dry-run, and safety
- Add LingJiTools service layer (17 methods) with unit tests
- Add LingJi Tool Service report and Obsidian CLI audit documents

## 2026-07-16

- Add native PySide6 Windows desktop console for second brain
- Add dual workspace (production + acceptance) runtime isolation
- Add acceptance automation for desktop validation
- Add fixed-script watcher controls (independent API/watcher start/stop)
- Desktop defaults to acceptance workspace; headerless API remains production
- Pre-upgrade backup created before second-brain development

## 2026-07-15

- Add isolated second-brain memory service (feature/second-brain-memory branch)
- Add embedded Qdrant as local vector cache (Docker not required)
- Add SQLite schema: sources, conversations, messages, memories, knowledge_documents
- Add FastAPI server on 127.0.0.1:8765 with /health and /memory/* endpoints
- Add bounded watcher (3 configured roots)
- Add Ollama embedding with bge-m3 primary and nomic-embed-text fallback
- Add AGENTS.md with project config and disk rules
- Initial worktree setup from upstream lingji.git master branch
