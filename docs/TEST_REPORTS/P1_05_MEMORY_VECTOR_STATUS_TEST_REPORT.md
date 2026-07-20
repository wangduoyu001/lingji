# P1-05 Memory And Vector Status Test Report

Updated: 2026-07-20
Branch: `work/p1-05-memory-vector-status`
Base: `dcc23d282af5a9bd9b99e11e5bdfbcaf3f864aef`
Status: repository implementation complete; real Windows/Ollama/Qdrant acceptance pending

## 1. Goal

Expose truthful memory, Embedding and Qdrant status through the authenticated Local Control API without letting the control process open the same embedded Qdrant path as the MCP process.

Fix Brain Status so unknown or unavailable values remain `null` or an explicit state instead of becoming fake zero counts.

## 2. Implemented API

Authenticated Local Control API on port `8766` now exposes:

```text
GET /api/memory/status
GET /api/vector/status
GET /api/vector/coverage
```

Existing endpoints now include the same shared contract:

```text
GET /api/brain/status
GET /api/overview
GET /api/settings
GET /api/providers
```

Tauri still does not access Qdrant directly.

## 3. Shared Statistics Contract

Added:

```text
src/gateway/memory_statistics.py
```

`MemoryStatisticsService` reports:

```text
schema_version
as_of
source
stale
state
workspace
memory
embedding
vector
coverage
warnings
```

Memory fields include:

```text
state
documents
chunks
core_memories
revision
database_bytes
database_path
fts_tokenizer
last_rebuild_at
integrity
```

Vector fields include:

```text
state
ready
mode
collection
collection_exists
vectors
dimension
rebuild_required
last_error
embedding
```

Coverage fields include:

```text
state
expected
indexed
missing
coverage
missing_chunk_ids
missing_chunk_ids_truncated
```

Missing chunk IDs are capped at 100 in the status payload.

## 4. State Values

The service uses the common runtime states:

```text
healthy
degraded
unavailable
disabled
configuration_required
```

Unknown values are not converted to zero.

Examples:

```text
No status snapshot:
  memory.documents = null
  vector.vectors = null
  state = configuration_required

Semantic explicitly disabled:
  vector.vectors = null
  vector.state = disabled

Embedding or Qdrant bootstrap failure:
  lexical memory remains available
  vector.state = degraded
```

## 5. Multi-Process Safety

Embedded Qdrant is owned by the process that constructs the MemoryGateway.

That process writes an atomic status snapshot:

```text
<workspace storage>/memory_status.json
```

The Local Control API reads this snapshot when it does not own the Gateway. It does not open the embedded Qdrant directory merely to display status.

The snapshot includes counters, health, collection metadata and warnings. It does not contain memory text, chunk text or vectors.

Snapshots older than five minutes are marked stale and degraded.

## 6. Runtime Publishing

`build_memory_gateway()` attaches one live `MemoryStatisticsService` and publishes a snapshot after startup.

`MemoryGateway.rebuild()` publishes again after coordinated lexical/vector synchronization.

The MCP extraction callback now routes written documents through:

```text
MemoryGateway.rebuild()
  -> MemoryIndexCoordinator
  -> SQLite lexical index
  -> Qdrant semantic index
  -> shared status snapshot
```

It no longer writes only to SQLite through a private indexing side path.

## 7. Brain Status Fix

`LocalControlService.brain_status()` now reads the shared status contract.

It reports:

```text
memory_count
memory_chunk_count
memory_bytes
memory_revision
memory_state
vector_count
vector_state
vector_collection
vector_dimension
vector_rebuild_required
embedding_state
embed_model
workspace
status_source
status_stale
status_as_of
warnings
```

When the runtime snapshot is absent, memory and vector counts are `null`, not `0`.

## 8. Tests

Added:

```text
tests/test_memory_statistics.py
tests/test_status_snapshot_wiring.py
```

Updated:

```text
tests/test_control_api.py
```

Coverage includes:

1. live memory/vector counters
2. atomic snapshot persistence
3. snapshot reader behavior
4. stale snapshot degradation
5. absent snapshot does not report fake zero
6. lexical-only disabled semantic state
7. semantic bootstrap failure degradation
8. startup snapshot publishing
9. snapshot refresh after rebuild
10. authenticated memory status API
11. authenticated vector status API
12. authenticated vector coverage API
13. Brain Status uses shared counts
14. Settings runtime contract includes memory/vector state

The previously added Phase 1 suites remain required:

```text
tests/test_embedding_provider.py
tests/test_qdrant_semantic_provider.py
tests/test_memory_index_coordinator.py
tests/test_semantic_runtime_wiring.py
```

## 9. Isolated Local Acceptance Script

Added:

```text
scripts/validate_p1_05_local.py
```

The script:

- checks the Ollama endpoint
- checks whether the selected embedding model is installed
- creates a temporary acceptance workspace
- uses in-memory Qdrant
- writes temporary Chinese and English memories
- performs a coordinated rebuild
- verifies Embedding and vector dimension
- verifies vector coverage
- verifies multilingual retrieval
- verifies the three Local Control API endpoints
- verifies Brain Status does not show fake zero
- optionally runs focused pytest suites
- writes JSON and Markdown reports
- does not read or write the production Vault, production SQLite databases or production Qdrant collection

Recommended command:

```text
ollama pull bge-m3
python scripts/validate_p1_05_local.py --model bge-m3 --run-pytest
```

Reports are written under:

```text
storage/reports/p1-05-local-acceptance/
```

## 10. bge-m3 Decision

The acceptance script defaults to `bge-m3` because LingJi needs Chinese, English and mixed-language retrieval.

The repository production default is not silently changed in this task. Switching an existing collection from another embedding model may change vector dimension and requires an explicit rebuild decision.

The local acceptance report must record the actual returned dimension. For the official BGE-M3 model, the expected dense vector dimension is 1024.

References:

- https://huggingface.co/BAAI/bge-m3
- https://ollama.com/library/bge-m3

## 11. Validation State

Executed before this report:

```text
Embedding fake-transport tests: 13 passed
Qdrant 1.12 direct in-memory API smoke: passed
```

Not executed in the assistant environment:

```text
P1-05 committed pytest
complete repository pytest
real Windows Ollama call
real bge-m3 embedding
production embedded Qdrant
real Local Control API process on 8766
real MCP process on stdio or 8767
Tauri runtime smoke
```

The GitHub connector does not provide the user's local checkout or Windows runtime. These items remain pending until the local acceptance command runs.

## 12. Required Local Commands

```text
python -m pip install -r requirements.txt
ollama pull bge-m3
python scripts/validate_p1_05_local.py --model bge-m3 --run-pytest
python -m pytest tests/ -v
```

Also verify the normal runtime after the isolated acceptance passes:

```text
GET http://127.0.0.1:8766/api/memory/status
GET http://127.0.0.1:8766/api/vector/status
GET http://127.0.0.1:8766/api/vector/coverage
```

All requests require the existing `X-LingJi-Token` header.

## 13. Files

```text
src/gateway/memory_statistics.py
src/gateway/__init__.py
src/gateway/bootstrap.py
src/gateway/memory_gateway.py
src/control/service.py
src/control/api.py
src/mcp_server.py
tests/test_memory_statistics.py
tests/test_status_snapshot_wiring.py
tests/test_control_api.py
scripts/validate_p1_05_local.py
docs/TEST_REPORTS/P1_05_MEMORY_VECTOR_STATUS_TEST_REPORT.md
```

## 14. Known Limitations

- Production model migration to bge-m3 is not automatic.
- Staged replacement-collection build and validated switch remain pending.
- Search-time semantic failure warnings are not yet included in every search response.
- Runtime Settings UI does not yet expose every vector/workspace setting.
- Tauri does not yet have the final Vector Center page.
- Snapshot freshness depends on Gateway startup and rebuild events; a future heartbeat may refresh idle-runtime timestamps.

## 15. Data Safety

This task does not:

- modify permanent Vault content
- migrate production data
- delete old Qdrant collections
- rewrite database schema
- store text or vectors in the status snapshot
- allow Tauri to access Qdrant directly
- expand `second_brain`

## 16. Rollback

Revert the P1-05 commits.

Delete generated local acceptance reports if desired:

```text
storage/reports/p1-05-local-acceptance/
```

The status snapshot is rebuildable runtime data and may be deleted safely:

```text
<workspace storage>/memory_status.json
```

No permanent-memory rollback is required.

## 17. Next Step

After local acceptance passes:

```text
P2 structured source/conversation/message read model
```

A minimal Tauri status card may be added before the full Memory Inspector, but it must consume the 8766 endpoints created here.
