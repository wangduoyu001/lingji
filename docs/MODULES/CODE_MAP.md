# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-20  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Verified Commit（已验证提交）: `b9950b4066fbb0b602c2ffba5109da2fa8371cf3`  
> Current Development（当前开发）: P2-03 Structured Read Model（结构化读取模型）`IMPLEMENTED_NOT_TESTED`

## 1. 仓库职责

```text
src/
= 长期平台主线

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）

second_brain/desktop/
= 旧 PySide6 兼容、验收和诊断界面
```

开发前必须确认真实服务和数据流，不能仅凭目录名猜测功能归属。

## 2. 当前统一运行链路

```text
src/extraction/
  -> Raw Snapshot（原始快照）和 Vault 文档
  -> lingji_memory.db Structured Read Model
       -> Source / Conversation / Message / MessageMemoryLink
  -> MemoryIndexCoordinator
       -> lingji_memory.db lexical index
       -> QdrantSemanticProvider
  -> HybridRetriever
  -> ContextPackBuilder
  -> MemoryGateway
       -> MemoryStatisticsService
       -> memory_status.json
  -> MemoryInspectorFacade
       -> authenticated 8766 GET API
  -> MCP / Local Control API
  -> Tauri UI
```

Provider（提供器）、Coordinator（协调器）和 Gateway（网关）由 `build_memory_gateway()` 统一装配。P2-03 的 Read Model 是可重建查询层，不取代采集管线、MemoryGateway 或 HybridRetriever。

## 3. 数据权威与索引

```text
Obsidian Vault + Git
= 永久记忆和正式知识文本

Workspace raw path
= 原始导入材料

src/storage/state_db.py
= 任务、处理状态、队列和 Audit Event（审计事件）

src/retrieval/memory_db.py
= 可重建 Lexical/Metadata Index（词法与元数据索引）

src/sources/read_model.py
= 可重建 Structured Read Model（结构化读取模型）

src/retrieval/qdrant_provider.py
= 可重建 Semantic Index Provider（语义向量索引提供器）

<workspace storage>/memory_status.json
= 可重建 Runtime Status Snapshot（运行状态快照）
```

`second_brain/db.py` 仍是迁移期 Compatibility Data（兼容数据），不是最终数据权威。

Source/Conversation/Message（来源、对话、消息）正式查询入口已经迁入 `src/sources/`，但本任务没有自动导入生产历史数据。

## 4. Workspace（工作区）入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Workspace 名称 | `src/runtime/workspace.py::WorkspaceName` | 已实现并验证 |
| Workspace 对象 | `src/runtime/workspace.py::WorkspaceContext` | 已实现并验证 |
| Workspace 解析 | `src/runtime/workspace.py::WorkspaceResolver` | 已实现并验证 |
| Workspace 验证错误 | `src/runtime/workspace.py::WorkspaceValidationError` | 已实现 |
| 端口合同 | `src/runtime/ports.py` | 已实现并验证 |
| P1 本机验收 | `scripts/validate_p1_05_local.py` | 已通过 |
| P2-02 隔离验收 | `scripts/validate_p2_02_local.py` | 已通过 |
| P2-03 Read Model 隔离测试 | `tests/test_memory_inspector_facade.py` | 已编写，待 pytest |

每个 Workspace 隔离：

- Vault
- Raw Archive（原始资料归档）
- `lingji_state.db`
- `lingji_memory.db`
- Qdrant 路径或 URL 与 Collection
- 日志和缓存
- Runtime Settings（运行时设置）
- 队列数据库
- 备份、派生文件和报告

Production 与 Acceptance 路径不得重叠。

## 5. 正式记忆入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Memory Gateway（记忆网关） | `src/gateway/memory_gateway.py::MemoryGateway` | 已实现，支持语义检索 |
| Runtime Assembly（运行时装配） | `src/gateway/bootstrap.py::build_memory_gateway()` | 已实现并验证 |
| AI Profile（AI 权限配置） | `src/gateway/profiles.py::AIProfileRegistry` | 已实现 |
| 混合检索 | `src/retrieval/hybrid.py::HybridRetriever` | 已实现 |
| 语义合同 | `src/retrieval/semantic.py` | 已实现 |
| Qdrant Provider | `src/retrieval/qdrant_provider.py::QdrantSemanticProvider` | 已实现并接线 |
| Embedding Provider | `src/model_center/embedding.py::OllamaEmbeddingProvider` | 已实现并接线 |
| Embedding Factory（构建工厂） | `src/model_center/embedding.py::build_embedding_provider()` | 已实现 |
| 中文短词回退 | `src/retrieval/enhanced.py` | 已实现 |
| Memory Database（记忆数据库） | `src/retrieval/memory_db.py::MemoryDatabase` | 已实现 |
| Chunker（文本分块器） | `src/retrieval/chunker.py::MarkdownChunker` | 已实现 |
| Context Pack（上下文包） | `src/retrieval/context_pack.py::ContextPackBuilder` | 已实现 |
| Incremental Sync（增量同步） | `src/retrieval/incremental_sync.py` | Coordinator 内部实现 |
| Lexical/Vector Coordinator（词法与向量协调器） | `src/retrieval/index_coordinator.py::MemoryIndexCoordinator` | 已实现并验证 |
| Status Service（状态服务） | `src/gateway/memory_statistics.py::MemoryStatisticsService` | 已实现并验证 |
| Memory Lifecycle（记忆生命周期） | `src/memory/lifecycle.py::MemoryLifecycleService` | 已实现 |
| State/Audit（状态与审计） | `src/storage/state_db.py::StateDatabase` | 已实现 |
| MCP | `src/mcp_server.py` | 已接入协调索引和状态发布 |
| Memory Inspector Facade | `src/gateway/memory_inspector.py::MemoryInspectorFacade` | 已实现，待重点测试 |

当前正式检索链路：

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

P2-03 不修改该排名链路。Memory 列表和详情复用 canonical `MemoryDatabase`，搜索召回仍由 `MemoryGateway`/`HybridRetriever` 负责。

语义初始化失败时，Gateway 降级为 Lexical-only（仅词法检索），不得伪造向量成功状态。

## 6. Structured Read Model（结构化读取模型）入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Schema 与稳定 ID | `src/sources/read_model.py::SourceReadModel` | 已实现，待重点测试 |
| Source Upsert/查询 | `SourceReadModel.upsert_source/list_sources/get_source` | 已实现，待重点测试 |
| Conversation Upsert/查询 | `SourceReadModel.upsert_conversation/list_conversations/get_conversation` | 已实现，待重点测试 |
| Message Upsert/查询 | `SourceReadModel.upsert_message/list_messages/get_message` | 已实现，待重点测试 |
| Message→Memory Link | `SourceReadModel.link_message_memory` | 已实现，待重点测试 |
| Explicit Rebuild（显式重建） | `SourceReadModel.rebuild` | 已实现，未用于生产数据 |
| Permission-aware Query（权限感知查询） | `src/sources/service.py::SourceQueryService` | 已实现，待重点测试 |
| Viewer Contract（查看者合同） | `src/sources/service.py::ViewerContext` | 已实现 |
| Control Builder | `src/control/memory_inspector.py::build_memory_inspector` | 已实现，避免第二个 Qdrant Client |

派生表：

```text
source_read_model_meta
source_records
conversation_records
message_records
message_memory_links
```

列表 Message 只返回 `content_preview`、`content_length`、`content_hash`；完整正文只由明确的 Message Detail API 返回。

## 7. Provider 与状态边界

```text
src/model_center/embedding.py
  -> 向量生成和实际模型状态

src/retrieval/qdrant_provider.py
  -> semantic candidates（语义候选）
  -> upsert/delete
  -> count/exists/coverage/status

src/retrieval/index_coordinator.py
  -> lexical commit first（词法优先提交）
  -> canonical snapshot（标准快照）
  -> semantic delta（语义增量）
  -> structured degraded warnings（结构化降级警告）

src/retrieval/hybrid.py
  -> canonical resolve（标准结果解析）
  -> privacy/Agent Scope 过滤
  -> RRF（倒数排名融合）和 metadata boost（元数据加权）

src/gateway/memory_statistics.py
  -> memory/vector/embedding 统计与健康状态
  -> 不包含正文和原始向量
  -> 为 Control Process（控制进程）提供快照

src/gateway/memory_inspector.py
  -> 只有已注入 live provider 时才查询 per-chunk exists
  -> snapshot-only 时返回 exists=null
  -> 不返回 raw vector 或完整 Qdrant payload
```

Control Process 不得为了显示状态再次打开 Embedded Qdrant（嵌入式 Qdrant）。

## 8. Collection Migration（向量集合迁移）

| 能力 | 入口 | 状态 |
|---|---|---|
| Migration Service（迁移服务） | `src/retrieval/collection_migration.py::VectorCollectionMigrationService` | 已合并并验证 |
| Production Plan CLI（生产计划命令行） | `scripts/prepare_vector_collection_migration.py` | 已实现 |
| Isolated Validation（隔离验收） | `scripts/validate_p2_02_local.py` | 已通过 |
| Migration Tests（迁移测试） | `tests/test_vector_collection_migration.py` | 重点测试通过 |

正式生产候选 Collection 尚未构建，生产模型尚未切换。

## 9. 统一采集入口

| 能力 | 正式入口 |
|---|---|
| Adapter Interface（适配器接口） | `src/extraction/base.py::ExtractionAdapter` |
| Adapter Registry（适配器注册表） | `src/extraction/registry.py::AdapterRegistry` |
| Pipeline（处理管线） | `src/extraction/pipeline.py::ExtractionPipeline` |
| Persistent Queue（持久队列） | `src/extraction/queue.py::SQLiteExtractionQueue` |
| Worker（工作进程） | `src/extraction/worker.py::ExtractionWorker` |
| Vault/Raw Sink（知识库与原始资料写入器） | `src/extraction/sink.py::VaultExtractionSink` |
| Runtime Assembly | `src/extraction/bootstrap.py::build_extraction_pipeline()` |
| ChatGPT Import | `src/extraction/adapters/chatgpt.py::ChatGPTExportAdapter` |
| Codex Capture | `src/extraction/adapters/codex.py::CodexWorkReportAdapter` |
| Web/Social Capture | `src/extraction/adapters/web.py::WebCaptureAdapter` |
| Media Extraction | `src/extraction/adapters/media.py::MediaExtractionAdapter` |

ChatGPT Adapter 已能解析逐条消息，但当前正式采集链路尚未自动写入 Structured Read Model。P2-03 只提供幂等接口和显式重建能力，不自动导入生产历史。

所有新采集必须进入 `src/extraction/`，不得扩展旧 Watcher 成为正式链路。

## 10. Control API 与 Tauri

| 能力 | 入口 | 状态 |
|---|---|---|
| Control Service | `src/control/service.py::LocalControlService` | 已实现 |
| Control API | `src/control/api.py::create_control_app()` | 已实现 |
| Memory Status | `GET /api/memory/status` | 已实现并验证 |
| Vector Status | `GET /api/vector/status` | 已实现并验证 |
| Vector Coverage | `GET /api/vector/coverage` | 已实现并验证 |
| Brain Status | `GET /api/brain/status` | 已实现并验证 |
| Memory Inspector Status | `GET /api/memory/inspector/status` | 已实现，待重点测试 |
| Source/Conversation/Message API | `GET /api/memory/inspector/*` | 已实现，待重点测试 |
| Memory/Source/Vector Linkage API | `GET /api/memory/inspector/memories/*` | 已实现，待重点测试 |
| MCP Status | `GET /api/mcp/status` | 已实现 |
| Runtime Settings | `src/control/runtime_settings.py::RuntimeSettingsStore` | 已实现基础框架 |
| Control Startup | `run_control_api.py` | 已实现 |
| Tauri Entry | `desktop/lingji-control/src/main.tsx` | 已实现 |
| Tauri API Client | `desktop/lingji-control/src/api.ts` | 已实现，仅访问 8766 |
| Vector Center Page | `desktop/lingji-control/src/pages/VectorCenterPage.tsx` | 已合并并验证 |
| UI Smoke | `desktop/lingji-control/scripts/ui-modular-smoke.mjs` | 已包含 Vector Center |

Inspector API 只增加 GET，不增加写入、编辑或删除记忆的路由。

当前 UI 缺口：

- P2-04 Tauri Memory Inspector 尚未实现
- Runtime Settings 缺少完整 memory/vector/workspace/MCP 可编辑分组
- 知识中心、来源会话和 AI 权限可视化仍待完善

## 11. Compatibility（兼容层）待迁移能力

| 能力 | 兼容入口 | 正式目标 |
|---|---|---|
| Structured Source/Conversation/Message | `second_brain/db.py` | `src/sources/` 可重建 Read Model；生产导入未执行 |
| Memory Versions（记忆版本） | `second_brain/db.py` | Revision Read Model |
| Relations/Conflicts（关系与冲突） | `second_brain/conflict/` 与 DB 表 | 统一只读模型 |
| Acceptance Scenario（验收场景） | `second_brain/acceptance.py` | 正式 Capability Contract（能力合同） |
| PySide6 Flow | `second_brain/desktop/` | Tauri 能力迁移 |

兼容层只提供迁移证据，不得继续扩展为正式产品。

## 12. 端口地图

```text
8765 = second_brain Compatibility API
8766 = authenticated Local Control API
8767 = src MCP Streamable HTTP
stdio = default local MCP transport
```

## 13. 当前测试地图

重点 Memory/Runtime（记忆与运行时）测试：

```text
tests/test_memory_retrieval.py
tests/test_memory_lifecycle.py
tests/test_permanent_memory_gateway.py
tests/test_incremental_index_sync.py
tests/test_workspace_contract.py
tests/test_memory_capability_contract.py
tests/test_embedding_provider.py
tests/test_qdrant_semantic_provider.py
tests/test_memory_index_coordinator.py
tests/test_semantic_runtime_wiring.py
tests/test_memory_statistics.py
tests/test_status_snapshot_wiring.py
tests/test_control_api.py
tests/test_vector_collection_migration.py
```

P2-03 新增：

```text
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

P2-03 当前只完成静态编译、临时 SQLite 冒烟和禁止项扫描，重点 pytest 尚未执行。

最近一次已记录全量本机汇总仍为：

```text
223 passed
0 failed
8 skipped
```

该数字不是 P2-03 测试结果。测试数量相对 P1-05 有未核对差异：`UNRECONCILED_TEST_COUNT_DELTA`。

## 14. 开发前检查

1. 确认 Remote HEAD（远程最新提交）。
2. 阅读 `DOCUMENTATION_MAINTENANCE.md`、`PROJECT_STATUS.md` 和 `UNIFIED_MEMORY_EXECUTION_STATUS.md`。
3. 使用 `WorkspaceResolver` 解析运行资源。
4. 保留 `HybridRetriever` 为唯一最终排名路径。
5. 保留语义失败时的词法成功路径。
6. 使用共享 `MemoryStatisticsService`，不得伪造 UI 计数。
7. Tauri 和 Control Process 不得直接访问 Embedded Qdrant。
8. 每项重大能力必须包含测试和 Markdown 报告。
9. 已验证且未受影响的 P1/P2 测试不重复执行。

## 15. 下一步

```text
P2-03 重点 pytest 与代码审查
-> 合并正式分支
-> P2-04 Memory Inspector
```

当前合并状态：`NOT_MERGED_AWAITING_REVIEW`。
