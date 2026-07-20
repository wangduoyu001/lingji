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
= compatibility acceptance and diagnostic UI
```

Do not infer product ownership from directory names. Confirm the real service and data flow before changing code.

## 2. Unified Runtime Flow

```text
src/extraction
  -> raw snapshot and Vault documents
  -> MemoryIndexCoordinator
       -> lingji_memory.db
       -> QdrantSemanticProvider
  -> HybridRetriever
  -> ContextPackBuilder
  -> MemoryGateway
       -> MemoryStatisticsService
       -> memory_status.json
  -> MCP / Local Control API
  -> Tauri UI
```

The Provider, Coordinator and Gateway chain is wired by `build_memory_gateway()`. P1-05 adds a shared status snapshot so the Local Control process does not reopen the same embedded Qdrant directory.

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
= rebuildable semantic index provider

<workspace storage>/memory_status.json
= rebuildable runtime status snapshot, never memory authority
```

`second_brain/db.py` remains compatibility data during migration. It is not the final authority.

## 4. Runtime Contracts

| Capability | Current long-term entry | Status |
|---|---|---|
| Workspace names | `src/runtime/workspace.py::WorkspaceName` | implemented |
| Workspace data object | `src/runtime/workspace.py::WorkspaceContext` | implemented |
| Workspace resolution | `src/runtime/workspace.py::WorkspaceResolver` | implemented |
| Workspace validation error | `src/runtime/workspace.py::WorkspaceValidationError` | implemented |
| Port/process contract | `src/runtime/ports.py` | implemented, local validation pending |
| Semantic runtime assembly | `src/gateway/bootstrap.py::build_memory_gateway()` | implemented, local validation pending |
| Shared memory/vector statistics | `src/gateway/memory_statistics.py::MemoryStatisticsService` | implemented, local validation pending |
| Isolated local validator | `scripts/validate_p1_05_local.py` | implemented |

Without an explicit workspace, production retains the existing Vault and SQLite transition paths. Explicit acceptance contexts use the isolated P0-03 paths and collection.

## 5. Workspace Resource Contract

Each `WorkspaceContext` resolves:

- Vault and raw archive
- storage root
- `lingji_state.db`
- `lingji_memory.db`
- Qdrant mode, path or URL, and collection
- logs and cache
- runtime settings and task queue database
- backups, derived files, temporary files and reports

Production and acceptance paths must not overlap. Qdrant collection names must differ even when a remote URL is shared.

## 6. Long-Term Memory Entry Points

| Capability | Current long-term entry | Status |
|---|---|---|
| Memory gateway | `src/gateway/memory_gateway.py::MemoryGateway` | implemented; semantic-aware |
| Runtime assembly | `src/gateway/bootstrap.py::build_memory_gateway()` | semantic and statistics wired |
| AI profiles | `src/gateway/profiles.py::AIProfileRegistry` | implemented |
| Lexical/semantic fusion | `src/retrieval/hybrid.py::HybridRetriever` | implemented |
| Semantic contracts | `src/retrieval/semantic.py` | implemented |
| Qdrant provider | `src/retrieval/qdrant_provider.py::QdrantSemanticProvider` | implemented and wired |
| Embedding provider | `src/model_center/embedding.py::OllamaEmbeddingProvider` | implemented and wired |
| Embedding factory | `src/model_center/embedding.py::build_embedding_provider()` | implemented |
| Enhanced Chinese fallback | `src/retrieval/enhanced.py` | implemented |
| Rebuildable memory index | `src/retrieval/memory_db.py::MemoryDatabase` | implemented |
| Chunking | `src/retrieval/chunker.py::MarkdownChunker` | implemented |
| Context Pack | `src/retrieval/context_pack.py::ContextPackBuilder` | implemented |
| Incremental lexical sync | `src/retrieval/incremental_sync.py::IncrementalMemorySynchronizer` | coordinator implementation detail |
| Lexical/vector coordinator | `src/retrieval/index_coordinator.py::MemoryIndexCoordinator` | implemented and wired |
| Shared status service | `src/gateway/memory_statistics.py::MemoryStatisticsService` | implemented and wired |
| Permanent-memory lifecycle | `src/memory/lifecycle.py::MemoryLifecycleService` | implemented |
| State and events | `src/storage/state_db.py::StateDatabase` | implemented |
| MCP tools/resources/prompts | `src/mcp_server.py` | coordinated indexing and status publishing |
| MCP CLI startup | `run_mcp_server.py` | implemented |

Current semantic and status chain:

```text
build_memory_gateway()
  -> EmbeddingProvider
  -> QdrantSemanticProvider
  -> HybridRetriever.semantic_provider
  -> MemoryIndexCoordinator.semantic_provider
  -> MemoryGateway
  -> MemoryStatisticsService
  -> atomic memory_status.json
```

A semantic initialization error returns a lexical-only Gateway and a structured warning. It does not fail startup or fabricate vector counts.

## 7. Provider And Status Boundaries

```text
src/model_center/embedding.py
  -> vectors and verified model state

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

src/gateway/memory_statistics.py
  -> memory/vector/embedding counters and health
  -> no memory text or vectors
  -> status snapshot for the control process
```

Qdrant is not a permanent memory authority or a second ranking pipeline. The control process must not open embedded Qdrant merely to display status.

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

MCP document writes now route through `MemoryGateway.rebuild()` so lexical, semantic and status state are updated together.

## 9. Control, Settings And UI Entry Points

| Capability | Entry |
|---|---|
| Control service | `src/control/service.py::LocalControlService` |
| Control API | `src/control/api.py::create_control_app()` |
| Memory status | `GET /api/memory/status` |
| Vector status | `GET /api/vector/status` |
| Vector coverage | `GET /api/vector/coverage` |
| Brain status | `GET /api/brain/status` |
| MCP contract status | `GET /api/mcp/status` |
| Runtime settings | `src/control/runtime_settings.py::RuntimeSettingsStore` |
| Control startup | `run_control_api.py` |
| Model inventory | `src/model_center/inventory.py::LocalModelInventoryService` |
| Tauri entry | `desktop/lingji-control/src/main.tsx` |
| Tauri API client | `desktop/lingji-control/src/api.ts` |
| UI smoke | `desktop/lingji-control/scripts/ui-modular-smoke.mjs` |

Tauri uses only the authenticated Local Control API on `127.0.0.1:8766`.

Remaining control/UI gaps:

- Runtime Settings lacks complete editable memory, vector, workspace and MCP groups
- no final Vector Center page
- no final Memory Inspector page
- local acceptance and full regression remain pending

## 10. Compatibility Capabilities To Migrate

| Capability | Current compatibility entry | Mainline status/target |
|---|---|---|
| Qdrant | `second_brain/vector_store.py::VectorStore` | adapted, wired and observable under `src` |
| Ollama embedding fallback | `second_brain/embedding.py::OllamaEmbedder` | adapted and wired under Model Center |
| Structured sources/conversations/messages | `second_brain/db.py` | rebuildable source read model planned |
| Memory versions | `second_brain/db.py` | revision read model planned |
| Relations and conflicts | `second_brain/conflict/`, DB tables | unified read models planned |
| Acceptance scenarios | `second_brain/acceptance.py` | capability contracts and new isolated validators |
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

P1-05 does not modify this contract.

## 13. Testing Map

Existing memory/runtime suites:

- `tests/test_memory_retrieval.py`
- `tests/test_memory_lifecycle.py`
- `tests/test_permanent_memory_gateway.py`
- `tests/test_incremental_index_sync.py`
- `tests/test_workspace_contract.py`
- `tests/test_memory_capability_contract.py`

Phase 1 suites:

- `tests/test_embedding_provider.py`
- `tests/test_qdrant_semantic_provider.py`
- `tests/test_memory_index_coordinator.py`
- `tests/test_semantic_runtime_wiring.py`
- `tests/test_memory_statistics.py`
- `tests/test_status_snapshot_wiring.py`
- `tests/test_control_api.py`

Reports:

- `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`
- `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_01_EMBEDDING_PROVIDER_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_02_QDRANT_SEMANTIC_PROVIDER_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_03_MEMORY_INDEX_COORDINATOR_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_04_SEMANTIC_RUNTIME_WIRING_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_05_MEMORY_VECTOR_STATUS_TEST_REPORT.md`

Current evidence:

- workspace contract: 8 passed in isolated environment
- embedding fake-transport suite: 13 passed
- Qdrant 1.12 direct in-memory API smoke: passed
- committed P1-05 and full repository pytest: pending complete checkout
- real Ollama, bge-m3 and Windows runtime: pending

## 14. Before Coding Checklist

1. Confirm branch and remote HEAD.
2. Read the architecture plan, roadmap and current status.
3. Resolve runtime resources through `WorkspaceResolver`.
4. Preserve `HybridRetriever` as the only final ranking path.
5. Preserve lexical success when semantic providers fail.
6. Use the shared `MemoryStatisticsService`; do not invent UI counters.
7. Do not let Tauri or the control process access embedded Qdrant directly.
8. Add tests and a Markdown report for each major capability.
9. Do not call Phase 1 validated until the isolated local validator and full regression pass.
