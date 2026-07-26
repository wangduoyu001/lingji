# Memory Inspector Code Analysis — Corrected Unified View

> Updated: 2026-07-20
> Branch: `feature/second-brain-memory`
> Status: Corrected after `src/` vs `second_brain/` capability audit
> Supersedes the earlier architectural conclusion that the Inspector should use `second_brain` as its permanent backend.

## 1. Correction Notice

The earlier analysis correctly located the working `second_brain` MemoryService, RetrievalService, SQLite, Qdrant and PySide6 paths.

Its architectural conclusion was incomplete because it analyzed the requested Second Brain modules without first comparing the newer `src` MemoryGateway, retrieval, extraction, MCP, control and Tauri platform.

The corrected conclusion is:

```text
src/
= long-term unified memory platform

second_brain/
= compatibility and migration runtime

Memory Inspector
= Tauri -> Local Control API :8766 -> src MemoryGateway and unified read models
```

The legacy paths remain relevant as migration sources and parity references, not as the final memory authority.

## 2. Verified Long-Term Entry Points

| Capability | Path / entry |
|---|---|
| Unified MemoryGateway | `src/gateway/memory_gateway.py::MemoryGateway` |
| Gateway assembly | `src/gateway/bootstrap.py::build_memory_gateway()` |
| AI profiles | `src/gateway/profiles.py::AIProfileRegistry` |
| Hybrid retrieval | `src/retrieval/hybrid.py::HybridRetriever` |
| Semantic interface | `src/retrieval/hybrid.py::SemanticProvider` |
| Rebuildable memory index | `src/retrieval/memory_db.py::MemoryDatabase` |
| Context Pack | `src/retrieval/context_pack.py::ContextPackBuilder` |
| Incremental synchronization | `src/retrieval/incremental_sync.py` |
| Permanent-memory lifecycle | `src/memory/lifecycle.py::MemoryLifecycleService` |
| State and audit events | `src/storage/state_db.py::StateDatabase` |
| Unified ingestion | `src/extraction/` |
| MCP | `src/mcp_server.py`, `run_mcp_server.py` |
| Local Control Service | `src/control/service.py::LocalControlService` |
| Local Control API | `src/control/api.py::create_control_app()` |
| Tauri UI | `desktop/lingji-control/src/` |

## 3. Verified Compatibility Entry Points

| Capability | Path / entry | Migration value |
|---|---|---|
| Legacy MemoryService | `second_brain/memory/service.py::MemoryService` | lifecycle and Qdrant synchronization reference |
| Legacy RetrievalService | `second_brain/retrieval/service.py::RetrievalService` | working exact + vector behavior reference |
| Compatibility SQLite | `second_brain/db.py` | sources, conversations, messages, versions, relations, conflicts |
| Qdrant | `second_brain/vector_store.py::VectorStore` | working provider implementation to adapt |
| Ollama embedding | `second_brain/embedding.py::OllamaEmbedder` | primary/fallback execution to adapt |
| Runtime assembly | `second_brain/runtime.py::build_runtime()` | dependency and acceptance reference |
| Workspace isolation | `second_brain/runtime_registry.py::RuntimeRegistry` | production/acceptance isolation pattern |
| Legacy API | `second_brain/api.py` | compatibility and migration reads |
| PySide6 UI | `second_brain/desktop/` | acceptance and diagnostic flow reference |

## 4. Permanent Memory Authority

`src/retrieval/memory_db.py` explicitly states that Obsidian is the canonical memory store and `lingji_memory.db` is rebuildable.

Final authority:

```text
Obsidian Vault + Git
= permanent memory and formal knowledge text

storage/raw
= original source archive

lingji_state.db
= task and audit state

lingji_memory.db
= rebuildable lexical and metadata index

Qdrant
= rebuildable semantic index
```

`second_brain.sqlite3` must not remain a second permanent-memory authority after migration.

## 5. Retrieval Comparison

### 5.1 `src` retrieval

`src/retrieval/hybrid.py` provides:

- FTS5/BM25 candidates through `MemoryDatabase`
- trigram and fallback tokenization
- optional SemanticProvider
- RRF fusion
- metadata boosts
- project, tag, status, privacy, time and Agent Scope filters
- citations and line ranges
- Core Memory and pin-to-context weighting

### 5.2 Current semantic gap

`src/gateway/bootstrap.py` currently passes:

```python
semantic_provider=None
```

Therefore unified Qdrant search is not yet connected.

### 5.3 `second_brain` retrieval value

`second_brain` already performs:

- Ollama query embedding
- Qdrant vector search
- embedded, remote and test modes
- collection dimension checks
- SQLite fallback

Its Qdrant and embedding code should be adapted into `src` as a SemanticProvider. Its simpler ranking formula must not replace the mature `src` RRF pipeline.

## 6. Correct Memory Inspector Backend

```text
Tauri Memory Inspector
  -> authenticated Local Control API :8766
  -> read-only Inspector facade in src
       -> MemoryGateway
       -> MemoryDatabase
       -> HybridRetriever
       -> Qdrant SemanticProvider
       -> source/revision/relation/conflict read models
  -> Obsidian/Git authority
```

Tauri must not directly call the compatibility API on `8765`.

## 7. Inspector Read Contract

The final read model should provide:

- canonical memory list and detail
- source path and citation lines
- lifecycle and owner-review state
- current memory revision
- relationships, revisions and conflict candidates
- lexical index state
- Qdrant state and per-item vector existence
- active and fallback embedding model
- current retrieval trace
- project, privacy, time and Agent Scope decisions
- workspace and storage state

Brain Status, Inspector and MCP must use the same statistics provider.

## 8. Search Trace Design

Normal and traced search use one internal pipeline.

Trace data may include:

- lexical and semantic channels
- lexical and semantic rank
- semantic similarity
- RRF contribution
- metadata boosts
- final retrieval score
- filters and rejection reasons
- citation
- warnings and degraded state

Historical explanations must not be fabricated from logs that did not store these facts.

## 9. Vector Read Design

The adapted provider needs read-only diagnostics:

- mode, path/URL and collection
- readiness and dimension
- model state
- counts by kind
- per-memory/per-chunk point existence
- missing and orphan points when detectable
- last write/query/rebuild when tracked
- dimension mismatch and rebuild requirement

Raw vectors are not displayed by default.

## 10. Source, Conversation and Message Migration

The structured tables in `second_brain` are valuable for audit and expansion.

The target read model must be:

- rebuildable from raw snapshots or Vault documents
- linked to stable source IDs
- privacy filtered
- explicit about model, role, ordinal, timestamp and attachment references
- treated as source evidence, not permanent personal memory

## 11. Relations, Versions and Conflicts

The compatibility tables provide useful query patterns.

The final unified model should derive from:

- Vault metadata and links
- Git/file history
- state and audit events
- deterministic rebuildable indexes

Conflict detection may create owner-review candidates. It must not automatically rewrite Core Memory.

## 12. Port Conflict

Current code defaults:

```text
second_brain FastAPI = 8765
src MCP Streamable HTTP = 8765
Local Control API = 8766
```

Target:

```text
8766 = Local Control API
8767 = optional MCP Streamable HTTP
stdio = default local MCP
```

The target remains planned until code and tests change the configuration.

## 13. Development Order

1. freeze duplicate legacy development
2. adapt Qdrant and embedding into `src`
3. add health, count, workspace and per-point contracts
4. implement the read-only Inspector facade in `src`
5. connect Local Control API
6. implement the Tauri page
7. migrate structured source and relation/conflict read models
8. run dual-read and compatibility-disabled tests
9. retire the legacy runtime only after parity, export and rollback validation

## 14. Testing Requirements

- stable IDs from the same Vault input
- lexical and semantic citations
- Qdrant outage fallback
- privacy and Agent Scope enforcement
- normal/trace result parity
- vector coverage for active/core memory
- source read-model rebuildability
- physical production/acceptance isolation
- Brain Status, Inspector and MCP statistic equality
- Tauri uses only `8766`
- all formal Inspector capabilities work with legacy runtime disabled after migration

## 15. Final Conclusion

The correct solution combines the strongest parts of both implementations:

```text
src platform, authority, retrieval fusion, permissions, MCP, tasks and Tauri
+
second_brain Qdrant, embedding, structured source and acceptance patterns
=
one unified private second brain
```

This is a migration into one architecture, not permanent coexistence and not immediate deletion.
