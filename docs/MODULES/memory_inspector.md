# LingJi Memory Inspector Design

> Status: Planned
> Module: Second Brain
> Goal: Make LingJi memory behavior visible and explainable.

## 1. Purpose

Memory Inspector is the visualization and debugging layer for LingJi memory.

It answers four questions:

1. What memories does LingJi have?
2. Where did each memory come from?
3. Why was a memory retrieved?
4. What is the current memory health state?

This module does not replace MemoryService or RetrievalService.
It only provides inspection and explanation.

## 2. Design Principles

- SQLite remains the structured source of truth.
- Qdrant remains the vector retrieval cache.
- Existing memory schema should not be changed.
- Reuse existing services.
- No duplicate memory logic.
- Keep implementation minimal.

## 3. Planned Architecture

```
Memory Inspector UI
        |
        v
Inspector API
        |
        +--> MemoryService
        |
        +--> RetrievalService
        |
        +--> SQLite
        |
        +--> Qdrant metadata
```

## 4. Core Features

### Memory List

Display:

- memory id
- title
- summary
- memory type
- source
- created time
- updated time
- importance
- embedding status

### Memory Detail

Display:

- complete content
- original source
- related memories
- vector status
- metadata
- version history

### Retrieval Trace

For a user query show:

```
Question
  |
  v
Retrieved memories
  |
  v
Similarity score
  |
  v
Retrieval explanation
```

Example fields:

- query
- matched memory id
- similarity score
- source
- reason

## 5. API Plan

Possible endpoints:

```
GET  /memory/inspector/list
GET  /memory/inspector/{id}
POST /memory/inspector/search
```

## 6. Development Requirements

Before implementation:

1. Read existing MemoryService and RetrievalService.
2. Confirm current database schema.
3. Research RAG tracing and memory visualization patterns.
4. Avoid architecture changes.

## 7. Acceptance Criteria

Feature is accepted when:

- User can browse stored memories.
- User can inspect memory source.
- User can see retrieval reasons.
- API tests pass.
- Existing tests remain passing.
- No database migration required.
- Documentation updated.

## 8. Future Extensions

Possible future additions:

- memory quality score
- duplicate detection
- memory decay
- manual memory approval workflow
