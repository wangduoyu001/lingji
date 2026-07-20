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

## 3. Canonical Data And Indexes

```text
Obsidian Vault + Git
= permanent memory and formal knowledge text

workspace raw path
= original imported material

src/storage/state_db.py
= jobs, processing state, queue and audit events

src/retrieval/memory_db.py
= rebuildable lexical and metadata index

Qdrant provider under src/retrieval
= rebuildable semantic index, not yet connected
```

`second_brain/db.py` remains a compatibility database during migration. It is not the final authority.

## 4. Runtime Contracts

| Capability | Current long-term entry | Status |
|---|---|---|
| Workspace names | `src/runtime/workspace.py::WorkspaceName` | implemented |
| Workspace data object | `src/runtime/workspace.py::WorkspaceContext` | implemented |
| Workspace resolution | `src/runtime/workspace.py::WorkspaceResolver` | implemented |
| Workspace validation error | `src/runtime/workspace.py::WorkspaceValidationError` | implemented |
| Port/process contract | `src/runtime/ports.py` | implemented, local validation pending |
| Runtime exports | `src/runtime/__init__.py` | implemented |

The workspace resolver is side-effect free. It does not create paths, read databases, start services or import Qdrant.

`build_memory_gateway(..., workspace=...)` is the first explicit wiring seam. Existing callers retain the Settings transition mapping until later phases migrate them deliberately.

## 5. Workspace Resource Contract

Each `WorkspaceContext` resolves:

- Vault
- raw archive
- storage root
- `lingji_state.db`
- `lingji_memory.db`
- Qdrant mode
- Qdrant path or URL
- Qdrant collection
- logs
- cache
- runtime settings
- task queue database
- backups
- derived files
- temporary files
- reports

Production and acceptance paths must not be equal, aliases, or parent/child paths. Qdrant collection names must differ even when a remote URL is shared.

## 6. Long-Term Memory Entry Points

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
| MCP tools/resources/prompts | `src/mcp_server.py` |
| MCP CLI startup | `run_mcp_server.py` |

Current semantic gap:

`src/gateway/bootstrap.py` still passes `semantic_provider=None`. Do not describe Qdrant as connected until Phase 1 code and tests pass.

Planned Phase 1 entry points, not yet implemented:

| Planned capability | Planned path |
|---|---|
| Embedding Provider | `src/model_center/embedding.py` |
| Semantic contracts | `src/retrieval/semantic.py` |
| Qdrant Provider | `src/retrieval/qdrant_provider.py` |
| Lexical/vector coordinator | `src/retrieval/index_coordinator.py` |
| Unified memory statistics | `src/gateway/memory_statistics.py` |

## 7. Unified Ingestion Entry Points

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

New data sources must enter this framework. Do not add new production ingestion to `second_brain` connectors.

## 8. Control, Settings, Models And UI Entry Points

| Capability | Entry |
|---|---|
| Control service | `src/control/service.py::LocalControlService` |
| Control API | `src/control/api.py::create_control_app()` |
| Read-only MCP contract API | `GET /api/mcp/status` |
| Runtime settings | `src/control/runtime_settings.py::RuntimeSettingsStore` |
| Control startup | `run_control_api.py` |
| Model inventory | `src/model_center/inventory.py::LocalModelInventoryService` |
| Model capabilities | `src/model_center/registry.py` |
| Backup | `src/storage/backup.py::BackupManager` |
| Tauri app entry | `desktop/lingji-control/src/main.tsx` |
| React composition | `desktop/lingji-control/src/App.tsx` |
| Navigation | `desktop/lingji-control/src/navigation.ts` |
| API client | `desktop/lingji-control/src/api.ts` |
| UI smoke | `desktop/lingji-control/scripts/ui-modular-smoke.mjs` |

Tauri uses only the authenticated Local Control API on `127.0.0.1:8766`.

Current control gaps:

- `LocalControlService` does not construct or receive the unified MemoryGateway.
- `brain_status()` may report false zero counts.
- Runtime Settings lacks editable memory, vector, workspace and MCP groups.
- Tauri lacks final Inspector, Vector, Knowledge, source and AI/MCP pages.

## 9. Compatibility Capabilities To Migrate

| Capability | Current compatibility entry | Target |
|---|---|---|
| Qdrant | `second_brain/vector_store.py::VectorStore` | `src/retrieval` Provider |
| Ollama embedding fallback | `second_brain/embedding.py::OllamaEmbedder` | Model Center Provider |
| Structured sources/conversations/messages | `second_brain/db.py` | rebuildable source read model |
| Memory versions | `second_brain/db.py` | revision read model |
| Relations and conflicts | `second_brain/conflict/`, DB tables | unified read models |
| Acceptance scenarios | `second_brain/acceptance.py` | capability contracts |
| PySide6 flows | `second_brain/desktop/` | Tauri capability migration |

The workspace contract is now implemented in `src`; compatibility runtime path behavior remains migration evidence only.

## 10. Planned Unified Read Models

The following paths remain roadmap targets:

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

## 11. Port Map

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

P0-03 did not modify this contract.

## 12. Testing Map

Existing suites:

- `tests/test_memory_retrieval.py`
- `tests/test_memory_lifecycle.py`
- `tests/test_permanent_memory_gateway.py`
- `tests/test_incremental_index_sync.py`
- `tests/test_ai_context_adapters.py`
- `tests/test_extraction_queue.py`
- `tests/test_extraction_worker.py`
- `tests/test_control_api.py`
- `tests/test_mcp_server.py`

P0-03 suites:

- `tests/test_workspace_contract.py`
- `tests/fixtures/memory_capability.py`
- `tests/test_memory_capability_contract.py`

Reports:

- `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`
- `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`

Current evidence:

- workspace contract: 8 passed in isolated assistant environment
- memory capability contract: repository code present, full-checkout execution pending
- full repository regression: pending

## 13. Before Coding Checklist

1. Confirm branch and remote HEAD.
2. Read the architecture plan, roadmap and current status.
3. Locate the existing class/function and data authority.
4. Resolve the target workspace through `WorkspaceResolver` when adding new runtime resources.
5. Confirm whether the target belongs to `src`, Tauri or compatibility-only code.
6. Confirm API registration and Tauri gateway boundaries.
7. Confirm tests and Markdown report location.
8. Do not create another workspace, retrieval, ranking or settings concept.
9. Do not call a planned path implemented until its code and tests exist.
