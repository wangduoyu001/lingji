# LingJi Code Map

> Updated: 2026-07-20
> Purpose: identify real long-term entry points before development.
> Architecture: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
> Execution roadmap: `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`

## 1. Repository Roles

```text
src/
= long-term platform mainline

second_brain/
= compatibility, migration and acceptance source

desktop/lingji-control/
= only primary desktop UI

second_brain/desktop/
= PySide6 acceptance and diagnostic UI
```

Do not infer product ownership from directory names. Confirm the real service and data flow before changing code.

## 2. Unified Target Flow

```text
src/extraction
  -> raw snapshot and Vault documents
  -> MemoryIndexCoordinator (planned)
       -> lingji_memory.db
       -> Qdrant SemanticProvider
  -> HybridRetriever
  -> ContextPackBuilder
  -> MemoryGateway
  -> MCP / Local Control API
  -> Tauri UI
```

## 3. Canonical Data and Indexes

```text
Obsidian Vault + Git
= permanent memory and formal knowledge text

storage/raw
= original imported material

src/storage/state_db.py
= jobs, processing state and audit events

src/retrieval/memory_db.py
= rebuildable lexical and metadata index

Qdrant provider under src/retrieval
= rebuildable semantic index, not yet connected
```

`second_brain/db.py` remains a compatibility database during migration. It is not the final authority.

## 4. Long-Term Memory Entry Points

| Capability | Current long-term entry |
|---|---|
| Memory gateway | `src/gateway/memory_gateway.py::MemoryGateway` |
| Runtime assembly | `src/gateway/bootstrap.py::build_memory_gateway()` |
| AI profiles | `src/gateway/profiles.py::AIProfileRegistry` |
| Lexical/semantic fusion | `src/retrieval/hybrid.py::HybridRetriever` |
| Current semantic Protocol | `src/retrieval/hybrid.py::SemanticProvider` |
| Enhanced Chinese fallback | `src/retrieval/enhanced.py` |
| Rebuildable memory index | `src/retrieval/memory_db.py::MemoryDatabase` |
| Chunking | `src/retrieval/chunker.py::MarkdownChunker` |
| Context Pack | `src/retrieval/context_pack.py::ContextPackBuilder` |
| Incremental synchronization | `src/retrieval/incremental_sync.py::IncrementalMemorySynchronizer` |
| Permanent-memory lifecycle | `src/memory/lifecycle.py::MemoryLifecycleService` |
| State and events | `src/storage/state_db.py::StateDatabase` |
| MCP | `src/mcp_server.py` and `run_mcp_server.py` |

Current semantic gap:

`src/gateway/bootstrap.py` passes `semantic_provider=None`. Do not describe Qdrant as connected to the unified gateway until this changes and tests pass.

Planned Phase 1 entry points, not yet implemented:

| Planned capability | Planned path |
|---|---|
| Embedding Provider | `src/model_center/embedding.py` |
| Semantic contracts | `src/retrieval/semantic.py` |
| Qdrant Provider | `src/retrieval/qdrant_provider.py` |
| Lexical/vector coordinator | `src/retrieval/index_coordinator.py` |
| Unified memory statistics | `src/gateway/memory_statistics.py` |

## 5. Unified Ingestion Entry Points

| Capability | Real entry |
|---|---|
| Adapter interface | `src/extraction/base.py::ExtractionAdapter` |
| Adapter registry | `src/extraction/registry.py::AdapterRegistry` |
| Pipeline | `src/extraction/pipeline.py::ExtractionPipeline` |
| Persistent queue | `src/extraction/queue.py::SQLiteExtractionQueue` |
| Worker | `src/extraction/worker.py::ExtractionWorker` |
| Vault/raw sink | `src/extraction/sink.py::VaultExtractionSink` |
| Runtime assembly | `src/extraction/bootstrap.py::build_extraction_pipeline()` |
| ChatGPT import | `src/extraction/adapters/chatgpt.py::ChatGPTExportAdapter` |
| Codex capture | `src/extraction/adapters/codex.py::CodexWorkReportAdapter` |
| Web/social capture | `src/extraction/adapters/web.py::WebCaptureAdapter` |
| Media extraction | `src/extraction/adapters/media.py::MediaExtractionAdapter` |
| Media semantic derivatives | `src/media/semantic.py::MediaSemanticService` |

New data sources must enter this framework. Do not add new production ingestion to `second_brain` connectors.

## 6. Control, Settings, Models and UI Entry Points

| Capability | Entry |
|---|---|
| Control service | `src/control/service.py::LocalControlService` |
| Control API | `src/control/api.py::create_control_app()` |
| Runtime settings | `src/control/runtime_settings.py::RuntimeSettingsStore` |
| Control startup | `run_control_api.py` |
| Model inventory | `src/model_center/inventory.py::LocalModelInventoryService` |
| Model capabilities | `src/model_center/registry.py` |
| Backup | `src/storage/backup.py::BackupManager` |
| Tauri app entry | `desktop/lingji-control/src/main.tsx` |
| React composition | `desktop/lingji-control/src/App.tsx` |
| Navigation | `desktop/lingji-control/src/navigation.ts` |
| API client | `desktop/lingji-control/src/api.ts` |
| Types | `desktop/lingji-control/src/types.ts` |
| Pages | `desktop/lingji-control/src/pages/` |
| UI smoke | `desktop/lingji-control/scripts/ui-modular-smoke.mjs` |

Tauri uses only the authenticated Local Control API on `127.0.0.1:8766`.

Current control gaps:

- `LocalControlService` does not construct or receive the unified MemoryGateway.
- `brain_status()` reads missing `overview["memory_stats"]` and may report false zero counts.
- Runtime Settings lacks memory, vector, workspace and MCP groups.
- Tauri lacks the final Inspector/Vector/Knowledge/AI-MCP pages and global service status bar.

## 7. Compatibility Capabilities To Migrate

| Capability | Current compatibility entry | Target |
|---|---|---|
| Qdrant | `second_brain/vector_store.py::VectorStore` | `src/retrieval` SemanticProvider adapter |
| Ollama embedding fallback | `second_brain/embedding.py::OllamaEmbedder` | unified provider + Model Center |
| Structured sources/conversations/messages | `second_brain/db.py`, `second_brain/connectors/chat.py` | rebuildable source read model |
| Memory versions | `second_brain/db.py` | Git/events/derived revision read model |
| Relations and conflicts | `second_brain/conflict/`, DB tables | `src` relation/conflict read model |
| Production/acceptance isolation | `second_brain/runtime_registry.py` | unified workspace runtime |
| Acceptance scenarios | `second_brain/acceptance.py` | unified capability contract |
| PySide6 flows | `second_brain/desktop/` | migration and regression reference |

Do not continue building duplicate production functionality in these compatibility paths.

## 8. Planned Unified Read Models

The following paths are roadmap targets and must not be described as implemented before code and tests exist:

| Planned capability | Planned path |
|---|---|
| Source/conversation/message index | `src/sources/read_model.py` |
| Permission-aware source queries | `src/sources/service.py` |
| Retrieval trace | `src/retrieval/trace.py` |
| Memory Inspector facade | `src/gateway/memory_inspector.py` |
| Revision model | `src/memory/revisions.py` |
| Relation model | `src/memory/relations.py` |
| Conflict candidates | `src/memory/conflicts.py` |
| Legacy export/parity | `src/migration/` |
| Workspace runtime | `src/runtime/workspace.py` |

## 9. Port Map

Current conflict:

```text
second_brain FastAPI = 8765
src MCP HTTP default = 8765
Local Control API = 8766
```

Target:

```text
8766 = Local Control API
8767 = optional MCP Streamable HTTP
stdio = default local MCP
```

The target is documentation until code and tests implement it.

## 10. Memory Inspector Entry

Final Memory Inspector path:

```text
Tauri page
  -> Local Control API :8766
  -> src MemoryInspectorFacade / MemoryGateway / shared statistics
  -> lingji_memory.db + Qdrant + rebuildable read models
  -> Obsidian/Git authority
```

It must not treat `second_brain.sqlite3` as the final memory source.

## 11. Testing Map

Relevant existing suites include:

- `tests/test_memory_retrieval.py`
- `tests/test_memory_lifecycle.py`
- `tests/test_permanent_memory_gateway.py`
- `tests/test_incremental_index_sync.py`
- `tests/test_ai_context_adapters.py`
- `tests/test_extraction_queue.py`
- `tests/test_extraction_worker.py`
- `tests/test_control_api.py`
- `tests/test_control_api_extended.py`
- `tests/test_brain_status_e2e.py`
- `tests/test_second_brain.py`
- `tests/test_desktop.py`
- `desktop/lingji-control/scripts/ui-modular-smoke.mjs`

Roadmap-required new suites include provider, capability contract, source read model, statistics, Inspector API, workspace isolation, dual-read and no-legacy regression tests.

## 12. Before Coding Checklist

1. Confirm branch and remote HEAD.
2. Read the unified architecture plan, execution roadmap and current status.
3. Locate existing class/function and data authority.
4. Confirm whether the target is long-term `src` or compatibility `second_brain`.
5. Confirm API registration and UI gateway.
6. Confirm storage and workspace isolation.
7. Confirm tests and Markdown report location.
8. Split work into Provider, synchronization, API, Tauri UI, tests and docs when multiple layers are involved.
9. Do not create a new module based only on a feature name.
10. Do not call a planned path implemented until its code and tests exist.
