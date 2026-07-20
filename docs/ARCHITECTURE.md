# ARCHITECTURE.md — LingJi (灵机) System Architecture

> Generated: 2026-07-20
> Version: 0.2.0 (second brain)

## Overview

LingJi uses a four-layer architecture (Data → Index → Logic → Ops), with the second-brain service running in parallel as an isolated memory and knowledge management layer.

## High-Level Diagram

`	ext
┌─────────────────────────────────────────────────────────────────┐
│                    L4: Operations Layer                         │
│   backup.py   journal   integrity check   metrics   dashboard   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    L3: Logic Layer (Lightweight)                 │
│   PEMISCore  CronScheduler  SafetyGuard  DecisionEngine         │
│   OppGenerator  UserFeedback  LingJiTools  ObsidianCli           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    L2: Index Layer (Rebuildable)                 │
│   PEMISIndex (pemis_index.json)                                 │
│   Qdrant Vector DB (memory + knowledge embeddings)             │
│   SQLite (conversations, memories, knowledge_documents)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    L1: Data Layer (Immutable Source of Truth)    │
│   Obsidian Vault (Markdown)   AI Chat JSON   Codex Task JSON    │
│   Second Brain Raw Archive (data/raw/ai_chat)                   │
└─────────────────────────────────────────────────────────────────┘
`

## Second Brain Architecture

`	ext
  ┌──────────────────────────────┐
  │   Bounded Watcher            │
  │   ─ Polls 3 roots ───────────│
  │                              │
  │   data/inbox/ai_chat/*.json  ￫  ChatConnector → SQLite
  │   data/inbox/codex_tasks/*.json ￫  CodexConnector → SQLite
  │   Obsidian knowledge dir     ￫  ObsidianConnector → SQLite
  └──────────────────────────────┘
                │
  ┌─────────────▼──────────────┐
  │   FastAPI (127.0.0.1:8765) │
  │   Runtime                  │
  │   ┌──────────────────────┐ │
  │   │ MemoryService        │ │  CRUD + versioning + supersede
  │   │ RetrievalService     │ │  Semantic + exact search
  │   │ DistillationService  │ │  Extract memories from chats
  │   │ ConflictService      │ │  Resolve memory conflicts
  │   │ ChatConnector        │ │  Import AI conversations
  │   │ CodexConnector       │ │  Import Codex task records
  │   │ ObsidianConnector    │ │  Index knowledge (no distill)
  │   └──────────────────────┘ │
  └─────────────┬──────────────┘
                │
  ┌─────────────▼──────────────┐
  │   SQLite (structured truth) │
  │   Embedded Qdrant (vectors) │
  └────────────────────────────┘
                │
  ┌─────────────▼──────────────┐
  │   PySide6 Desktop App     │
  │   (灵机第二大脑)           │
  │   Acceptance workspace    │
  └────────────────────────────┘
`

## PEMIS v6 Architecture

`	ext
  PEMISCore(main.py)
    ├─ PEMISIndex — hash-based incremental file indexing
    ├─ Embedder — Ollama embeddings with primary/fallback
    ├─ CronScheduler — jobs: distill / integrity / full_check / read_feedback / daily_capture
    ├─ SafetyGuard — NORMAL / DEGRADED / SAFE_MODE / RECOVERY_MODE
    ├─ DecisionEngine — generate top-6 opportunities
    ├─ OppGenerator — scan vault, produce opportunity Markdown
    ├─ UserFeedback — read Control Center feedback
    ├─ Dashboard — sync opportunities to vault
    └─ Watchdog — file change → incremental reindex + re-decide
`

## Key Design Decisions

- **Dual workspace**: Production and acceptance are physically separated directories
- **SQLite as truth**: Qdrant can be wiped and rebuilt from SQLite
- **No WebUI**: Obsidian is the primary user interface; PySide6 desktop for second brain
- **Isolation**: Second brain does not modify PEMIS v6 files or startup chain
- **File-driven execution**: PowerShell scripts for management, not interactive shells
