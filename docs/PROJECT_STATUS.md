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

Repository implementation has landed. Real Windows simultaneous binding and Tauri runtime smoke remain pending.

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
- complete-checkout lexical contract and full pytest: pending

Report: `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`

## 4. Phase 1 Unified Semantic Memory

### P1-01 EmbeddingProvider

Implemented in `src/model_center/embedding.py`:

- Ollama modern and compatibility endpoints
- primary/fallback behavior
- batch embedding
- verified active model and dimension
- failure state and Settings/runtime factory

Validation evidence:

- fake-transport suite: `13 passed`
- real Ollama validation: pending

Report: `docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md`

### P1-02 QdrantSemanticProvider

Implemented in `src/retrieval/qdrant_provider.py`:

- embedded, remote and in-memory modes
- Workspace path and collection isolation
- deterministic point IDs
- upsert/delete/search/count/exists/coverage/status
- dimension mismatch and rebuild-required state
- text/vector exclusion from diagnostic payloads

Validation evidence:

- Qdrant 1.12 direct in-memory API smoke: passed
- committed provider pytest: pending complete checkout

Report: `docs/TEST_REPORTS/P1_02_QDRANT_SEMANTIC_PROVIDER_TEST_REPORT.md`

### P1-03 MemoryIndexCoordinator

Implemented in `src/retrieval/index_coordinator.py`:

- canonical before/after chunk snapshots
- semantic added/updated/removed delta
- metadata-aware fingerprints
- lexical-first commit
- semantic degradation without lexical rollback

Report: `docs/TEST_REPORTS/P1_03_MEMORY_INDEX_COORDINATOR_TEST_REPORT.md`

### P1-04 Runtime Wiring

Formal runtime chain:

```text
EmbeddingProvider
  -> QdrantSemanticProvider
  -> HybridRetriever
  -> MemoryIndexCoordinator
  -> MemoryGateway
```

Implemented:

- Workspace-aware provider construction
- one shared provider for retrieval and indexing
- lexical-only fallback after semantic bootstrap failure
- existing production Vault/SQLite transition paths preserved
- explicit acceptance isolation

Report: `docs/TEST_REPORTS/P1_04_SEMANTIC_RUNTIME_WIRING_TEST_REPORT.md`

### P1-05 Memory And Vector Status

Repository implementation has landed in the P1-05 integration branch.

Implemented:

- one `MemoryStatisticsService`
- atomic `<workspace storage>/memory_status.json` snapshot
- live Gateway writer and read-only Local Control reader
- no second embedded Qdrant open from the control process
- stale snapshot detection
- truthful unknown values instead of fake zero
- Brain Status correction
- MCP written-document callback now uses coordinated indexing

Authenticated Local Control API:

```text
GET /api/memory/status
GET /api/vector/status
GET /api/vector/coverage
```

The shared contract is also exposed in Brain Status, Overview, Settings and Provider Status.

Tests added:

```text
tests/test_memory_statistics.py
tests/test_status_snapshot_wiring.py
```

Updated:

```text
tests/test_control_api.py
```

Local validator:

```text
scripts/validate_p1_05_local.py
```

Recommended isolated acceptance:

```text
ollama pull bge-m3
python scripts/validate_p1_05_local.py --model bge-m3 --run-pytest
```

This validator uses a temporary acceptance Workspace and in-memory Qdrant. It does not touch production data.

Report: `docs/TEST_REPORTS/P1_05_MEMORY_VECTOR_STATUS_TEST_REPORT.md`

## 5. Current Accurate State

```text
Embedding migration          = implemented
Qdrant migration             = implemented
Workspace isolation          = implemented
Lexical/vector coordination  = implemented
MemoryGateway runtime wiring = implemented
8766 status API              = implemented
Brain Status real counters   = implemented
Repository tests             = committed
Real local acceptance        = pending
Full pytest                   = pending
Tauri Vector Center          = not implemented
```

No CI result currently proves the complete-checkout test commands passed.

## 6. bge-m3 Position

The isolated P1-05 validator defaults to `bge-m3` because LingJi primarily needs Chinese, English and mixed-language document retrieval.

The production default is not silently changed. A model change can alter vector dimension and therefore requires an explicit collection rebuild decision.

## 7. Remaining Critical Gaps

1. Run real Windows/Ollama/bge-m3 acceptance.
2. Run focused Phase 1 tests and full `tests/`.
3. Implement staged replacement-collection build and validated switch for model/dimension changes.
4. Surface search-time semantic degradation in search responses.
5. Expose editable vector/workspace/MCP groups in Runtime Settings.
6. Add the minimal Tauri status card, then later the full Vector Center and Memory Inspector.

## 8. Development Freeze Rules

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only for compatibility, export, parity and migration blockers
- no direct Tauri access to `8765`, `8767` or Qdrant
- no compatibility-data deletion before export, parity and rollback validation

## 9. Next Development Sequence

First complete local validation:

```text
python -m pip install -r requirements.txt
ollama pull bge-m3
python scripts/validate_p1_05_local.py --model bge-m3 --run-pytest
python -m pytest tests/ -v
```

After acceptance passes:

```text
P2 structured source/conversation/message read model
```

A minimal Tauri status card may consume the new 8766 endpoints before the full Memory Inspector is developed.
