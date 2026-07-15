# Architecture

```text
AI chat inbox -> raw archive -> normalized conversations/messages
              -> deterministic candidate extraction -> review -> memories (SQLite)

Explicit Obsidian directory -> versioned knowledge_documents (SQLite)

active memories + knowledge documents -> embedded Qdrant cache
SQLite exact lookup + Qdrant semantic recall -> retrieval/context API

bounded watcher -> localhost API only
```

FastAPI listens on `127.0.0.1:8765`. The API is the sole owner of the embedded Qdrant path. The watcher is an optional, separately stoppable process.
