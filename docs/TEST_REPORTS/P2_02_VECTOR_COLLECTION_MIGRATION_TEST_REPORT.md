# P2-02 Vector Collection Migration Test Report

Updated: 2026-07-20
Branch: `work/p2-02-vector-collection-migration`
Base: `a076b4f42b530077e7cff7dd3745cf2250293bae`
Status: repository implementation complete; complete-checkout local validation pending

## 1. Goal

Prepare a new Embedding/Qdrant collection without changing the active production model or collection.

The migration flow must prove that the candidate contains exactly the canonical chunks from `lingji_memory.db`, uses the requested model, has a valid dimension, and reaches complete coverage before it produces activation and rollback settings.

## 2. Safety Boundary

This task implements:

```text
plan
  -> build target collection
  -> validate exact vector count
  -> validate 100% coverage
  -> validate active model and dimension
  -> write atomic manifest
  -> produce activation and rollback settings
```

It does not:

```text
change active runtime settings
delete the source collection
delete a failed target collection
restart MCP or Local Control
modify Vault or SQLite content
switch the production model
```

## 3. Canonical Data Source

`MemoryIndexCoordinator.semantic_points()` is the only source of candidate points.

```text
Obsidian Vault + Git
  -> lingji_memory.db
  -> canonical SemanticPoint list
  -> target Qdrant collection
```

The migration service does not read memory text from the source Qdrant collection and does not treat Qdrant as permanent memory authority.

## 4. Implemented Contracts

Added:

```text
src/retrieval/collection_migration.py
```

Core objects:

- `VectorCollectionMigrationService`
- `VectorCollectionMigrationPlan`
- `VectorCollectionMigrationResult`
- `VectorCollectionMigrationError`

The service validates:

1. source and target collection names differ
2. collection names use a bounded safe character set
3. target model is non-empty
4. canonical index contains at least one chunk
5. every canonical point is submitted
6. Provider returns one ID for each submitted point
7. coverage is exactly `1.0`
8. missing count is exactly `0`
9. target Collection exists and is ready
10. target Provider does not report `rebuild_required`
11. target vector count exactly equals canonical Chunk count
12. target vector dimension is positive
13. Embedding Provider is verified and available
14. actual active model matches the requested target model
15. Provider status refers to the target collection

A failed validation writes a failed manifest without activation settings.

## 5. Switch Contract

A validated bge-m3 candidate produces an explicit activation patch:

```json
{
  "embed_model": "bge-m3",
  "fallback_embed_model": "bge-m3",
  "production_qdrant_collection": "<target collection>"
}
```

The target model is also used as the initial fallback to avoid mixing different vector dimensions in one collection.

The manifest contains rollback settings for the previous model, fallback model and collection.

The service does not apply either patch.

## 6. CLI

Added:

```text
scripts/prepare_vector_collection_migration.py
```

Plan-only usage:

```powershell
python scripts/prepare_vector_collection_migration.py `
  --model bge-m3 `
  --collection lingji_memory_production_bge_m3_1024_v1
```

Plan-only mode does not create a collection.

Execution for embedded Qdrant requires both:

```text
--execute
--confirm-exclusive-qdrant
```

Example:

```powershell
python scripts/prepare_vector_collection_migration.py `
  --model bge-m3 `
  --collection lingji_memory_production_bge_m3_1024_v1 `
  --execute `
  --confirm-exclusive-qdrant
```

Before embedded execution, all other LingJi processes that own the embedded Qdrant directory must be stopped. The flag records explicit operator confirmation; file locking remains the final runtime guard.

## 7. Manifest

Default location:

```text
<workspace reports>/vector-migrations/
```

The JSON manifest includes:

- source and target collection
- source and target model
- expected and upserted counts
- vector and Embedding status
- coverage
- activation settings
- rollback settings
- validation status

It does not contain Chunk text, memory body text or vectors.

Writes use a temporary file followed by atomic replacement.

## 8. Tests

Added:

```text
tests/test_vector_collection_migration.py
```

Coverage:

1. active collection cannot be reused as target
2. empty canonical index is rejected
3. complete candidate writes a validated manifest
4. activation settings target bge-m3 and the new collection
5. rollback settings preserve the old model and collection
6. manifest does not contain memory body text
7. partial coverage is rejected
8. failed candidate has no activation settings
9. extra vectors are rejected
10. wrong active model is rejected
11. short Provider upsert result is rejected
12. Ollama `:latest` model tags compare correctly
13. success and failure events are recorded

The tests use the real `MemoryDatabase` and real canonical SemanticPoint generation. Qdrant and Ollama are represented by a focused fake target Provider so failure states remain deterministic.

## 9. Required Local Validation

```powershell
python -m pytest tests/test_vector_collection_migration.py -v --tb=short
python -m pytest tests/test_memory_index_coordinator.py tests/test_qdrant_semantic_provider.py -v --tb=short
python -m py_compile `
  src/retrieval/collection_migration.py `
  src/retrieval/index_coordinator.py `
  scripts/prepare_vector_collection_migration.py
```

Plan-only production inspection:

```powershell
python scripts/prepare_vector_collection_migration.py `
  --model bge-m3 `
  --collection lingji_memory_production_bge_m3_1024_v1
```

Do not execute the production candidate build until the plan output has been reviewed and embedded Qdrant has exclusive ownership.

## 10. Validation State

The GitHub connector can inspect and commit repository files but cannot run the user's Windows checkout.

Therefore:

```text
committed migration tests: not executed here
production plan-only command: not executed here
real bge-m3 candidate build: not executed here
production model/collection switch: intentionally not executed
```

## 11. Files

```text
src/retrieval/collection_migration.py
src/retrieval/index_coordinator.py
src/retrieval/__init__.py
scripts/prepare_vector_collection_migration.py
tests/test_vector_collection_migration.py
docs/TEST_REPORTS/P2_02_VECTOR_COLLECTION_MIGRATION_TEST_REPORT.md
```

## 12. Known Limitations

- Runtime Settings does not yet own the vector model and collection switch as one atomic operation.
- The CLI requires operator confirmation but cannot identify every external process that may own embedded Qdrant.
- A failed candidate is preserved for diagnosis and is not automatically deleted.
- Retrieval-quality A/B comparison between the old and candidate collections remains a later validation step.
- Remote Qdrant aliases are not introduced in this task.
- The Tauri Vector Center is developed separately and is not modified here.

## 13. Rollback

Repository rollback:

```text
revert P2-02 commits
```

Runtime rollback after a future activation uses the manifest's `rollback_settings`.

The source collection is never deleted by this task, so rollback remains possible.

## 14. Next Priority

After the local P2-02 tests pass:

```text
1. review the production plan-only output
2. build the bge-m3 target collection with exclusive embedded Qdrant access
3. verify exact vector count and 100% coverage
4. run retrieval-quality comparison
5. implement one controlled activation transaction
6. restart and verify Gateway, MCP and 8766 status
7. retain the previous collection for rollback
```

Non-critical cleanup, failed-candidate deletion and collection history UI remain documented backlog items rather than blockers.
