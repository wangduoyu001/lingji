# P1-04 Semantic Runtime Wiring Test Report

Updated: 2026-07-20
Branch: `work/p1-04-semantic-runtime-wiring`
Base: `5cafe4285a903dd9e98a1dd26f7bd326379d7dfb`
Status: repository implementation complete; complete-checkout pytest and real local runtime validation pending

## 1. Goal

Connect the unified EmbeddingProvider, QdrantSemanticProvider and MemoryIndexCoordinator to the formal `build_memory_gateway()` runtime while preserving lexical-only startup and search when semantic components fail.

## 2. Runtime Flow

```text
Settings + optional runtime values
  -> existing or explicit WorkspaceContext
  -> build_embedding_provider()
  -> QdrantSemanticProvider
  -> HybridRetriever.semantic_provider
  -> MemoryIndexCoordinator.semantic_provider
  -> MemoryGateway
```

One semantic provider instance is shared by retrieval and index synchronization. No second ranking or permission path is introduced.

## 3. Implemented

Modified `src/gateway/bootstrap.py`:

- accepts optional runtime override values
- resolves an explicit WorkspaceContext when supplied
- retains current production Vault and SQLite paths when no explicit workspace is supplied
- builds the EmbeddingProvider
- builds the QdrantSemanticProvider
- injects the same provider into HybridRetriever and MemoryIndexCoordinator
- records structured bootstrap degradation warnings
- preserves lexical-only startup after configuration or dependency failure
- allows semantic runtime to be explicitly disabled
- owns and closes created providers

Modified `src/gateway/memory_gateway.py`:

- stores one `MemoryIndexCoordinator`
- routes rebuild and incremental synchronization through the coordinator
- stores the active WorkspaceContext
- exposes runtime warnings through memory health
- closes owned runtime resources safely

Modified `src/config.py`:

```text
semantic_enabled
semantic_batch_size
qdrant_distance
qdrant_timeout_seconds
qdrant_collection_schema
```

Existing fields remain authoritative for:

```text
embedding_provider
embedding_enabled
embedding models
Ollama endpoint
workspace Qdrant mode/path/url/collection
```

## 4. Production Transition Mapping

P1-04 does not silently move existing production data.

Without an explicit WorkspaceContext:

```text
Vault             -> existing settings.vault_path
lingji_state.db   -> existing settings.state_db_path
lingji_memory.db  -> existing settings.memory_db_path
Qdrant            -> production workspace collection and configured path/url
```

Acceptance and explicitly supplied workspaces continue to use the isolated P0-03 contract.

This allows semantic integration without turning a provider wiring task into an undeclared data migration.

## 5. Degradation Contract

The following errors do not prevent the lexical gateway from starting:

- invalid semantic boolean override
- invalid semantic batch size
- Workspace validation failure
- unsupported embedding provider
- Embedding Provider construction failure
- Qdrant Provider construction failure
- missing optional runtime prerequisites

The gateway then exposes:

```text
retriever.semantic_provider = null
index_coordinator.semantic_provider = null
runtime_warnings[].code = semantic_runtime_initialization_failed
```

Lexical search, Core Memory and Context Pack remain available.

Runtime search-time Qdrant failures continue through the existing HybridRetriever lexical fallback.

## 6. Lexical Capability Contract

The existing lexical-only capability fixture now explicitly sets:

```text
semantic_enabled = false
```

This preserves the Phase 0 contract and prevents a lexical-only test from accidentally depending on Qdrant or Ollama after semantic runtime becomes enabled by default.

## 7. Tests

Added:

```text
tests/test_semantic_runtime_wiring.py
```

Coverage:

1. enabled runtime injects one semantic provider into Retriever and Coordinator
2. explicit semantic disable skips both factories
3. embedding/provider initialization failure returns a lexical gateway
4. invalid boolean override returns a lexical gateway with a warning
5. existing production Vault and SQLite paths are preserved without an explicit workspace
6. semantic query failure still returns lexical results
7. Gateway close releases owned semantic and embedding providers

Existing coordinator tests cover semantic write failure after lexical commit.

## 8. Validation State

The GitHub connector can commit and inspect code but cannot execute a complete repository checkout. The isolated container cannot resolve GitHub.

Therefore:

```text
committed P1-04 pytest: not executed here
full repository pytest: not executed here
real Ollama + embedded Qdrant integration: not executed here
```

Required local validation:

```text
python -m pip install -r requirements.txt
python -m pytest tests/test_semantic_runtime_wiring.py -v
python -m pytest tests/test_memory_index_coordinator.py -v
python -m pytest tests/test_embedding_provider.py tests/test_qdrant_semantic_provider.py -v
python -m pytest tests/test_memory_capability_contract.py tests/test_permanent_memory_gateway.py -v
python -m pytest tests/ -v
```

## 9. Files

```text
src/config.py
src/gateway/bootstrap.py
src/gateway/memory_gateway.py
tests/fixtures/memory_capability.py
tests/test_semantic_runtime_wiring.py
docs/TEST_REPORTS/P1_04_SEMANTIC_RUNTIME_WIRING_TEST_REPORT.md
```

## 10. Intentionally Not Included

- Local Control vector status API
- vector coverage API
- unified MemoryStatisticsService
- Runtime Settings UI fields
- staged collection switching
- Memory Inspector
- Vector Center UI
- legacy data migration or deletion

## 11. Known Limitations

- Search-time semantic exceptions are swallowed by HybridRetriever and are not yet returned as structured query warnings.
- Real provider readiness and vector statistics are not yet aggregated into Local Control API.
- Model or dimension changes mark rebuild-required but do not yet build and switch a replacement collection.
- Full local regression and real Ollama/Qdrant execution remain pending.

## 12. Data Safety

This task does not migrate, delete or rewrite existing Vault, SQLite or Qdrant data.

Qdrant collection creation still occurs only when semantic indexing performs an upsert.

## 13. Rollback

Revert the P1-04 commits. `MemoryGateway` returns to direct lexical synchronization, and `build_memory_gateway()` returns to `semantic_provider=None`.

No data rollback is required for the repository change itself.

## 14. Next Step

```text
P1-05 unified vector status, coverage and Phase 1 validation
```

P1-05 must expose truthful provider state through the authenticated Local Control API on port 8766. It must not begin the full Memory Inspector UI.
