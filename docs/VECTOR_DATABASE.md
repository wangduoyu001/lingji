# VECTOR_DATABASE.md — LingJi Vector Database Strategy

> Generated: 2026-07-20

## Current State

The second brain uses **embedded Qdrant** as its vector database. No Docker service is required.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| SECOND_BRAIN_QDRANT_PATH | data/qdrant | Local filesystem path for embedded Qdrant |
| SECOND_BRAIN_QDRANT_URL | (empty) | Remote Qdrant URL (alternative to local) |
| SECOND_BRAIN_QDRANT_COLLECTION | lingji_memories_v1 | Collection name |

When SECOND_BRAIN_QDRANT_URL is set and non-empty, the client connects to a remote
Qdrant instance. Otherwise, local embedded Qdrant is used.

For testing, the Qdrant path can be set to :memory: for in-memory mode.

## Vector Store Details

`python
# From vector_store.py
class VectorStore:
    def __init__(self, collection, path=None, url=""):
        # If url is set → remote Qdrant client
        # If path is ":memory:" → in-memory Qdrant
        # Otherwise → file-based embedded Qdrant at path
`

## PEMIS v6 Vector Strategy

The PEMIS v6 src/dashboard.py has a reserved vector store interface comment block.
Qdrant integration is prepared in code but **not activated** in the current PEMIS v6 flow.
PEMIS v6 uses file-based indexing (pemis_index.json) for opportunity management.

## Rebuild Strategy

Qdrant is considered a **cache**. It can be deleted and rebuilt from:
- SQLite active memories (second brain)
- SQLite knowledge_documents (second brain)

SQLite and raw archives are the canonical sources of truth.

## Chunking

Text is chunked before embedding (from chunking.py):
- Default max chunk size: 1500 characters
- Overlap: 150 characters
- Chunks at paragraph boundaries when possible

## Embedding

All vectors use Ollama embedding models (bge-m3 primary, nomic-embed-text fallback).
