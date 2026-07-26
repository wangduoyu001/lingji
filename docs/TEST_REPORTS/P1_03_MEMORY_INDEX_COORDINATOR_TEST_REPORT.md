# P1-03 MemoryIndexCoordinator Test Report

Updated: 2026-07-20
Branch: `work/p1-03-memory-index-coordinator`
Base: `1a9ea2eff8c467f43defb93fb082053d68e035e9`
Status: repository implementation complete; complete-checkout pytest pending

## 1. Goal

Coordinate the rebuildable lexical index and optional semantic index from the same canonical chunk state without making `MemoryDatabase` depend on Qdrant.

The lexical index must remain usable when embedding or Qdrant fails.

## 2. Architecture

```text
Vault index entries
  -> MemoryIndexCoordinator
       -> MemoryDatabase / IncrementalMemorySynchronizer
       -> snapshot canonical documents + chunks
       -> derive semantic added / updated / removed delta
       -> SemanticIndexProvider
       -> structured result + warning event
```

The coordinator reads the post-commit canonical rows from `lingji_memory.db` and converts them to `SemanticPoint`. It does not read permanent memory from Qdrant.

## 3. Implemented

Added:

```text
src/retrieval/index_coordinator.py
```

Core types:

- `MemoryIndexCoordinator`
- `SemanticSyncResult`
- `SemanticSyncWarning`

Capabilities:

- incremental lexical synchronization through the existing synchronizer
- full lexical rebuild through the existing database implementation
- canonical chunk snapshots before and after lexical synchronization
- deterministic semantic delta calculation
- added chunk upsert
- changed content upsert
- changed metadata payload upsert
- removed chunk delete
- bounded semantic batches
- lexical-only mode when no semantic provider is configured
- structured semantic degradation
- optional state event recording
- full rebuild re-upserts all current canonical chunks

## 4. Data Flow

```text
before lexical snapshot
  -> lexical sync or rebuild
  -> after lexical snapshot
  -> compare chunk IDs and fingerprints
       added
       updated
       removed
  -> delete removed semantic points
  -> upsert added/updated semantic points
```

For a forced rebuild, all current chunks are upserted again. Known chunks removed from the lexical index are deleted from the semantic index.

Unknown pre-existing Qdrant orphans are not deleted in this task. Atomic new-collection rebuild and orphan reconciliation remain later Phase 1 work.

## 5. Semantic Fingerprint

The semantic fingerprint includes:

- chunk text
- chunk content hash
- document content hash
- title and heading
- relative path
- memory type and tier
- status and review status
- privacy
- project and tags
- Agent Scope
- validity dates
- line numbers
- relevant retrieval metadata

This allows a stable chunk ID to be re-upserted when metadata changes even if the body text remains unchanged.

## 6. Degradation Contract

Lexical work is committed before semantic work begins.

If semantic delete or upsert fails:

```text
lexical index = updated and usable
semantic status = degraded
warning code = semantic_delete_failed or semantic_upsert_failed
```

The coordinator does not roll back the lexical index and does not convert a semantic failure into a total indexing failure.

## 7. Result Contract

The result preserves existing lexical counters and adds:

```text
semantic.status
semantic.degraded
semantic.upserted
semantic.deleted
semantic.failed
semantic.added
semantic.updated
semantic.removed
semantic.warnings

degraded
warnings
```

Semantic status values in this task:

```text
healthy
degraded
disabled
```

## 8. Tests

Added:

```text
tests/test_memory_index_coordinator.py
```

Coverage:

1. initial sync upserts all canonical chunks
2. unchanged sync performs no semantic write
3. body update deletes old chunk IDs and upserts new IDs
4. metadata-only update re-upserts a stable chunk ID
5. document removal deletes semantic chunks
6. semantic failure leaves the lexical index committed
7. semantic failure records a degraded event
8. no semantic provider preserves lexical-only operation
9. force rebuild re-upserts all current chunks

The tests use the real `MemoryDatabase`, real `MarkdownChunker` and existing incremental synchronizer with a fake semantic provider. They do not create a second test-only lexical implementation.

## 9. Validation State

The repository connector does not provide a complete executable checkout and the isolated container cannot resolve GitHub.

Therefore:

```text
committed coordinator pytest: not executed here
full repository pytest: not executed here
```

Required local commands:

```text
python -m pytest tests/test_memory_index_coordinator.py -v
python -m pytest tests/test_incremental_index_sync.py tests/test_memory_retrieval.py -v
python -m pytest tests/test_embedding_provider.py tests/test_qdrant_semantic_provider.py -v
python -m pytest tests/ -v
```

The implementation remains `awaiting local validation` until these commands run in the complete repository.

## 10. Files

```text
src/retrieval/index_coordinator.py
src/retrieval/__init__.py
tests/test_memory_index_coordinator.py
docs/TEST_REPORTS/P1_03_MEMORY_INDEX_COORDINATOR_TEST_REPORT.md
```

## 11. Intentionally Not Included

- `MemoryGateway` runtime wiring
- replacing `semantic_provider=None`
- automatic Qdrant collection switching
- remote Qdrant authentication settings
- vector status API
- Memory Inspector
- Vector Center UI
- legacy data migration or deletion

## 12. Known Limitations

- Unknown semantic orphan points cannot be identified from the lexical before-snapshot.
- Full staged collection rebuild and validated switching are still required for model/dimension changes.
- Semantic warning propagation into search responses is not implemented here.
- Runtime settings and Local Control status remain later tasks.

## 13. Data Safety

This task does not modify:

- permanent Vault content
- raw input
- database schema
- runtime startup
- real Qdrant collections
- Tauri
- `second_brain`

No semantic provider is constructed automatically by this task.

## 14. Rollback

Revert the P1-03 commits, restore `src/retrieval/__init__.py`, and remove the coordinator and test files.

No database or Qdrant rollback is required because runtime wiring is not part of this task.

## 15. Next Step

```text
P1-04 build_memory_gateway runtime wiring
```

P1-04 must construct the Workspace-aware EmbeddingProvider and QdrantSemanticProvider, inject them into `HybridRetriever` and `MemoryIndexCoordinator`, and preserve lexical-only startup when semantic configuration or dependencies are unavailable.
