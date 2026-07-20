# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-20  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Validated Code Commit（已验证代码提交）: `8a4860553edfbb698665c7dcb1f8bfaf3f556eba`  
> Current Development（当前开发）: P2-03 Structured Read Model（结构化读取模型）

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

Provider（提供器）、Coordinator（协调器）和 Gateway（网关）由 `build_memory_gateway()` 统一装配。

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

src/retrieval/qdrant_provider.py
= 可重建 Semantic Index Provider（语义向量索引提供器）

<workspace storage>/memory_status.json
= 可重建 Runtime Status Snapshot（运行状态快照）
```

`second_brain/db.py` 仍是迁移期 Compatibility Data（兼容数据），不是最终数据权威。

Source/Conversation/Message（来源、对话、消息）数据必须迁移为可重建 Read Model（读取模型），不能让兼容数据库成为长期事实源。

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

当前正式链路：

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

语义初始化失败时，Gateway 降级为 Lexical-only（仅词法检索），不得伪造向量成功状态。

## 6. Provider 与状态边界

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
```

Control Process 不得为了显示状态再次打开 Embedded Qdrant（嵌入式 Qdrant）。

## 7. Collection Migration（向量集合迁移）

| 能力 | 入口 | 状态 |
|---|---|---|
| Migration Service（迁移服务） | `src/retrieval/collection_migration.py::VectorCollectionMigrationService` | 已合并并验证 |
| Production Plan CLI（生产计划命令行） | `scripts/prepare_vector_collection_migration.py` | 已实现 |
| Isolated Validation（隔离验收） | `scripts/validate_p2_02_local.py` | 已通过 |
| Migration Tests（迁移测试） | `tests/test_vector_collection_migration.py` | 重点测试通过 |

正式生产候选 Collection 尚未构建，生产模型尚未切换。

## 8. 统一采集入口

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

所有新采集必须进入 `src/extraction/`，不得扩展旧 Watcher 成为正式链路。

## 9. Control API 与 Tauri

| 能力 | 入口 | 状态 |
|---|---|---|
| Control Service | `src/control/service.py::LocalControlService` | 已实现 |
| Control API | `src/control/api.py::create_control_app()` | 已实现 |
| Memory Status | `GET /api/memory/status` | 已实现并验证 |
| Vector Status | `GET /api/vector/status` | 已实现并验证 |
| Vector Coverage | `GET /api/vector/coverage` | 已实现并验证 |
| Brain Status | `GET /api/brain/status` | 已实现并验证 |
| MCP Status | `GET /api/mcp/status` | 已实现 |
| Runtime Settings | `src/control/runtime_settings.py::RuntimeSettingsStore` | 已实现基础框架 |
| Control Startup | `run_control_api.py` | 已实现 |
| Tauri Entry | `desktop/lingji-control/src/main.tsx` | 已实现 |
| Tauri API Client | `desktop/lingji-control/src/api.ts` | 已实现，仅访问 8766 |
| Vector Center Page | `desktop/lingji-control/src/pages/VectorCenterPage.tsx` | 已合并并验证 |
| UI Smoke | `desktop/lingji-control/scripts/ui-modular-smoke.mjs` | 已包含 Vector Center |

当前 UI 缺口：

- Memory Inspector 尚未实现
- Runtime Settings 缺少完整 memory/vector/workspace/MCP 可编辑分组
- 知识中心、来源会话和 AI 权限可视化仍待完善

## 10. P2-03 计划入口

Code Map 中为 P2-03 保留的正式路径：

| 能力 | 目标路径 |
|---|---|
| Source/Conversation/Message Read Model（来源、对话、消息读取模型） | `src/sources/read_model.py` |
| Permission-aware Source Query（权限感知来源查询） | `src/sources/service.py` |
| Memory Inspector Facade（记忆检查器门面） | `src/gateway/memory_inspector.py` |
| Retrieval Trace（检索追踪） | `src/retrieval/trace.py` |
| Revision Read Model（修订读取模型） | `src/memory/revisions.py` |
| Relation Read Model（关系读取模型） | `src/memory/relations.py` |
| Conflict Candidate（冲突候选） | `src/memory/conflicts.py` |
| Legacy Export/Parity（旧数据导出与等价验证） | `src/migration/` |

P2-03 当前只负责 Structured Read Model（结构化读取模型）和只读 8766 API 合同。

P2-04 再开发 Tauri Memory Inspector 页面。

创建目标文件前必须先检查现有实现；如果真实代码已有更合适入口，应复用而不是重复创建。

## 11. Compatibility（兼容层）待迁移能力

| 能力 | 兼容入口 | 正式目标 |
|---|---|---|
| Structured Source/Conversation/Message | `second_brain/db.py` | `src/sources/` 可重建 Read Model |
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

最新本机汇总：

```text
223 passed
0 failed
8 skipped
```

测试数量相对 P1-05 有未核对差异，下一次全量 Regression Test（回归测试）必须解释。

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
