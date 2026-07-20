# PROJECT_STATUS.md — LingJi Project Status

> Generated: 2026-07-20
> Branch: feature/second-brain-memory
> Latest commit: 945f054 feat: add native second-brain desktop console

## Overall Status

The project consists of two independently operating systems running in parallel:

### PEMIS v6 (src/)

The background scheduler service is fully implemented:

| Component | Status | Notes |
|-----------|--------|-------|
| PEMISCore main loop | ✅ Implemented | In main.py, includes indexer + embedder + scheduler |
| PEMISIndex (indexer) | ✅ Implemented | Hash-based incremental indexing |
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
| Bounded watcher | ✅ Implemented | Polls 3 configured roots |
| PySide6 desktop | ✅ Implemented | Native Windows UI |
| Acceptance workspace | ✅ Implemented | Isolated test workspace |
| Dual runtime | ✅ Implemented | Production + acceptance via X-LingJi-Workspace header |

### Integration Points Remaining

- [ ] Activate bge-m3 embedding model (may need to pull in Ollama)
- [ ] VM-based Python MCP server (second_brain/mcp_server.py mentioned in AGENTS.md, not yet created)
- [ ] Periodic integration between PEMIS and second brain

## Test Report Summary

| Test File | Type | Coverage |
|-----------|------|----------|
| tests/test_second_brain.py | Integration | MemoryService, RetrievalService, VectorStore, duel import detection |
| tests/test_lingji_tools.py | Unit | All 17 LingJiTools methods, tool_result format, dry-run |
| tests/test_obsidian_cli.py | Unit | CLI invocation, config, encoding, timeout, dry-run |
| tests/test_desktop.py | Desktop | PySide6 UI acceptance |

## Known Issues

- Qdrant Docker service is **not running** on this machine; embedded Qdrant is the default
- bge-m3 may not be downloaded in Ollama; nomic-embed-text fallback covers this
- Initial Obsidian indexing can be slow (every MD doc needs an embedding)
