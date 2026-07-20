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
  -> MemoryIndexCoordinator
       -> lingji_memory.db
       -> QdrantSemanticProvider
  -> HybridRetriever
  -> ContextPackBuilder
  -> MemoryGateway
  -> MCP / Local Control API
  -> Tauri UI
```

The coordinator exists but is not yet wired into `MemoryGateway` startup.

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

src/retrieval/qdrant_provider.py
= rebuildable semantic index provider, not yet connected to gateway startup
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

| Capability | Current long-term entry | Status |
|---|---|---|
| Memory gateway | `src/gateway/memory_gateway.py::MemoryGateway` | implemented |
| Runtime assembly | `src/gateway/bootstrap.py::build_memory_gateway()` | lexical only; semantic wiring pending |
| AI profiles | `src/gateway/profiles.py::AIProfileRegistry` | implemented |
| Lexical/semantic fusion | `src/retrieval/hybrid.py::HybridRetriever` | implemented |
| Search semantic Protocol | `src/retrieval/hybrid.py::SemanticProvider` | implemented |
| Combined semantic contracts | `src/retrieval/semantic.py` | implemented; local validation pending |
| Qdrant provider | `src/retrieval/qdrant_provider.py::QdrantSemanticProvider` | implemented; local validation pending |
| Embedding provider | `src/model_center/embedding.py::OllamaEmbeddingProvider` | implemented; real Ollama validation pending |
| Embedding factory | `src/model_center/embedding.py::build_embedding_provider()` | implemented |
| Enhanced Chinese fallback | `src/retrieval/enhanced.py` | implemented |
| Rebuildable memory index | `src/retrieval/memory_db.py::MemoryDatabase` | implemented |
| Chunking | `src/retrieval/chunker.py::MarkdownChunker` | implemented |
| Context Pack | `src/retrieval/context_pack.py::ContextPackBuilder` | implemented |
| Incremental lexical sync | `src/retrieval/incremental_sync.py::IncrementalMemorySynchronizer` | implemented |
| Lexical/vector coordinator | `src/retrieval/index_coordinator.py::MemoryIndexCoordinator` | implemented; runtime wiring and local validation pending |
| Coordinator warning/result contracts | `src/retrieval/index_coordinator.py` | implemented |
| Unified memory statistics | `src/gateway/memory_statistics.py` | planned |
| Permanent-memory lifecycle | `src/memory/lifecycle.py::MemoryLifecycleService` | implemented |
| State and events | `src/storage/state_db.py::StateDatabase` | implemented |
| MCP tools/resources/prompts | `src/mcp_server.py` | implemented |
| MCP CLI startup | `run_mcp_server.py` | implemented |

Current semantic runtime gap:

```text
src/gateway/bootstrap.py
  -> semantic_provider=None

src/gateway/memory_gateway.py
  -> IncrementalMemorySynchronizer directly
```

Do not describe Qdrant as connected to MemoryGateway until P1-04 wiring and integration tests pass.

## 7. Semantic Provider And Coordinator Boundaries

```text
src/model_center/embedding.py
  -> vectors and verified model status

src/retrieval/qdrant_provider.py
  -> semantic candidates
  -> upsert/delete
  -> count/exists/coverage/status

src/retrieval/index_coordinator.py
  -> lexical commit first
  -> canonical before/after snapshots
  -> semantic delta
  -> structured degraded warnings

src/retrieval/hybrid.py
  -> canonical resolve
  -> privacy and Agent Scope checks
  -> RRF and metadata boosts
```

Qdrant must not become a permanent memory authority or a second ranking pipeline. Semantic failure must not roll back a successful lexical update.

## 8. Unified Ingestion Entry Points

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

## 9. Control, Settings, Models And UI Entry Points

| Capability | Entry |
|---|---|
| Control service | `src/control/service.py::LocalControlService` |
| Control API | `src/control/api.py::create_control_app()` |
| Read-only MCP contract API | `GET /api/mcp/status` |
| Runtime settings | `src/control/runtime_settings.py::RuntimeSettingsStore` |
| Control startup | `run_control_api.py` |
| Model inventory | `src/model_center/inventory.py::LocalModelInventoryService` |
| Embedding provider | `src/model_center/embedding.py` |
| Model capabilities | `src/model_center/registry.py` |
| Backup | `src/storage/backup.py::BackupManager` |
| Tauri app entry | `desktop/lingji-control/src/main.tsx` |
| React composition | `desktop/lingji-control/src/App.tsx` |
| Navigation | `desktop/lingji-control/src/navigation.ts` |
| API client | `desktop/lingji-control/src/api.ts` |
| UI smoke | `desktop/lingji-control/scripts/ui-modular-smoke.mjs` |

Tauri uses only the authenticated Local Control API on `127.0.0.1:8766`.

Current control gaps:

- `LocalControlService` does not construct or receive the unified MemoryGateway
- `brain_status()` may report false zero counts
- Runtime Settings lacks editable memory, vector, workspace and MCP groups
- no vector status or coverage API exists
- Tauri lacks final Inspector, Vector, Knowledge, source and AI/MCP pages

## 10. Compatibility Capabilities To Migrate

| Capability | Current compatibility entry | Mainline status/target |
|---|---|---|
| Qdrant | `second_brain/vector_store.py::VectorStore` | provider adapted under `src`; runtime wiring pending |
| Ollama embedding fallback | `second_brain/embedding.py::OllamaEmbedder` | provider adapted under Model Center |
| Structured sources/conversations/messages | `second_brain/db.py` | rebuildable source read model planned |
| Memory versions | `second_brain/db.py` | revision read model planned |
| Relations and conflicts | `second_brain/conflict/`, DB tables | unified read models planned |
| Acceptance scenarios | `second_brain/acceptance.py` | capability contracts |
| PySide6 flows | `second_brain/desktop/` | Tauri capability migration |

The compatibility runtime remains migration evidence. Do not extend it as a formal product.

## 11. Planned Unified Read Models

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

## 12. Port Map

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Phase 1 provider/coordinator work does not modify this contract.

## 13. Testing Map

Existing memory/runtime suites:

- `tests/test_memory_retrieval.py`
- `tests/test_memory_lifecycle.py`
- `tests/test_permanent_memory_gateway.py`
- `tests/test_incremental_index_sync.py`
- `tests/test_ai_context_adapters.py`
- `tests/test_workspace_contract.py`
- `tests/test_memory_capability_contract.py`

Phase 1 suites:

- `tests/test_embedding_provider.py`
- `tests/test_qdrant_semantic_provider.py`
- `tests/test_memory_index_coordinator.py`

Reports:

- `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`
- `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_02_QDRANT_SEMANTIC_PROVIDER_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_03_MEMORY_INDEX_COORDINATOR_TEST_REPORT.md`

Current evidence:

- workspace contract: 8 passed in isolated environment
- embedding fake-transport suite: 13 passed
- Qdrant 1.12 direct in-memory API smoke: passed
- committed Qdrant provider pytest in a complete checkout: pending
- committed coordinator pytest in a complete checkout: pending
- full repository regression: pending

## 14. Before Coding Checklist

1. Confirm branch and remote HEAD.
2. Read the architecture plan, roadmap and current status.
3. Locate the existing class/function and data authority.
4. Resolve the target workspace through `WorkspaceResolver` when adding runtime resources.
5. Confirm whether the target belongs to `src`, Tauri or compatibility-only code.
6. Preserve `HybridRetriever` as the only final ranking path.
7. Preserve lexical success when semantic providers fail.
8. Confirm tests and Markdown report location.
9. Do not create another workspace, retrieval, ranking or settings concept.
10. Do not call Qdrant connected until gateway wiring and integration tests pass.
