# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Development Branch（开发分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `d17d0bbca3d079c763b584df87578a5a8d312953`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
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

开发前必须确认真实服务、数据流和 Workspace（工作区），不能仅凭目录名猜测功能归属。

## 2. 当前统一运行链路

```text
src/extraction/
  -> Raw Snapshot（原始快照）和 Vault 文档
  -> P2-03B 待接线 Structured Read Model（结构化读取模型）写入
  -> MemoryIndexCoordinator（记忆索引协调器）
       -> lingji_memory.db Lexical Index（词法索引）
       -> QdrantSemanticProvider（Qdrant 语义提供器）
  -> HybridRetriever（混合检索器）
  -> ContextPackBuilder（上下文包构建器）
  -> MemoryGateway（记忆网关）
       -> MemoryStatisticsService（记忆统计服务）
       -> memory_status.json
  -> MemoryInspectorFacade（记忆检查器门面）
       -> authenticated 8766 GET API（带认证的只读接口）
  -> MCP / Local Control API（本地控制接口）
  -> Tauri UI
```

P2-03 的 Read Model（读取模型）是可重建查询层，不取代采集管线、MemoryGateway 或 HybridRetriever。

## 3. 数据权威与索引

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

Workspace raw path
= 原始导入材料

src/storage/state_db.py
= 任务、处理状态、队列和 Audit Event（审计事件）

src/retrieval/memory_db.py
= 可重建 Lexical/Metadata Index（词法与元数据索引）

src/sources/read_model.py
= 可重建 Structured Read Model（结构化读取模型）

src/retrieval/qdrant_provider.py
= 可重建 Semantic Index Provider（语义索引提供器）

<workspace storage>/memory_status.json
= 可重建 Runtime Status Snapshot（运行状态快照）
```

`second_brain/db.py` 仍是 Compatibility Data（兼容数据）和迁移证据，不是最终数据权威。

## 4. Workspace 入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Workspace 名称 | `src/runtime/workspace.py::WorkspaceName` | 已实现并验证 |
| Workspace 对象 | `src/runtime/workspace.py::WorkspaceContext` | 已实现并验证 |
| Workspace 解析 | `src/runtime/workspace.py::WorkspaceResolver` | 已实现并验证 |
| Workspace 验证错误 | `src/runtime/workspace.py::WorkspaceValidationError` | 已实现 |
| Port Contract（端口合同） | `src/runtime/ports.py` | 已实现并验证 |
| P1 本机验收 | `scripts/validate_p1_05_local.py` | 已通过 |
| P2-02 隔离验收 | `scripts/validate_p2_02_local.py` | 已通过 |
| P2-03 隔离测试 | `tests/test_memory_inspector_facade.py` | 已编写，待 pytest |

Production（生产）与 Acceptance（验收）路径不得重叠。

## 5. 正式记忆入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Memory Gateway | `src/gateway/memory_gateway.py::MemoryGateway` | 已实现并验证 |
| Runtime Assembly（运行时装配） | `src/gateway/bootstrap.py::build_memory_gateway()` | 已实现并验证 |
| AI Profile（AI 权限配置） | `src/gateway/profiles.py::AIProfileRegistry` | 已实现 |
| Hybrid Retrieval（混合检索） | `src/retrieval/hybrid.py::HybridRetriever` | 已实现 |
| Semantic Contract（语义合同） | `src/retrieval/semantic.py` | 已实现 |
| Qdrant Provider | `src/retrieval/qdrant_provider.py::QdrantSemanticProvider` | 已实现并接线 |
| Embedding Provider（向量嵌入提供器） | `src/model_center/embedding.py::OllamaEmbeddingProvider` | 已实现并接线 |
| Memory Database（记忆数据库） | `src/retrieval/memory_db.py::MemoryDatabase` | 已实现 |
| Chunker（文本分块器） | `src/retrieval/chunker.py::MarkdownChunker` | 已实现 |
| Context Pack（上下文包） | `src/retrieval/context_pack.py::ContextPackBuilder` | 已实现 |
| Lexical/Vector Coordinator（词法与向量协调器） | `src/retrieval/index_coordinator.py::MemoryIndexCoordinator` | 已实现并验证 |
| Status Service（状态服务） | `src/gateway/memory_statistics.py::MemoryStatisticsService` | 已实现并验证 |
| Memory Lifecycle（记忆生命周期） | `src/memory/lifecycle.py::MemoryLifecycleService` | 已实现 |
| State/Audit（状态与审计） | `src/storage/state_db.py::StateDatabase` | 已实现 |
| MCP | `src/mcp_server.py` | 已接入 |

语义初始化失败时，Gateway 降级为 Lexical-only（仅词法检索），不得伪造向量成功状态。

## 6. P2-03 单一正式实现

仓库中只保留一个正式 `SourceReadModel`：

```text
src/sources/read_model.py::SourceReadModel
```

该文件直接负责：

- Schema Version validation（数据库结构版本验证）。
- Source/Conversation/Message 派生表。
- Stable ID（稳定标识符）。
- Idempotent Upsert（幂等更新或插入）。
- `privacy_inherited`、`projects_inherited`、`agent_scope_inherited`。
- Source→Conversation 和 Conversation→Message 继承同步。
- 显式子级权限覆盖保护。
- 分页、筛选、排序和关联读取。

Package Export（包导出）：

```text
src/sources/__init__.py
-> from .read_model import SourceReadModel
```

仓库中只保留一个正式 `MemoryInspectorFacade`：

```text
src/gateway/memory_inspector.py::MemoryInspectorFacade
```

该文件直接负责：

- Memory 列表和详情。
- Message→Memory→Chunk 关联。
- Chunk→Vector 诊断。
- `rebuild_required` true/false/null 三态。
- live provider（实时提供器）存在时查询单 Chunk 状态。
- snapshot-only（仅快照）时返回 `exists=null`。
- 不返回 raw vector（原始向量）或完整 Qdrant payload（载荷）。

Package Export：

```text
src/gateway/__init__.py
-> from .memory_inspector import MemoryInspectorFacade
```

已删除平行实现：

```text
src/sources/read_model_contract.py
src/gateway/memory_inspector_contract.py
```

## 7. 权限感知查询与 URL 脱敏

正式入口：

```text
src/sources/service.py::SourceQueryService
src/sources/service.py::ViewerContext
```

职责：

- Owner/Agent（所有者/智能体）权限过滤。
- Privacy Filter（隐私过滤）。
- Agent Scope（智能体范围）。
- Workspace 响应标识。
- 路径引用脱敏。
- HTTP/HTTPS URL（统一资源定位符）用户名、密码、敏感查询参数和 fragment（片段）脱敏。

敏感查询参数：

```text
token, access_token, api_key, apikey, key, secret,
signature, sig, credential, authorization, session, cookie
```

## 8. Control API

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Control Service（控制服务） | `src/control/service.py::LocalControlService` | 已实现 |
| Control API | `src/control/api.py::create_control_app()` | 已实现 |
| Memory Status | `GET /api/memory/status` | 已实现并验证 |
| Vector Status | `GET /api/vector/status` | 已实现并验证 |
| Vector Coverage | `GET /api/vector/coverage` | 已实现并验证 |
| Brain Status | `GET /api/brain/status` | 已实现并验证 |
| Inspector Status | `GET /api/memory/inspector/status` | 已实现，待重点测试 |
| Source/Conversation/Message API | `GET /api/memory/inspector/*` | 已实现，待重点测试 |
| Memory/Source/Vector API | `GET /api/memory/inspector/memories/*` | 已实现，待重点测试 |

`src/control/api.py` 直接实现 Inspector 503 脱敏：

```text
READ_MODEL_UNAVAILABLE
Structured read model is unavailable
```

完整异常只进入内部 logger（日志记录器）。

`src/control/__init__.py` 没有 Monkey Patch（猴子补丁）或 import side effect（导入副作用）。已删除：

```text
src/control/api_contract.py
```

Inspector API 只增加 GET，不增加写入、编辑或删除记忆的路由。

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

ChatGPT Adapter 已能解析逐条消息，但当前正式采集链路尚未自动写入 Structured Read Model。该接线属于 P2-03B，本任务没有开始。

## 10. Tauri 边界

```text
8765 = second_brain Compatibility API（兼容接口）
8766 = authenticated Local Control API（带认证的本地控制接口）
8767 = optional MCP Streamable HTTP（可选 MCP 流式接口）
stdio = default local MCP transport（默认本地 MCP 传输）
```

Tauri 只能通过 8766 访问正式控制接口，不得直连 SQLite、Qdrant、Ollama、8765 或 8767。

本轮未修改 `desktop/lingji-control/`。

## 11. P2-03 测试地图

重点测试：

```text
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

直接相关 Regression Test（回归测试）：

```text
tests/test_memory_retrieval.py
tests/test_permanent_memory_gateway.py
tests/test_workspace_contract.py
tests/test_control_api.py
```

新增合同检查：

- Package Export 与直接模块导入得到同一个类对象。
- 三个 `*_contract.py` 文件不存在。
- `create_control_app.__module__ == "src.control.api"`。
- 不存在 Monkey Patch 标记。
- URL 认证信息和敏感查询参数不泄漏。

当前只完成辅助静态编译、临时 SQLite 冒烟和静态扫描，pytest 尚未执行。

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_REVIEW
```

## 12. 下一步

```text
P2-03 集中 pytest 与代码审查
-> P2-03B Structured Ingestion Wiring（结构化采集接线）
-> P2-04 Memory Inspector（记忆检查器）
```

当前不得合并正式分支，不得 force push。
