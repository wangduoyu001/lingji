# AI_CONTEXT.md — LingJi (灵机) Project AI Context

> Generated: 2026-07-20
> Source: codebase analysis

## Project Overview

LingJi (灵机) is a dual-layer AI system consisting of:

1. **PEMIS v6** — a profit-event monitoring and insight scheduler (background Python service)
2. **Second Brain** — a parallel memory and knowledge management service with a native Windows desktop client

The project lives entirely under **D:\codex\lingji-second-brain** on branch eature/second-brain-memory. The original LingJi PEMIS v4 project remains untouched at C:\Users\Administrator\Documents\New project-ai on branch master.

## AI Roles (per AGENTS.md)

- AI Director (AI编导)
- AI Operator (AI运营)
- AI Researcher (AI研究员)
- AI Business Planner (AI商业策划)
- AI Second Brain (AI第二大脑)

## Design Principles

| Principle | Meaning |
|-----------|---------|
| **Obsidian is SOURCE OF TRUTH** | No WebUI/Electron; Obsidian vault is the primary interface |
| **Metadata-only queries** | No reliance on file paths |
| **Interaction > Agent > Automation** | User experience first |
| **3-click rule** | Core operations in Obsidian within 3 clicks |
| **Capture First** | New files get classified/tagged/summarized before opportunity analysis |
| **AI must work proactively** | Auto-classify, tag, link, summarize |

## Key Architectural Decisions

- SQLite as structured source of truth; embedded Qdrant as a rebuildable vector cache
- Dual workspace (production + acceptance) for safe testing
- All runtime data on D: drive
- No modification to original LingJi project files
- PySide6 for desktop UI (no web tech)
- FastAPI on 127.0.0.1:8765 for second brain
- Bounded watcher — only 3 configured roots, no drive-wide scanning
- Windows-first: PowerShell scripts, native Obsidian CLI, .bat file launching

## Model Strategy

| Layer | Primary Model | Fallback Model | Notes |
|-------|--------------|----------------|-------|
| PEMIS v6 LLM | deepseek-chat (DeepSeek API) | qwen3:8b (Ollama) | Via .env key |
| Second Brain Embedding | bge-m3 (Ollama) | nomic-embed-text (Ollama) | bge-m3 may not be available |
| Original PEMIS v4 | deepseek-chat | qwen3:8b | In upstream project |

## Repository Structure

| Path | Purpose |
|------|---------|
| second_brain/ | Second-brain service, API, desktop, connectors |
| src/ | PEMIS v6 core: indexer, embedder, scheduler, security |
| 	ests/ | Unit and integration tests |
| scripts/ | PowerShell scripts for desktop setup, second brain management |
| data/ | Runtime data (gitignored) |
| PEMIS/ | Synced opportunity and dashboard Markdown |
