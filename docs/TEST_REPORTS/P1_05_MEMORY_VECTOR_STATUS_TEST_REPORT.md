# P1-05 Memory And Vector Status Test Report

Updated: 2026-07-20
Branch: `feature/second-brain-memory`
Validated commit: `9ab3c55074b0e56dac9ac8adccba934627bedd90`
Status: `PASS WITH KNOWN PRE-EXISTING FULL-SUITE FAILURES`

## 1. Goal

Expose truthful memory, Embedding and Qdrant status through the authenticated Local Control API without letting the control process open the same embedded Qdrant path as the MCP process.

Fix Brain Status so unknown or unavailable values remain `null` or an explicit state instead of becoming fake zero counts.

## 2. Implemented API

Authenticated Local Control API on port `8766` exposes:

```text
GET /api/memory/status
GET /api/vector/status
GET /api/vector/coverage
GET /api/brain/status
```

The same shared contract is also available from Overview, Settings and Provider Status.

Tauri does not access Qdrant directly.

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

Embedding fields include:

```text
provider_id
configured_model
fallback_model
active_model
dimension
verified
available
request_count
failure_count
last_success_at
last_failure_at
last_error
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

The MCP extraction callback routes written documents through:

```text
MemoryGateway.rebuild()
  -> MemoryIndexCoordinator
  -> SQLite lexical index
  -> Qdrant semantic index
  -> shared status snapshot
```

It no longer writes only to SQLite through a private indexing side path.

## 7. Brain Status Fix

`LocalControlService.brain_status()` reads the shared status contract and reports:

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

## 8. Automated Tests

Added:

```text
tests/test_memory_statistics.py
tests/test_status_snapshot_wiring.py
```

Updated:

```text
tests/test_control_api.py
```

Focused coverage includes:

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

The following focused suites passed locally:

```text
tests/test_memory_statistics.py
tests/test_status_snapshot_wiring.py
tests/test_embedding_provider.py
tests/test_qdrant_semantic_provider.py
tests/test_memory_index_coordinator.py
tests/test_semantic_runtime_wiring.py
tests/test_workspace_contract.py
tests/test_control_api.py
```

## 9. Real Local Acceptance

Local environment:

```text
Path: D:\codex\lingji-second-brain
Python: 3.13.2
qdrant-client: 1.18.0
Ollama: 0.32.0
Model: bge-m3:latest, F16, 566.70M
Actual vector dimension: 1024
```

Official isolated P1-05 validator result:

```text
semantic_provider_active             PASS
embedding_verified                   PASS
vector_dimension_detected            PASS
coordinated_rebuild_not_degraded     PASS
vector_coverage_complete             PASS
multilingual_search_returns_results  PASS
control_memory_status_200            PASS
control_vector_status_200            PASS
control_vector_coverage_200           PASS
brain_status_not_fake_zero           PASS
acceptance_workspace_isolated        PASS
```

Observed runtime values:

```text
documents = 2
chunks = 2
vectors = 2
coverage = 1.0
embedding model = bge-m3
embedding dimension = 1024
semantic state = healthy
workspace = acceptance
```

Both in-memory Qdrant and temporary embedded disk Qdrant passed.

The validation used isolated temporary paths and did not touch production data.

Detailed summary:

```text
docs/TEST_REPORTS/P1_05_LOCAL_ACCEPTANCE_SUMMARY.md
```

## 10. Full Repository Test Result

```text
244 passed
2 failed
9 skipped
146.50 seconds
```

Known pre-existing failures:

1. `test_brain_status_endpoint`
   - requires a separately running service in the full-suite context
   - the official P1-05 validator independently verified the endpoint successfully

2. `test_original_startup_files_are_unchanged`
   - compares the feature branch with master-era startup files
   - the feature branch intentionally differs from master

The nine skipped tests require the real Obsidian CLI.

Accurate classification:

```text
Phase 1 runtime acceptance = PASS
Focused Phase 1 tests      = PASS
Full suite completely green = NO
Full suite result           = PASS WITH 2 KNOWN PRE-EXISTING FAILURES AND 9 OPTIONAL SKIPS
```

## 11. bge-m3 Decision

`bge-m3` is validated for Chinese, English and mixed-language LingJi retrieval.

The detected dense vector dimension is 1024.

The repository production default is not silently changed. Switching an existing production collection requires:

```text
new collection
-> full rebuild
-> coverage validation
-> search parity validation
-> controlled switch
-> rollback retention
```

Do not mix vectors from embedding models with different dimensions in one collection.

## 12. Local Evidence

Generated local files:

```text
storage/reports/p1-05-local-acceptance/P1_05_LOCAL_ACCEPTANCE_20260720-212719.md
storage/reports/p1-05-local-acceptance/P1_05_LOCAL_ACCEPTANCE_20260720-212719.json
p1-05-full-pytest.log
p1-05-official-validation.log
```

The two log files remained untracked. No source code or configuration was modified during local validation.

## 13. Files Implemented By P1-05

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

- production model migration to bge-m3 is not automatic
- staged replacement-collection build and validated switch remain pending
- search-time semantic failure warnings are not yet included in every search response
- Runtime Settings UI does not yet expose every vector/workspace setting
- Tauri Vector Center is being developed separately
- snapshot freshness depends on Gateway startup and rebuild events; a future heartbeat may refresh idle-runtime timestamps
- two pre-existing full-suite failures still need cleanup or reclassification

## 15. Data Safety

This task and its local acceptance did not:

- modify permanent Vault content
- migrate production data
- delete old Qdrant collections
- rewrite database schema
- store text or vectors in the status snapshot
- allow Tauri to access Qdrant directly
- expand `second_brain`

## 16. Phase Decision

Phase 1 is accepted for continued development.

This does not authorize an automatic production bge-m3 switch or production vector rebuild.

## 17. Next Step

```text
P2-01 Tauri Vector Center
-> staged production bge-m3 collection migration
-> structured source/conversation/message read models
-> Memory Inspector
```
