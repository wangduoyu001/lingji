# PROJECT_STATUS.md — LingJi Project Status

> Updated: 2026-07-20
> Branch: `feature/second-brain-memory`
> Architecture authority: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
> Execution roadmap: `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`

## 1. Product Direction

```text
src/
= long-term platform mainline

second_brain/
= compatibility, migration and acceptance runtime

desktop/lingji-control/
= only primary desktop UI
```

LingJi converges into one private second brain and one shared memory system for all approved AI clients.

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

`second_brain.sqlite3` remains compatibility data during migration. It is not the long-term authority.

## 3. P0 Runtime Contracts

### P0-02 Port Contract

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Repository implementation has landed. Real Windows simultaneous binding and Tauri runtime smoke remain separate acceptance items.

Report: `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`

### P0-03 Workspace Contract

Implemented:

- one `WorkspaceContext`
- one `WorkspaceResolver`
- production/acceptance physical path isolation
- separate Qdrant collection contracts
- lexical Memory Capability Contract

Validation evidence:

- workspace contract: `8 passed`
- acceptance workspace isolation: passed in the P1-05 real local validator

Report: `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`

## 4. Phase 1 Unified Semantic Memory

### P1-01 EmbeddingProvider

Implemented in `src/model_center/embedding.py`:

- Ollama modern and compatibility endpoints
- primary/fallback behavior
- batch embedding
- verified active model and dimension
- failure state and Settings/runtime factory

Local validation:

```text
Ollama 0.32.0 reachable
bge-m3 installed
actual dimension = 1024
embedding verified
failure count = 0
```

### P1-02 QdrantSemanticProvider

Implemented in `src/retrieval/qdrant_provider.py`:

- embedded, remote and in-memory modes
- Workspace path and collection isolation
- deterministic point IDs
- upsert/delete/search/count/exists/coverage/status
- dimension mismatch and rebuild-required state
- text/vector exclusion from diagnostic payloads

Local validation:

```text
in-memory Qdrant = passed
temporary embedded disk Qdrant = passed
qdrant-client = 1.18.0
```

### P1-03 MemoryIndexCoordinator

Implemented in `src/retrieval/index_coordinator.py`:

- canonical before/after chunk snapshots
- semantic added/updated/removed delta
- metadata-aware fingerprints
- lexical-first commit
- semantic degradation without lexical rollback

Focused local tests passed.

### P1-04 Runtime Wiring

Formal runtime chain:

```text
EmbeddingProvider
  -> QdrantSemanticProvider
  -> HybridRetriever
  -> MemoryIndexCoordinator
  -> MemoryGateway
```

Implemented and validated:

- Workspace-aware provider construction
- one shared provider for retrieval and indexing
- lexical-only fallback after semantic bootstrap failure
- explicit acceptance isolation
- coordinated rebuild without degradation
- multilingual retrieval

### P1-05 Memory And Vector Status

Implemented:

- one `MemoryStatisticsService`
- atomic `<workspace storage>/memory_status.json` snapshot
- live Gateway writer and read-only Local Control reader
- no second embedded Qdrant open from the control process
- stale snapshot detection
- truthful unknown values instead of fake zero
- Brain Status correction
- MCP written-document callback uses coordinated indexing

Authenticated Local Control API:

```text
GET /api/memory/status
GET /api/vector/status
GET /api/vector/coverage
GET /api/brain/status
```

Real local acceptance passed:

```text
semantic provider active          PASS
bge-m3 verified                   PASS
actual dimension 1024             PASS
coordinated rebuild               PASS
vector coverage 2/2 = 1.0         PASS
multilingual retrieval            PASS
memory status API                 PASS
vector status API                 PASS
vector coverage API               PASS
Brain Status real counters        PASS
acceptance isolation              PASS
```

Reports:

- `docs/TEST_REPORTS/P1_05_MEMORY_VECTOR_STATUS_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_05_LOCAL_ACCEPTANCE_SUMMARY.md`

## 5. Test State

Focused Phase 1 and status suites passed, including:

```text
test_memory_statistics.py
test_status_snapshot_wiring.py
test_embedding_provider.py
test_qdrant_semantic_provider.py
test_memory_index_coordinator.py
test_semantic_runtime_wiring.py
test_workspace_contract.py
test_control_api.py
```

Full repository result:

```text
244 passed
2 failed
9 skipped
146.50 seconds
```

The two failures are known pre-existing environment/baseline checks:

1. `test_brain_status_endpoint`
   - requires a separately running service in the full-suite context
   - the official P1-05 validator verified the endpoint successfully

2. `test_original_startup_files_are_unchanged`
   - compares the feature branch with master-era startup files
   - the feature branch intentionally differs

The nine skipped tests require the real Obsidian CLI.

Accurate conclusion:

```text
Phase 1 runtime acceptance = PASS
Focused Phase 1 tests      = PASS
Full suite completely green = NO
Full suite result           = PASS WITH 2 KNOWN PRE-EXISTING FAILURES AND 9 OPTIONAL SKIPS
```

## 6. Current Accurate State

```text
Embedding migration          = implemented and locally validated
Qdrant migration             = implemented and locally validated
Workspace isolation          = implemented and locally validated
Lexical/vector coordination  = implemented and locally validated
MemoryGateway runtime wiring = implemented and locally validated
8766 status API              = implemented and locally validated
Brain Status real counters   = implemented and locally validated
bge-m3 acceptance            = passed at 1024 dimensions
Production bge-m3 switch     = not performed
Production vector rebuild    = not performed
Tauri Vector Center          = in parallel development branch
Memory Inspector             = not implemented
```

## 7. bge-m3 Position

`bge-m3` is now the validated acceptance model for LingJi Chinese, English and mixed-language retrieval.

The production default is not silently changed. A production switch requires:

```text
new production collection
-> full vector rebuild
-> coverage validation
-> search parity validation
-> controlled collection switch
-> rollback retention
```

Do not mix vectors from models with different dimensions in one collection.

## 8. Remaining Critical Gaps

1. Complete and review `P2-01 Tauri Vector Center`.
2. Implement staged replacement-collection build and validated production switch to bge-m3.
3. Surface search-time semantic degradation in search responses.
4. Expose editable vector/workspace/MCP groups in Runtime Settings.
5. Develop structured source/conversation/message read models.
6. Develop Memory Inspector after shared statistics and Vector Center are stable.
7. Clean up or reclassify the two pre-existing full-suite failures.

## 9. Development Freeze Rules

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only for compatibility, export, parity and migration blockers
- no direct Tauri access to `8765`, `8767` or Qdrant
- no compatibility-data deletion before export, parity and rollback validation

## 10. Next Development Sequence

```text
P2-01 Tauri Vector Center
-> staged bge-m3 production collection migration
-> structured source/conversation/message read model
-> Memory Inspector
```

The Vector Center branch must remain separate until reviewed against this accepted P1-05 backend contract.
