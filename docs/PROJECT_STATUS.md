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

## 5. P0 Runtime Contracts

### P0-02 Port Contract

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Repository implementation has landed. Real Windows simultaneous binding, full pytest and Tauri runtime smoke remain pending.

Report: `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`

### P0-03 Workspace And Capability Contract

Implemented:

- one frozen `WorkspaceContext`
- one `WorkspaceResolver`
- production and acceptance physical path contracts
- isolated Vault, raw, SQLite, Qdrant, logs, cache, settings, queue, backups, derived, temp and reports
- lexical Memory Capability Contract

Validation evidence:

- workspace contract: `8 passed`
- Python syntax validation: passed
- complete-checkout lexical contract and full pytest: pending

Report: `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`

## 6. P1-01 Unified Embedding Provider

Implemented in `src/model_center/embedding.py`:

- Provider and transport contracts
- Ollama modern and compatibility endpoints
- primary/fallback model behavior
- batch embedding
- verified active model and dimension
- failure state and reset
- Settings/runtime factory
- configuration validation

A configured model is not reported as active before a successful call.

Validation evidence:

- fake-transport suite: `13 passed`
- real Ollama and full pytest: pending

Report: `docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md`

## 7. P1-02 Qdrant SemanticProvider

Implemented in `src/retrieval/qdrant_provider.py`:

- search/index/diagnostic contracts
- embedded, remote and in-memory modes
- Workspace collection/path isolation
- deterministic UUIDv5 point IDs
- upsert, delete, count, exists, coverage and status
- dimension mismatch and rebuild-required state
- payload body exclusion
- optional-dependency unavailable state

Validation evidence:

- Qdrant 1.12 direct in-memory API smoke passed
- committed provider pytest and full pytest: pending

Report: `docs/TEST_REPORTS/P1_02_QDRANT_SEMANTIC_PROVIDER_TEST_REPORT.md`

## 8. P1-03 MemoryIndexCoordinator

Implemented in `src/retrieval/index_coordinator.py` and merged into the mainline:

- canonical before/after chunk snapshots
- added, updated and removed semantic delta
- metadata-aware semantic fingerprints
- bounded upsert batches
- semantic delete
- force rebuild re-upsert
- lexical-only mode
- structured healthy/degraded/disabled result
- lexical commit preserved after semantic failure

Validation state:

- focused coordinator suite committed with 8 scenarios
- complete-checkout coordinator pytest and full regression: pending

Report: `docs/TEST_REPORTS/P1_03_MEMORY_INDEX_COORDINATOR_TEST_REPORT.md`

## 9. P1-04 Semantic Runtime Wiring

Repository implementation has landed in the P1-04 integration branch.

The formal runtime now builds one semantic chain:

```text
EmbeddingProvider
  -> QdrantSemanticProvider
  -> HybridRetriever
  -> MemoryIndexCoordinator
  -> MemoryGateway
```

Implemented:

- `build_memory_gateway()` constructs Workspace-aware providers
- the same Qdrant provider is injected into retrieval and synchronization
- `MemoryGateway.rebuild()` routes through MemoryIndexCoordinator
- semantic runtime can be explicitly disabled
- provider/configuration failure returns a lexical-only gateway
- existing production Vault and SQLite paths remain the transition mapping
- explicit acceptance Workspace remains physically isolated
- runtime warnings are available from memory health
- Gateway owns and closes created providers
- lexical capability tests explicitly disable semantic requirements

Validation state:

- runtime wiring suite committed with 6 focused scenarios
- complete-checkout P1-04 pytest: pending
- real Ollama + Qdrant runtime: pending
- full pytest: pending

Report: `docs/TEST_REPORTS/P1_04_SEMANTIC_RUNTIME_WIRING_TEST_REPORT.md`

## 10. Current Critical Gaps

1. Local Control API does not yet expose truthful vector status or coverage.
2. Brain Status may still report false zero memory/vector counts.
3. Runtime Settings does not yet expose editable vector/workspace/MCP groups.
4. Search-time semantic failures are not yet returned as structured query warnings.
5. Full staged collection rebuild and validated collection switching are not implemented.
6. Phase 1 complete-checkout regression and real local runtime validation remain pending.

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
P1-05 vector status, coverage and Phase 1 validation
```

Required work:

- add one shared MemoryStatisticsService
- expose real memory, embedding and Qdrant state
- expose vector coverage through Local Control API on 8766
- fix Brain Status false-zero behavior
- keep Tauri away from direct Qdrant access
- run focused and full local validation
- publish the final Phase 1 report

Do not start the full Memory Inspector before shared statistics and Phase 1 validation exist.

## 13. Required Local Validation

```text
python -m pip install -r requirements.txt
python -m pytest tests/test_embedding_provider.py -v
python -m pytest tests/test_qdrant_semantic_provider.py -v
python -m pytest tests/test_memory_index_coordinator.py -v
python -m pytest tests/test_semantic_runtime_wiring.py -v
python -m pytest tests/test_workspace_contract.py tests/test_memory_capability_contract.py -v
python -m pytest tests/test_incremental_index_sync.py tests/test_memory_retrieval.py -v
python -m pytest tests/ -v
```

No CI result currently proves these complete-checkout commands passed. Missing CI is not success.
