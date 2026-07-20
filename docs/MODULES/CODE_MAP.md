# LingJi Code Map

> Purpose: provide AI and developers with a fast project entry map before code changes.
>
> Rule: do not create new modules based only on feature names. Confirm existing entry points before development.

## Architecture Entry

Current architecture:

```
Data Layer
  ↓
Index Layer
  ↓
Logic Layer
  ↓
Ops Layer
```

Second Brain runs as an isolated memory and knowledge layer.

Reference:
- docs/ARCHITECTURE.md
- docs/MEMORY_SYSTEM.md
- docs/VECTOR_DATABASE.md

## Second Brain Runtime Map

Runtime entry:

```
FastAPI Runtime
127.0.0.1:8765
```

Core services:

```
MemoryService
- Memory CRUD
- Version management
- Supersede handling

RetrievalService
- Semantic search
- Exact search

DistillationService
- Memory extraction

ConflictService
- Memory conflict handling

ChatConnector
- AI conversation import

CodexConnector
- Codex task import

ObsidianConnector
- Knowledge indexing
```

## Storage Map

Source of truth:

```
SQLite
├── conversations
├── memories
└── knowledge_documents
```

Vector index:

```
Qdrant
- Memory embeddings
- Knowledge embeddings
```

Design rule:
SQLite is authoritative. Qdrant can be rebuilt.

## UI Map

Desktop:

```
PySide6 Desktop App
```

Purpose:

- Second Brain acceptance workspace
- Runtime status display
- Memory interaction

## Development Before Coding Checklist

Before modifying code:

1. Confirm current branch.
2. Confirm latest commit.
3. Read relevant docs.
4. Locate existing service/class/function.
5. Confirm API registration point.
6. Confirm test location.

## Missing Detailed Paths

This document intentionally does not invent file paths.

When a module path changes, update this file with the real implementation location after verification.

Required additions for future maintenance:

- MemoryService source file
- RetrievalService source file
- FastAPI router file
- Desktop UI entry file
- Test file mapping
