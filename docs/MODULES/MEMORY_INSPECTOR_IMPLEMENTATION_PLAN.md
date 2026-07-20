# LingJi Memory Inspector Implementation Plan

Status: Ready for Development
Module: Second Brain

## Goal

Implement the first usable Memory Inspector without changing existing memory architecture.

The feature must make memory behavior visible:

1. What memories exist
2. Where memories come from
3. Why memories are retrieved
4. Current memory status

## Development Order

### Phase 1: Code Understanding

Before coding:

- Locate MemoryService implementation
- Locate RetrievalService implementation
- Confirm SQLite schema
- Confirm Qdrant integration
- Confirm API registration
- Confirm UI integration point

No guessing paths.

## Phase 2: Backend

Create a lightweight inspection layer.

Responsibilities:

- Read memory information
- Read metadata
- Read retrieval trace
- Return inspection data

Do not:

- Write memories
- Change memory schema
- Duplicate retrieval logic

## Phase 3: API

Add:

GET /memory/inspector/list

GET /memory/inspector/{id}

POST /memory/inspector/search

Requirements:

- Clear JSON format
- Error handling
- Existing API style compatibility

## Phase 4: UI

Display:

- Memory count
- Memory list
- Source information
- Detail panel
- Retrieval explanation

Prefer existing desktop/UI framework.

Do not create a second dashboard system.

## Testing

Required:

- List memories
- View memory detail
- Search retrieval trace
- Missing memory handling
- Qdrant unavailable fallback

Run existing tests after changes.

## Acceptance

Accepted when:

- User can visually inspect memories
- User can understand retrieval reasons
- No database migration exists
- Existing tests pass
- Documentation updated
- Git commit created

## Future

Not included in this phase:

- Automatic memory deletion
- Memory scoring optimization
- Autonomous memory rewriting
- Large UI redesign
