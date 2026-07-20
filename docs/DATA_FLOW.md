# DATA_FLOW.md — LingJi Data Flow

> Generated: 2026-07-20

## Overview

LingJi has two independent data flows:

1. **PEMIS v6** — Vault Markdown → Index → Analysis → Opportunities → Dashboard
2. **Second Brain** — Inbox JSON/SQLite + Obsidian Markdown → Memories/Knowledge → Qdrant

## PEMIS v6 Data Flow

`	ext
Obsidian Vault (Markdown)
    │
    ▼
PEMISIndex (build_index / incremental)
    │
    ├──► pemis_index.json (storage/)
    │
    ▼
DecisionEngine (top-6 opportunities)
    │
    ├──► OppGenerator (scan → generate)
    │
    ▼
Dashboard (sync to vault)
    │
    ├──► PEMIS/opportunities/*.md
    ├──► PEMIS/dashboard/Control Center.md
    └──► PEMIS/status/ (system status)

Scheduler Jobs:
    read_feedback  ← Every 10 min ← Control Center feedback
    daily_capture  ← Every 24h    ← Capture new files + scan
    distill        ← Every 24h    ← Knowledge distillation
    integrity      ← Every 24h    ← Integrity check
    full_check     ← Every 24h    ← Update dashboard
`

## Second Brain Data Flow

`	ext
Input Sources:
    data/inbox/ai_chat/*.json
    data/inbox/codex_tasks/*.json
    Obsidian Knowledge Directory (configured)

    │
    ▼
BoundedWatcher (polls 3 roots every N seconds)
    │
    ▼
FastAPI (ingest endpoints)
    │
    ├──► ChatConnector → SQLite (conversations, messages)
    │   └──► DistillationService → Memory candidates → pending
    │
    ├──► CodexConnector → SQLite (memories)
    │
    └──► ObsidianConnector → SQLite (knowledge_documents)
        └──► Embedding → Qdrant

Retrieval:
    Query → RetrievalService
        ├──► SQLite keyword match (exact)
        └──► Qdrant semantic search (vector)
        └──► Combined ranked result
`

## Dual Workspace

- Production: data/second_brain.sqlite3, data/qdrant, data/raw, data/inbox
- Acceptance: data/acceptance/second_brain.sqlite3, data/acceptance/qdrant,
  data/acceptance/raw, data/acceptance/inbox

Workspace selected by X-LingJi-Workspace header.
Desktop defaults to acceptance; headerless API traffic stays production.
