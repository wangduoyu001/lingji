# ARCHITECTURE.md — LingJi Unified Architecture

> Updated: 2026-07-20
> Status: Target architecture with explicit transition state
> Authoritative plan: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Product Definition

LingJi is one local-first private second brain, one shared memory system for approved AI clients, and one desktop control center.

The repository currently contains overlapping implementations, but they are not separate long-term products.

## 2. Long-Term Ownership

```text
src/
= long-term platform mainline
= ingestion, memory gateway, retrieval, MCP, control API, tasks and operations

second_brain/
= compatibility and migration runtime
= source of working Qdrant, embedding, structured conversation and acceptance patterns

desktop/lingji-control/
= only primary desktop UI

second_brain/desktop/
= acceptance, compatibility and emergency diagnosis only
```

New memory features, ingestion adapters and primary UI pages must not be developed in parallel implementations.

## 3. Data Authority

```text
Permanent memory and formal knowledge text
= Obsidian Vault + Git history

Original imported material
= configurable storage/raw archive

Runtime jobs, processing state and audit events
= lingji_state.db

Rebuildable lexical and metadata index
= lingji_memory.db

Rebuildable semantic index
= Qdrant

Structured source/conversation/message queries
= rebuildable derived read model
```

`lingji_memory.db` and Qdrant are indexes, not independent permanent-memory authorities.

`second_brain.sqlite3` remains a compatibility database during migration. It must not become a second long-term source of truth.

## 4. Target Runtime

```text
Input Sources
  -> src/extraction adapters
  -> persistent queue, idempotency, retries and privacy scan
  -> raw snapshot
  -> Vault source documents and memory candidates
  -> owner review
  -> permanent memory in Obsidian/Git
  -> incremental index synchronization

Obsidian Vault
  -> lingji_memory.db
       -> FTS5 / BM25 / trigram / metadata
  -> Qdrant SemanticProvider
       -> semantic chunks
  -> HybridRetriever
       -> RRF and metadata weighting
       -> privacy, project, tag, time and Agent Scope
  -> ContextPackBuilder
  -> Unified MemoryGateway
       -> MCP
       -> Local Control API
       -> internal jobs

Tauri Desktop
  -> authenticated Local Control API :8766
```

## 5. Current Verified Gap

`src/retrieval/hybrid.py` already supports an optional `SemanticProvider`, but `src/gateway/bootstrap.py` currently passes `semantic_provider=None`.

Therefore the current `src` retrieval path is primarily lexical and metadata based. Real Qdrant semantic retrieval still exists in `second_brain/` and must be adapted into `src`, not preserved as a second search stack.

## 6. Retrieval Target

```text
FTS5 / BM25 / Chinese substring fallback
+
Qdrant semantic search
+
metadata, privacy, time and Agent Scope filters
+
RRF and existing boosts
=
One retrieval pipeline
```

Qdrant failure must not disable lexical retrieval.

## 7. Port Contract

Target port map:

```text
8766 = Local Control API and Tauri gateway
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
```

Transition warning:

- `second_brain` FastAPI currently uses `8765`
- `src` currently defaults MCP HTTP to `8765`
- these services conflict when both use HTTP
- the conflict is not resolved until code and tests are updated
- Tauri must never call `8765` directly

## 8. UI Architecture

The final primary UI is `desktop/lingji-control/`.

It must expose truthful read models for:

- overview and service health
- memory inspector
- knowledge and Obsidian indexing
- sources and conversations
- tasks and structured progress
- vector center
- models, CPU and GPU
- AI clients, permissions and MCP
- opportunity system
- storage, backup and recovery
- settings
- logs and diagnostics

PySide6 may remain during migration for acceptance and diagnosis, but it must not receive new competing product features.

## 9. Workspace Isolation

Production and acceptance must physically isolate:

- Vault or fixture Vault
- raw archive
- state database
- memory index database
- Qdrant collection or path
- logs
- generated assets
- runtime settings

A request header alone does not provide physical isolation.

## 10. Migration Rules

1. Freeze new duplicate development in `second_brain/`.
2. Adapt Qdrant and embedding into `src` first.
3. Migrate structured source/conversation/message read models.
4. Migrate version, relation and conflict query capability.
5. Build Memory Inspector on the unified `src` MemoryGateway.
6. Run dual-read capability and data verification.
7. Stop legacy writes, preserve read-only compatibility, then retire the old runtime.

Direct deletion of `second_brain/` or its database is forbidden before parity, export and rollback checks pass.

## 11. References

- `docs/TECH_RESEARCH/SRC_SECOND_BRAIN_CAPABILITY_AUDIT.md`
- `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
- `docs/MODULES/UNIFIED_DESKTOP_UI_PLAN.md`
- `docs/MEMORY_SYSTEM.md`
- `docs/VECTOR_DATABASE.md`
