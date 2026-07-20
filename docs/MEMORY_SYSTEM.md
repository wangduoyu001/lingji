# MEMORY_SYSTEM.md — LingJi Memory System

> Generated: 2026-07-20
> Version: 0.2.0 (second brain)

## Overview

The second brain maintains an isolated memory system separate from PEMIS v6. It stores
traceable AI-chat archives and reviewable structured memories. Obsidian Markdown is
indexed as formal knowledge but never auto-distilled into memories.

## Data Flow

```
AI Chat JSON → Raw Archive → ChatConnector → SQLite (conversations/messages)
                                    → MemoryService (extract → pending memories)
                                    → DistillationService (review → active memories)

Codex Task JSON → CodexConnector → SQLite (memories)

Obsidian Markdown → ObsidianConnector → SQLite (knowledge_documents, no distill)

Active Memories + Knowledge → Embedding → Qdrant Vector Store (rebuildable cache)
```

## Memory Lifecycle

1. **Import** — Raw JSON files placed in inbox directories are detected by the watcher or ingested via API
2. **Extract** — Memory candidates are generated from conversations by distillation
3. **Pending** — Important memories start as `pending` and require explicit approval
4. **Active** — Approved memories become `active` and are embedded in Qdrant
5. **Superseded** — Newer knowledge can supersede old memories (version history retained)
6. **Conflicted** — Contradictory memories are flagged for review
7. **Rejected / Archived / Deleted** — Terminal states for irrelevant or removed memories

## Memory Types

| Type | Description | Auto-Approved |
|------|-------------|---------------|
| RULE | Directives and guidelines | No |
| FACT | Verifiable facts | No |
| DECISION | Past decisions and rationale | No |
| PREFERENCE | User preferences | No |
| INSIGHT | Derived insights | No |
| KNOWLEDGE | Knowledge documents (from Obsidian) | Yes (indexed, not distilled) |

## SQLite Schema

Core tables: `sources`, `projects`, `conversations`, `messages`, `memories`,
`memory_versions`, `knowledge_documents`, `knowledge_chunks`, `distillation_log`.

SQLite is the source of truth. Qdrant is a rebuildable cache.

## Vector Store

Embedded Qdrant (no Docker required). Collection: `lingji_memories_v1`.
Can use `:memory:` for testing, local path for production, or remote URL.

## Chunking

Text is split into overlapping chunks (default 1500 chars, 150 overlap) for embedding.
Knowledge documents and memories are chunked independently.
