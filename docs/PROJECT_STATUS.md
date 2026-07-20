# PROJECT_STATUS.md — LingJi Project Status

> Generated: 2026-07-20
> Branch: feature/second-brain-memory
> Latest commit: 21fe687 docs: add efficient task routing requirement

## Overall Status

The project consists of two independently operating systems running in parallel:

### PEMIS v6 (src/)

The background scheduler service is fully implemented:

| Component | Status | Notes |
|-----------|--------|-------|
| PEMISCore main loop | ✅ Implemented | In main.py, includes indexer + embedder + scheduler |
| Embedder | ✅ Implemented | Ollama-based with fallback chain |
| Cron scheduler | ✅ Implemented | distill/integrity/full_check/read_feedback/daily_capture |
| SafetyGuard | ✅ Implemented | NORMAL / DEGRADED / SAFE_MODE / RECOVERY_MODE |
| DecisionEngine | ✅ Implemented | Top-6 opportunity decision |
| OppGenerator | ✅ Implemented | Scan and generate from vault |
| UserFeedback | ✅ Implemented | Reads from Control Center |
| Dashboard | ✅ Implemented | Syncs opportunities to vault |
| Backup | ✅ Implemented | backup.py — code + data backup to D: |

### Second Brain (second_brain/)

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI server | ✅ Implemented | On 127.0.0.1:8765 |
| SQLite schema | ✅ Implemented | sources, conversations, messages, memories, knowledge_documents |
| Embedded Qdrant | ✅ Implemented | :memory: or local path; remote URL also supported |
| Ollama embedder | ✅ Implemented | bge-m3 -> nomic-embed-text fallback |
| Memory service | ✅ Implemented | CRUD + versioning + supersede |
| Retrieval service | ✅ Implemented | Semantic search via Qdrant + SQLite fallback |
| Distillation | ✅ Implemented | Extracts memories from conversations |
| Conflict resolution | ✅ Implemented | Detects and resolves memory conflicts |
| Chat connector | ✅ Implemented | Imports AI chat conversations |
| Codex connector | ✅ Implemented | Imports Codex task records |
| Obsidian connector | ✅ Implemented | Indexes Markdown knowledge without auto-distilling |
| Obsidian CLI tools | ✅ Implemented | Wraps official Obsidian.com CLI via subprocess (obsidian_cli.py) |
| LingJi Tools | ✅ Implemented | Unified tool service layer with frontmatter (lingji_tools.py) |
| Bounded watcher | ✅ Implemented | Polls 3 configured roots |
| PySide6 desktop | ✅ Implemented | Native Windows UI |
| Acceptance workspace | ✅ Implemented | Isolated test workspace |
| Dual runtime | ✅ Implemented | Production + acceptance via X-LingJi-Workspace header |

### Integration Points Remaining

- [ ] Activate bge-m3 embedding model (may need to pull in Ollama)
- [ ] VM-based Python MCP server (second_brain/mcp_server.py mentioned in AGENTS.md, not yet created)
- [ ] Periodic integration between PEMIS and second brain

## Test Report Summary

| Test File | Type | Tests | Status |
|-----------|------|-------|--------|
| tests/test_lingji_tools.py | Unit | 38 | 38 passed |
| tests/test_obsidian_cli.py | Unit | 22 | 22 passed |
| Full suite (excluding env-dep modules) | Integration | 169 | 160 passed, 9 skipped |
| tests/test_second_brain.py | Integration | — | Requires qdrant_client |
| tests/test_desktop.py | Desktop | — | Requires PySide6 |

## Known Issues

- Qdrant Docker service is **not running** on this machine; embedded Qdrant is the default
- bge-m3 may not be downloaded in Ollama; nomic-embed-text fallback covers this
- Initial Obsidian indexing can be slow (every MD doc needs an embedding)
- 6 pre-existing collection errors: 4 tests need PEMISIndex (removed in merge), 1 needs PySide6, 1 needs qdrant_client
