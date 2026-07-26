# VECTOR_DATABASE.md — LingJi Unified Vector Strategy

> Updated: 2026-07-20
> Status: Migration and target contract
> Authoritative plan: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Verified Current State

`second_brain/` currently has the only fully connected Qdrant path:

- embedded local mode
- in-memory test mode
- remote URL mode
- automatic collection creation
- cosine distance
- dimension validation
- upsert, delete, scroll and query
- collection status and rebuild
- Ollama embedding with primary/fallback models

`src/` already defines `src.retrieval.hybrid.SemanticProvider`, but `src/gateway/bootstrap.py` currently passes `semantic_provider=None`.

Therefore semantic retrieval is not yet connected to the long-term `src` MemoryGateway.

## 2. Final Decision

Qdrant will be adapted into the `src` retrieval system as a `SemanticProvider`.

Do not preserve the `second_brain` retrieval algorithm as a second long-term search path.

```text
src FTS5 / BM25 / Chinese fallback
+
Qdrant SemanticProvider
+
metadata, privacy, time and Agent Scope filters
+
RRF and existing ranking boosts
=
unified retrieval
```

## 3. Authority Boundary

Qdrant is always rebuildable.

```text
Permanent memory and formal knowledge
= Obsidian Vault + Git

Original imported material
= raw archive

Lexical/metadata index
= lingji_memory.db

Semantic index
= Qdrant
```

Neither Qdrant nor `second_brain.sqlite3` may become an independent permanent-memory authority.

## 4. Target Provider Contract

The Qdrant adapter must provide:

- semantic search compatible with `SemanticProvider.search()`
- stable `memory_id` and `chunk_id`
- payload metadata sufficient for post-filtering
- incremental upsert
- incremental delete
- full rebuild
- collection readiness and vector dimension
- total, memory and knowledge vector counts
- per-memory and per-chunk point existence
- orphan and missing-point detection when practical
- production and acceptance isolation
- embedded, remote and in-memory modes
- graceful lexical fallback when unavailable
- timestamps for latest write, query and rebuild when available

Raw vector values must not be exposed in the normal UI.

## 5. Embedding Provider

The current useful behavior in `second_brain/embedding.py` should be moved behind one provider contract and one Model Center configuration.

Required state:

- configured primary model
- configured fallback model
- active model
- unavailable models
- Ollama endpoint health
- vector dimension
- CPU/GPU execution state only when confirmed by telemetry
- last error

The two current defaults are inconsistent:

```text
src embed model: nomic-embed-text
second_brain primary: bge-m3
second_brain fallback: nomic-embed-text
```

The final choice must be user-configurable through Runtime Settings and visible in the Tauri Model and Vector Centers.

## 6. Collection Design

Use separate collections or physically isolated paths for production and acceptance.

Recommended stable point identity:

```text
memory chunk: memory_id + chunk_id
knowledge chunk: document_id + chunk_index or stable chunk_id
```

Payload should include only metadata needed for retrieval and diagnostics, such as:

- kind
- memory_id or document_id
- chunk_id
- title
- memory type and tier
- status
- project
- privacy
- tags
- Agent Scope
- source path or citation reference
- content hash or revision

The canonical text remains in the Vault/index read model. Large duplicated payload text should be avoided unless required for resilient query behavior and documented explicitly.

## 7. Dimension Changes

Changing embedding models may change vector dimension.

Required behavior:

1. detect configured and existing dimension mismatch
2. mark semantic retrieval degraded
3. keep lexical retrieval operational
4. show a rebuild-required warning
5. require explicit owner action or an approved maintenance workflow
6. rebuild into the correct production or acceptance collection

Do not silently mix vectors from incompatible models.

## 8. UI Visibility

The Tauri Vector Center must show truthful backend-confirmed values:

- mode and endpoint/path
- collection
- readiness
- dimension
- active and fallback model
- total vectors
- vectors by kind
- missing active-memory vectors
- orphan vectors
- last write, query and rebuild
- errors and rebuild requirement
- workspace

Per-memory and per-document views must show whether the expected vector point exists.

## 9. Migration Sequence

1. define the `src` Qdrant SemanticProvider adapter
2. connect one embedding provider through Model Center settings
3. implement incremental synchronization and rebuild
4. add health and vector statistics
5. add production/acceptance isolation
6. run lexical-only and lexical-plus-semantic contract tests
7. connect Memory Inspector and Vector Center
8. dual-read compare against `second_brain`
9. retire the legacy vector runtime only after parity

## 10. Current Compatibility Configuration

The existing `second_brain` variables remain compatibility-only during migration:

- `SECOND_BRAIN_QDRANT_PATH`
- `SECOND_BRAIN_QDRANT_URL`
- `SECOND_BRAIN_QDRANT_COLLECTION`

New long-term configuration must be owned by the unified `src` Runtime Settings and Model Center. Documentation must not claim migration is complete until code and tests confirm it.
