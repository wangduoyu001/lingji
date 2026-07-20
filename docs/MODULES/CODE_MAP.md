# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Combined Development Branch（联合开发分支）: `work/p2-03b-ingestion-wiring`  
> P2-03 Base Commit（基础提交）: `9f5f444e389cd549db653471c3a34ef27a109e15`  
> Combined Implementation Commit（联合实现提交）: `82a13334d475584869e92801b60e65bbc654937d`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> P2-03 Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> P2-03B Status（状态）: `IMPLEMENTED_NOT_TESTED`

## 1. 仓库职责

```text
src/
= 长期平台主线

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）
```

## 2. 当前统一采集与记忆链路

```text
src/extraction/
  -> Raw Snapshot（原始快照）
  -> Adapter.extract()
       -> documents
       -> structured_sources
  -> VaultExtractionSink.write_batch()
  -> on_documents_written
  -> StructuredReadModelSink.write_batch()
       -> SourceReadModel.upsert_bundle()
       -> StateDatabase.append_event()
  -> MemoryIndexCoordinator（记忆索引协调器）
       -> lingji_memory.db Lexical Index（词法索引）
       -> QdrantSemanticProvider（Qdrant 语义提供器）
  -> HybridRetriever（混合检索器）
  -> MemoryGateway（记忆网关）
  -> MemoryInspectorFacade（记忆检查器门面）
  -> authenticated 8766 GET API（带认证的只读接口）
```

P2-03 Read Model（读取模型）是可重建查询层，不取代 Vault、raw、MemoryGateway 或 HybridRetriever。

## 3. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

storage/raw
= 原始导入材料

src/storage/state_db.py
= 队列、处理状态和 Audit Event（审计事件）

src/retrieval/memory_db.py
= 可重建 Lexical/Metadata Index（词法与元数据索引）

src/sources/read_model.py
= 可重建 Structured Read Model（结构化读取模型）

src/retrieval/qdrant_provider.py
= 可重建 Semantic Index Provider（语义索引提供器）
```

`second_brain/db.py` 仍是 Compatibility Data（兼容数据）和迁移证据。

## 4. P2-03 正式入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Source Read Model（来源读取模型） | `src/sources/read_model.py::SourceReadModel` | `IMPLEMENTED_NOT_TESTED` |
| Permission Query（权限查询） | `src/sources/service.py::SourceQueryService` | `IMPLEMENTED_NOT_TESTED` |
| Viewer Contract（查看者合同） | `src/sources/service.py::ViewerContext` | `IMPLEMENTED_NOT_TESTED` |
| Memory Inspector Facade | `src/gateway/memory_inspector.py::MemoryInspectorFacade` | `IMPLEMENTED_NOT_TESTED` |
| Inspector Builder | `src/control/memory_inspector.py::build_memory_inspector` | `IMPLEMENTED_NOT_TESTED` |
| Inspector API | `src/control/api.py::create_control_app()` | `IMPLEMENTED_NOT_TESTED` |

正式实现只有：

```text
src/sources/read_model.py::SourceReadModel
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

不存在平行 `*_contract.py` 包装层或 Monkey Patch（猴子补丁）。

## 5. P2-03B 正式入口

| 能力 | 正式入口 | 状态 |
|---|---|---|
| Structured Models（结构化传输模型） | `src/extraction/models.py` | `IMPLEMENTED_NOT_TESTED` |
| ChatGPT Mapping（ChatGPT 映射） | `src/extraction/adapters/chatgpt.py::ChatGPTExportAdapter` | `IMPLEMENTED_NOT_TESTED` |
| Structured Sink（结构化写入器） | `src/extraction/structured_sink.py::StructuredReadModelSink` | `IMPLEMENTED_NOT_TESTED` |
| Pipeline（处理管线） | `src/extraction/pipeline.py::ExtractionPipeline` | `IMPLEMENTED_NOT_TESTED` |
| Runtime Assembly（运行时装配） | `src/extraction/bootstrap.py::build_extraction_pipeline()` | `IMPLEMENTED_NOT_TESTED` |
| Safe Error Summary（安全错误摘要） | `src/extraction/errors.py::safe_extraction_error` | `IMPLEMENTED_NOT_TESTED` |
| Audit Store（审计存储） | `src/storage/state_db.py::StateDatabase.append_event` | 已有正式接口，P2-03B 已接线 |

## 6. Audit Event 合同

`StructuredReadModelSink` 只使用：

```python
state_db.append_event(
    event_type,
    "structured_ingestion",
    execution_id,
    dict(payload),
)
```

事件：

```text
event_type  = structured_ingestion_completed
entity_type = structured_ingestion
entity_id   = execution_id
```

事件失败只写入 logger，不影响主流程。不保留 `record_event` 旁路。

## 7. 统一异常脱敏

唯一正式工具：

```text
src/extraction/errors.py::safe_extraction_error
```

调用位置：

```text
src/extraction/pipeline.py
src/extraction/adapters/chatgpt.py
src/extraction/structured_sink.py
```

外部只返回稳定摘要；完整异常仅进入 logger（日志记录器）。

## 8. Pipeline 顺序与降级

正式顺序：

```text
preserve_raw
-> Adapter
-> Vault write
-> on_documents_written
-> Structured Sink
```

索引回调失败时：

- Vault 结果保留。
- `indexed=false`。
- `index_error` 不包含异常原文或路径。
- Structured Source/Conversation/Message 继续写入。
- Memory Link 按索引失败合同跳过。

## 9. Workspace 与端口边界

```text
8765 = second_brain Compatibility API（兼容接口）
8766 = authenticated Local Control API（带认证的本地控制接口）
8767 = optional MCP Streamable HTTP（可选 MCP 流式接口）
stdio = default local MCP transport（默认本地 MCP 传输）
```

Tauri 只能访问 8766，不得直连 SQLite、Qdrant、Ollama、8765 或 8767。

P2-03/P2-03B 使用当前 Workspace 的：

```text
vault_path
storage_path
state_db_path
memory_db_path
```

## 10. 最小联合测试地图

```text
tests/test_structured_ingestion.py
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

`tests/test_structured_ingestion.py` 包括：

- 真实临时 `MemoryDatabase`。
- 真实 `SourceReadModel`。
- 真实 `StructuredReadModelSink`。
- 真实 `StateDatabase`。
- 幂等 Source/Conversation/Message 写入。
- Message 正文详情。
- Pipeline 顺序。
- 索引失败降级与路径脱敏。
- Audit Event 查询。
- ChatGPT warning 脱敏。

计划命令：

```powershell
python -m pytest `
  tests/test_structured_ingestion.py `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

当前 pytest 未执行。

## 11. 当前状态

```text
P2-03:  IMPLEMENTED_NOT_TESTED
P2-03B: IMPLEMENTED_NOT_TESTED
Combined Development Branch: work/p2-03b-ingestion-wiring
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 12. 下一步

停止开发，等待联合代码审查和一次集中测试。

不得开始 P2-04 Memory Inspector（记忆检查器），不得合并正式分支，不得 force push。
