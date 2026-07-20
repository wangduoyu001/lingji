# ROADMAP.md — LingJi Project Roadmap

> Generated: 2026-07-20

## Completed (v0.2.0)

- [x] PEMIS v6 core scheduler (indexer, embedder, cron, safety, decisions)
- [x] Opportunity generator with MoneyScore
- [x] Obsidian Control Center dashboard sync
- [x] User feedback reading from Control Center
- [x] Code and data backup system
- [x] Second brain FastAPI service (SQLite + embedded Qdrant)
- [x] Memory CRUD with versioning and supersede
- [x] Semantic retrieval (SQLite + Qdrant)
- [x] Distillation from conversations to memories
- [x] Conflict detection and resolution
- [x] Chat, Codex, and Obsidian connectors
- [x] Bounded watcher (3 roots)
- [x] Native PySide6 Windows desktop client
- [x] Dual workspace (production + acceptance)
- [x] LingJi Tools layer (17 methods wrapping Obsidian CLI)
- [x] ObsidianCLI with encoding, timeout, dry-run, safety
- [ ] Acceptance tests for desktop Qt navigation

## In Progress

- [ ] Activate bge-m3 embedding model in Ollama
- [ ] Integration tests linking PEMIS and second brain
- [ ] VM-based Python MCP server (second_brain/mcp_server.py)

## Planned

- [ ] Periodic sync between PEMIS decisions and second brain memories
- [ ] Automated memory review workflow in Obsidian
- [ ] Watcher auto-start on desktop launch (toggle)
- [ ] Scheduled task registration for second brain (optional)
- [ ] Multi-language support for knowledge indexing
