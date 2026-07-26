# P1-01 Unified Embedding Provider Test Report

Updated: 2026-07-20
Branch: `work/p1-01-embedding-provider-v2`
Base: `528fa3b6388baaba0b87d72c02db27d0816c2908`
Status: repository implementation complete; real Ollama and full repository validation pending

## 1. Goal

Migrate the useful Ollama primary/fallback embedding behavior from `second_brain/embedding.py` into the long-term `src/model_center/` mainline.

This task does not connect Qdrant and does not replace `semantic_provider=None`.

## 2. Architecture Decision

```text
Settings / runtime override values
  -> build_embedding_provider()
  -> EmbeddingProvider protocol
  -> OllamaEmbeddingProvider
  -> Ollama /api/embed
       fallback for older Ollama: /api/embeddings
  -> vector list + verified provider status
```

The provider does not know about Qdrant, the Vault, SQLite, retrieval ranking or the desktop UI.

## 3. Implemented

- `EmbeddingProvider` protocol
- `EmbeddingTransport` protocol
- `RequestsEmbeddingTransport`
- `EmbeddingStatus`
- `OllamaEmbeddingProvider`
- `build_embedding_provider()` factory
- primary embedding model
- fallback embedding model
- active model tracking after a successful call
- unavailable model tracking
- failure reset and primary retry
- batch embedding with bounded batch size
- embedding dimension tracking
- request and failure counters
- latest success and failure timestamps
- modern Ollama `/api/embed` support
- compatibility fallback to `/api/embeddings`
- explicit configuration validation
- explicit error when all models fail
- transport cleanup
- Model Center package exports

## 4. Truthful Readiness State

Provider construction does not prove that Ollama or a model is available.

Initial status is therefore:

```text
active_model = null
verified = false
available = false
```

Only a successful embedding call sets the real active model and marks the provider available.

This prevents Local Control or the future Vector Center from displaying a configured model as actively running before backend verification.

## 5. Configuration

Added to `src/config.py`:

```text
embedding_provider = ollama
embedding_enabled = true
embedding_timeout_seconds = 60
embedding_batch_size = 32
```

Existing fields remain the model and endpoint source:

```text
ollama_base_url
embed_model
fallback_embed_model
```

The factory also accepts explicit runtime override values:

```text
embedding_enabled
embedding_provider
embedding_endpoint
embedding_primary_model
embedding_fallback_model
embedding_timeout_seconds
embedding_batch_size
```

Formal Runtime Settings API/UI exposure remains a later runtime-wiring task. The factory contract is ready without adding a second configuration system.

## 6. Files

```text
src/config.py
src/model_center/embedding.py
src/model_center/__init__.py
tests/test_embedding_provider.py
docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md
```

## 7. Test Coverage

1. initial status is configured but not verified
2. primary model success
3. dimension recording
4. primary failure and fallback success
5. unavailable-model tracking
6. failure reset and primary recovery
7. bounded batch execution
8. old Ollama endpoint compatibility
9. all models unavailable
10. empty input and empty response
11. invalid endpoint, model, timeout and batch configuration
12. transport cleanup
13. factory settings and runtime overrides
14. provider disable behavior
15. unsupported provider rejection

## 8. Test Result

A dependency-light isolated test run was executed with a fake transport and no network calls:

```text
13 tests run
13 passed
0 failed
```

The startup environment printed an unrelated `artifact_tool` spreadsheet warmup warning. The embedding test process returned exit code `0`, and all 13 embedding tests passed.

## 9. Not Yet Run

- `python -m pytest tests/test_embedding_provider.py -v` in a full repository checkout
- full repository `python -m pytest tests/ -v`
- real local Ollama `/api/embed` request
- real missing-primary to installed-fallback model switch
- CPU/GPU runtime observation
- Qdrant integration
- semantic retrieval integration

These items require the local runtime and are not described as passed.

## 10. Data and Compatibility Safety

This task did not modify:

- Vault content
- raw archives
- SQLite schema or data
- Qdrant collections
- runtime settings files
- dependencies
- `second_brain` behavior
- Tauri
- Local Control API

The legacy embedder remains unchanged as migration evidence until the compatibility runtime retirement gate.

## 11. Known Limitations

- `src/gateway/bootstrap.py` still uses `semantic_provider=None`.
- No Qdrant client or collection is created.
- Provider status is not yet exposed through Local Control API.
- Runtime Settings definitions and UI controls are not yet added.
- A fallback model with a different dimension will be detected by the Qdrant provider and collection contract in P1-02, not by this provider alone.

## 12. Rollback

Revert the P1-01 commits or remove the new provider module and tests, restore `src/model_center/__init__.py`, and remove the four embedding configuration fields.

No data rollback is required.

## 13. Next Step

```text
P1-02 QdrantSemanticProvider
```

It must consume this `EmbeddingProvider`, use the P0-03 WorkspaceContext for collection isolation, and provide semantic candidates without replacing the existing HybridRetriever RRF pipeline.
