# P2-09A Runtime Truth and Configuration Alignment

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Make the local control status contract distinguish measured facts from unknown or unavailable values. The change covers GPU telemetry, embedding defaults, Qdrant rebuild diagnostics already exposed by the semantic provider, Brain Status aggregation, and startup component logging.

## Root causes

- `LocalControlService.brain_status()` copied the hardware snapshot, set every GPU utilization to `0`, and then launched a second `nvidia-smi` command. A failed command therefore looked like a measured idle GPU.
- `Settings.embed_model` and `Settings.fallback_embed_model` both defaulted to `nomic-embed-text`, so the fallback path was not a real fallback.
- Model inventory fallbacks used presentation strings such as `N/A` and installed model counts defaulted to `0`, conflating unknown state with measured state.
- `run_service.py` reported a generic successful startup without stating that it does not start the loopback control API on port 8766.

## Runtime status chain

The control layer now reuses the existing providers:

1. `HardwareCapabilityService.capabilities()` for static hardware facts.
2. `HardwareCapabilityService.telemetry()` for dynamic GPU/CPU/memory telemetry.
3. `MemoryStatisticsService.snapshot()` for memory, embedding and vector status.
4. `LocalModelInventoryService.inventory()` for configured model assignments.
5. `SQLiteExtractionQueue.list()` for recent processing state.

The control layer no longer invokes `nvidia-smi` itself.

## GPU truth contract

A GPU utilization value of `0` is retained only when it was returned by the telemetry provider. If a static GPU is known but dynamic telemetry is unavailable, dynamic fields are `null`, the GPU status is `unavailable`, the snapshot is stale, and diagnostic errors are included.

Static facts and dynamic facts are kept distinct:

- Static: GPU id, name, total VRAM and driver/CUDA capability.
- Dynamic: utilization, temperature, used/free VRAM, collection time and stale/error state.

## Embedding configuration

The default primary model is now `bge-m3` and the fallback is `nomic-embed-text`. `OllamaEmbeddingProvider` already keeps `active_model` as `null` until a successful embedding call and records the actually successful model after a request.

No model is downloaded automatically.

## Qdrant dimension protection

`QdrantSemanticProvider` already checks collection dimension before upsert and search. A mismatch sets `rebuild_required`, records the collection and embedding dimensions in the error, and raises `VectorDimensionMismatchError` instead of writing incompatible vectors. This task preserves that guard and exposes its status through the existing `MemoryStatisticsService` and Brain Status chain.

The code does not delete or rebuild a production collection automatically. Lexical retrieval remains independent from Qdrant availability.

## Brain Status fields

Unknown model counts, model names, CUDA versions and dynamic GPU readings are represented as `null` rather than `0` or `N/A`. Recent extraction jobs determine whether processing is `active` or `idle`. Provider failures are surfaced as structured warnings.

## Startup behavior

`run_service.py` now logs the state of:

- Core service
- Extraction worker
- Control API 8766

The service explicitly states that `run_service.py` does not start the control API and prints `python run_control_api.py` as the required separate command.

## Changed files

- `src/config.py`
- `src/control/service.py`
- `run_service.py`
- `tests/test_runtime_truth.py`
- `docs/MODULES/P2_09A_RUNTIME_TRUTH.md`
- `docs/TEST_REPORTS/P2_09A_RUNTIME_TRUTH_TEST_REPORT.md`

## Compatibility

Existing endpoint names are unchanged. Brain Status values become more truthful: callers that assumed unknown numeric values were always zero must now handle `null`.

## Known limits

- Real NVIDIA hardware, Ollama models and Qdrant collections require Windows-machine validation.
- GitHub CI can validate code paths with fakes but cannot prove the local driver's telemetry quality.

## Rollback

Revert the commits on `work/p2-09a-runtime-truth`. No database schema, vector collection or user data migration is involved.
