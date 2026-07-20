# P1-01 Embedding Provider Core Migration Test Report

> Date: 2026-07-20  
> Base: `39b754d940658fc6ae3bf7af29be2b1596335b2b`  
> Branch: `work/p1-01-embedding-provider`  
> Status: provider core implemented; workspace/runtime-settings wiring pending P0-03 merge

## Goal

Migrate the useful primary/fallback Ollama embedding behavior from `second_brain/embedding.py` into the long-term `src/model_center/` mainline without copying the legacy retrieval algorithm or touching Qdrant.

## Implemented

- `EmbeddingProvider` protocol
- `EmbeddingTransport` protocol
- `RequestsEmbeddingTransport`
- `EmbeddingStatus`
- `OllamaEmbeddingProvider`
- primary and fallback model ordering
- active model tracking
- unavailable model tracking
- failure reset and primary retry
- embedding dimension tracking
- request/failure counters and timestamps
- batch embedding with bounded batch size
- Ollama `/api/embed` support
- fallback to legacy `/api/embeddings`
- explicit errors when every configured model fails
- safe transport close
- Model Center package exports

## Intentionally Not Included

- Qdrant provider
- semantic retrieval wiring
- `semantic_provider=None` replacement
- Runtime Settings fields
- WorkspaceContext wiring
- Local Control API changes
- Tauri UI
- database or schema changes

Runtime Settings and Workspace wiring must be added after P0-03 lands, to avoid parallel edits to `src/config.py`, `src/runtime/__init__.py`, and shared status documents.

## Files

```text
src/model_center/embedding.py
src/model_center/__init__.py
tests/test_embedding_provider.py
docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md
```

## Test Coverage

1. primary model success
2. dimension and request status
3. primary failure and fallback success
4. unavailable model tracking
5. reset and primary recovery
6. bounded batch execution
7. legacy Ollama endpoint fallback
8. all models unavailable
9. invalid and empty responses
10. transport cleanup

## Test Result

Dependency-light isolated execution of the provider and fake transport suite:

```text
8 tests run
8 passed
0 failed
```

The test uses a fake transport and performs no network calls.

## Not Yet Run

- full repository `pytest`
- real local Ollama request
- primary model missing on a real Ollama installation
- fallback model missing on a real Ollama installation
- GPU/CPU behavior
- integration with Qdrant

These require the repository or local runtime and must not be described as passed.

## Data Safety

This task did not modify:

- Vault data
- SQLite databases
- Qdrant collections
- runtime settings files
- dependencies
- `second_brain` runtime behavior

## Rollback

Remove the new embedding module and test, then restore the previous `src/model_center/__init__.py`. No data rollback is required.

## Next Step

After P0-03 is merged:

1. rebase this branch onto the updated `feature/second-brain-memory`
2. add Runtime Settings and Workspace-aware provider factory wiring
3. run repository tests
4. perform one real Ollama integration test
5. then begin P1-02 QdrantSemanticProvider
