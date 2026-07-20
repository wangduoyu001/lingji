# CHANGELOG.md — LingJi (灵机) Project Changelog

> Format: [ISO date] Description (Author/Reference)

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
- Pre-upgrade backup created at D:\codex\backups\lingji-second-brain\20260715-225503

## 2026-07-15

- Add isolated second-brain memory service (feature/second-brain-memory branch)
- Add embedded Qdrant as local vector cache (Docker not required)
- Add SQLite schema: sources, conversations, messages, memories, knowledge_documents
- Add FastAPI server on 127.0.0.1:8765 with /health and /memory/* endpoints
- Add bounded watcher (3 configured roots)
- Add Ollama embedding with bge-m3 primary and nomic-embed-text fallback
- Add AGENTS.md with project config and disk rules
- Initial worktree setup from upstream lingji.git master branch
