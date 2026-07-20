# P1-02 Qdrant SemanticProvider Test Report

Updated: 2026-07-20
Branch: `work/p1-02-qdrant-semantic-provider`
Base: `84ddaf45b9bf51d1248a6ba53e41e38c72ddd7dd`
Status: repository implementation complete; real in-memory Qdrant execution pending local validation

## 1. Goal

Adapt the useful Qdrant behavior from `second_brain/vector_store.py` into the long-term `src/retrieval/` mainline without copying the legacy SQL or ranking algorithm.

Qdrant supplies semantic candidates, rebuildable index operations and diagnostics. The existing `HybridRetriever` remains the only RRF ranking and canonical permission-filtering path.

## 2. Architecture

```text
WorkspaceContext
  -> production / acceptance Qdrant mode, path or URL, collection

EmbeddingProvider
  -> query and chunk vectors

QdrantSemanticProvider
  -> search candidates
  -> upsert / delete
  -> count / exists / coverage / status

HybridRetriever
  -> canonical SQLite resolution
  -> privacy / Agent Scope / project / tag checks
  -> lexical + semantic RRF
```

The provider does not write permanent memory text and does not access the Vault directly.

## 3. Implemented Contracts

Added `src/retrieval/semantic.py`:

- `SemanticPoint`
- `SemanticIndexProvider`
- `SemanticDiagnosticsProvider`
- combined `SemanticProvider`
- reuse of the existing `hybrid.SemanticProvider` search protocol

Added `src/retrieval/qdrant_provider.py`:

- embedded Qdrant mode
- remote Qdrant mode
- in-memory acceptance mode
- lazy client creation
- optional dependency failure reporting
- workspace-scoped collection
- deterministic UUIDv5 point IDs
- stable point IDs from workspace + collection schema + chunk ID
- chunk upsert and batch upsert
- chunk delete
- delete by memory ID
- semantic search
- collection creation
- collection dimension checking
- `rebuild_required` on dimension mismatch
- total and kind-specific counts
- point existence checks
- expected/missing coverage
- status and diagnostics
- safe close behavior

## 4. Ranking and Permission Boundary

This task does not add a second ranking implementation.

Qdrant returns only IDs, scores and metadata payload. `HybridRetriever` still resolves canonical memory/chunk data from `lingji_memory.db`, applies post-filters and performs existing RRF and metadata boosts.

Server-side Qdrant filters cover:

- status
- privacy
- memory type
- project
- tags

Agent Scope and final authorization remain mandatory in the canonical HybridRetriever path.

## 5. Point Identity

```text
UUIDv5(
  namespace = lingji:qdrant-point,
  value = workspace + collection_schema + chunk_id
)
```

The original `memory_id` and `chunk_id` remain in payload.

Production and acceptance produce different point IDs and use different collections.

## 6. Payload Safety

The provider removes the following payload fields before Qdrant storage:

```text
text
content
body
vector
```

It stores rebuildable metadata such as:

- kind
- memory_id
- chunk_id
- title
- heading
- relative_path
- status
- privacy
- project
- tags
- agent_scope
- line numbers
- content hash when supplied
- active embedding model
- workspace
- collection schema

Qdrant remains a rebuildable index, not a permanent memory authority.

## 7. Dependency

Added to the main requirements:

```text
qdrant-client>=1.12,<2
```

The module still imports safely when the dependency is absent. Enabling or probing Qdrant then returns an explicit unavailable status rather than breaking lexical-only imports.

## 8. Tests

Added:

```text
tests/test_qdrant_semantic_provider.py
```

Dependency-free contract coverage:

1. stable point ID
2. production/acceptance point isolation
3. missing dependency returns `ready=false`
4. missing dependency includes an explicit installation error

Real Qdrant in-memory integration coverage, conditionally executed when `qdrant-client` is installed:

1. upsert
2. search
3. count
4. kind count
5. exists
6. status
7. payload text exclusion
8. privacy filtering
9. chunk delete
10. delete by memory ID
11. coverage and missing chunks
12. dimension mismatch
13. rebuild-required status

The conditional skip is dependency-based, not an unconditional replacement for integration testing.

## 9. Validation State

Current execution environment does not have `qdrant-client` installed.

Therefore:

```text
real in-memory Qdrant tests: not executed here
full repository pytest: not executed here
```

The task must remain `awaiting local validation` until the new dependency is installed and the real in-memory test suite passes.

Required local command:

```text
python -m pip install -r requirements.txt
python -m pytest tests/test_qdrant_semantic_provider.py -v
```

Then run:

```text
python -m pytest tests/test_embedding_provider.py tests/test_workspace_contract.py tests/test_memory_capability_contract.py -v
python -m pytest tests/ -v
```

## 10. Files

```text
requirements.txt
src/retrieval/semantic.py
src/retrieval/qdrant_provider.py
src/retrieval/__init__.py
tests/test_qdrant_semantic_provider.py
docs/TEST_REPORTS/P1_02_QDRANT_SEMANTIC_PROVIDER_TEST_REPORT.md
```

## 11. Intentionally Not Included

- `build_memory_gateway()` wiring
- replacement of `semantic_provider=None`
- MemoryIndexCoordinator
- full rebuild orchestration
- collection switching after validation
- Local Control vector API
- Tauri Vector Center
- Memory Inspector
- legacy data migration or deletion

## 12. Known Limitations

- Real Qdrant API compatibility is pending local execution against the pinned dependency range.
- Remote Qdrant authentication fields are not yet exposed through Runtime Settings.
- The provider does not switch collections automatically after a dimension change.
- Full collection rebuild and atomic collection switching belong to P1-03.
- HybridRetriever currently suppresses semantic exceptions without a structured warning; trace and warning propagation are later tasks.

## 13. Data Safety

This task did not modify:

- Vault data
- raw data
- SQLite data or schema
- existing Qdrant data
- runtime settings files
- Tauri
- Local Control API
- `second_brain` behavior

No collection is created until the provider is explicitly constructed and an upsert is requested.

## 14. Rollback

Revert the P1-02 commits, restore `src/retrieval/__init__.py` and `requirements.txt`, and remove the new provider, contract and test files.

No data rollback is required because this repository task did not connect the provider to runtime startup.

## 15. Next Step

After local in-memory Qdrant validation:

```text
P1-03 MemoryIndexCoordinator
```

It will synchronize the same chunk delta to `lingji_memory.db` and Qdrant, then P1-04 will connect the provider to `build_memory_gateway()` with lexical fallback.
