# PROJECT_STATUS.md — LingJi Project Status

> Updated: 2026-07-20
> Branch: `feature/second-brain-memory`
> Architecture authority: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
> Execution roadmap: `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`

## 1. Current Product Direction

```text
src/
= long-term platform mainline

second_brain/
= compatibility, migration and acceptance runtime

desktop/lingji-control/
= only primary desktop UI
```

LingJi must converge into one private second brain and one shared memory system for all approved AI clients.

## 2. Data Authority

```text
Obsidian Vault + Git
= permanent memory and formal knowledge text

storage/raw
= original imported material

lingji_state.db
= runtime jobs, queue and audit events

lingji_memory.db
= rebuildable lexical and metadata index

Qdrant
= rebuildable semantic index
```

`second_brain.sqlite3` remains compatibility data during migration. It is not the long-term memory authority.

## 3. Verified Mainline Capabilities

`src/` currently provides:

- Obsidian single-Vault memory model
- rebuildable `lingji_memory.db`
- FTS5, BM25, trigram and Chinese short-term fallback retrieval
- project, tag, privacy, time and Agent Scope filtering
- Core Memory and owner-reviewed candidates
- Context Pack, citations and memory revision
- multi-AI profiles and MemoryGateway
- MCP and AI context adapters
- unified extraction queue, idempotency, leases, retries and raw snapshots
- Local Control API and Tauri UI
- hardware/GPU, model, media, backup, storage, skills, scheduler and opportunity services

## 4. Compatibility Capabilities Still To Migrate

`second_brain/` still contains migration evidence and capabilities that must be covered before retirement:

- structured sources, conversations and messages
- memory versions, relations and conflicts
- compatibility API and PySide6 acceptance flows
- existing Qdrant/embedding implementation used as migration reference

No new formal product capability should be added there.

## 5. P0-02 Port Contract

Repository implementation has landed:

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Implemented:

- `src/runtime/ports.py` validates the three-service contract
- `run_mcp_server.py` checks HTTP port availability before startup
- authenticated `GET /api/mcp/status` exposes configuration truth
- Tauri remains on `8766` only

Still pending:

- real Windows simultaneous binding
- full repository pytest
- Tauri real runtime smoke

Report: `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`

## 6. P0-03 Workspace And Capability Contract

Repository implementation has landed.

Implemented:

- one frozen `WorkspaceContext`
- one `WorkspaceResolver`
- production and acceptance physical path contracts
- isolated Vault, raw, state DB, memory DB, Qdrant path/collection, logs, cache, settings, queue DB, backups, derived files, temp and reports
- explicit rejection of unknown workspaces, path aliases, containment and Windows `C:` paths
- explicit `WorkspaceContext` seam in `build_memory_gateway()`
- directory-independent lexical Memory Capability Contract adapter

Validation state:

- isolated workspace contract suite: `8 passed`
- Python syntax validation: passed
- lexical capability contract against a full checkout: pending
- related memory regressions and full pytest: pending

Report: `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`

## 7. P1-01 Unified Embedding Provider

Repository implementation has landed in `src/model_center/embedding.py`.

Implemented:

- `EmbeddingProvider` and transport contracts
- Ollama `/api/embed` and older `/api/embeddings` compatibility
- primary/fallback model behavior
- batch embedding
- verified active-model and dimension state
- failure counters, timestamps and reset
- Settings/runtime override factory
- explicit configuration validation

Important status rule:

```text
configured model != verified active model
```

The provider reports `available=false` until a real embedding call succeeds.

Validation state:

- dependency-light fake-transport suite: `13 passed`
- real Ollama call: pending
- full repository pytest: pending

Report: `docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md`

## 8. P1-02 Qdrant SemanticProvider

Repository implementation has landed in the mainline.

Implemented:

- semantic search/index/diagnostic contracts
- `QdrantSemanticProvider`
- embedded, remote and in-memory modes
- WorkspaceContext collection/path isolation
- deterministic UUIDv5 point IDs
- batch upsert, chunk delete and memory delete
- search candidates without replacing HybridRetriever RRF
- count, kind count, exists, coverage and status
- dimension mismatch and `rebuild_required`
- payload text/body exclusion
- optional-dependency unavailable status
- real in-memory integration test suite

Validation evidence:

- Qdrant 1.12 direct in-memory API smoke passed for collection creation, upsert, filtered query, count, retrieve, ID delete and filter delete
- committed provider integration pytest: pending complete checkout execution
- full repository pytest: pending

Report: `docs/TEST_REPORTS/P1_02_QDRANT_SEMANTIC_PROVIDER_TEST_REPORT.md`

## 9. P1-03 MemoryIndexCoordinator

Repository implementation has landed in the P1-03 integration branch and is not connected to runtime startup yet.

Implemented:

- `MemoryIndexCoordinator`
- canonical chunk snapshots before and after lexical synchronization
- semantic added, updated and removed delta calculation
- metadata-aware semantic fingerprints
- bounded semantic upsert batches
- semantic delete for removed chunks
- full rebuild re-upsert of all current chunks
- lexical-only mode when no semantic provider exists
- structured `healthy`, `degraded` and `disabled` semantic status
- lexical success preserved when embedding or Qdrant fails
- optional state events for coordinated or degraded sync

Validation state:

- focused coordinator suite committed with 8 scenarios
- complete-checkout coordinator pytest: pending
- incremental retrieval regressions and full pytest: pending

Report: `docs/TEST_REPORTS/P1_03_MEMORY_INDEX_COORDINATOR_TEST_REPORT.md`

## 10. Current Critical Gaps

1. `src/gateway/bootstrap.py` still passes `semantic_provider=None`.
2. `MemoryGateway.rebuild()` still calls the lexical synchronizer directly instead of `MemoryIndexCoordinator`.
3. Full staged collection rebuild and validated collection switching are not implemented.
4. Semantic failure warnings are still suppressed by `HybridRetriever` rather than surfaced structurally.
5. Runtime Settings does not yet expose editable vector/workspace/MCP groups.
6. Local Control API does not expose unified vector status or coverage.
7. Brain Status may still report false zero memory/vector counts.
8. P0 and Phase 1 full local regression validation remains pending.

## 11. Development Freeze Rules

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only for migration blockers, compatibility reads, export and parity tests
- no direct Tauri calls to `8765` or `8767`
- no deletion of compatibility data before export, parity and rollback validation

## 12. Next Development Sequence

Current next task:

```text
P1-04 build_memory_gateway runtime wiring
```

Required work:

- resolve the selected WorkspaceContext
- construct the EmbeddingProvider from Settings/runtime values
- construct QdrantSemanticProvider only when semantic indexing is enabled
- inject the semantic provider into HybridRetriever
- inject MemoryIndexCoordinator into MemoryGateway
- preserve lexical-only startup when Qdrant, Ollama, a model or the dependency is unavailable
- close owned providers safely
- add integration tests proving lexical fallback and semantic activation

Then:

```text
P1-05 vector status, coverage, tests and final Phase 1 report
```

Do not start Memory Inspector before semantic runtime wiring and shared statistics exist.

## 13. Required Local Validation

```text
python -m pip install -r requirements.txt
python -m pytest tests/test_embedding_provider.py -v
python -m pytest tests/test_qdrant_semantic_provider.py -v
python -m pytest tests/test_memory_index_coordinator.py -v
python -m pytest tests/test_workspace_contract.py tests/test_memory_capability_contract.py -v
python -m pytest tests/test_incremental_index_sync.py tests/test_memory_retrieval.py -v
python -m pytest tests/ -v
```

No CI result currently proves these complete-checkout commands passed. Missing CI is not success.
