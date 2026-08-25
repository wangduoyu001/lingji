# P2-03B Structured Ingestion Wiring（结构化采集接线）

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

> Updated（更新时间）: 2026-07-21
> Branch（分支）: `work/p2-03b-ingestion-wiring`
> Base Branch（基础分支）: `work/p2-03-structured-read-model`
> Base Commit（基础提交）: `9f5f444e389cd549db653471c3a34ef27a109e15`
> Combined Implementation Commit（联合实现提交）: `82a13334d475584869e92801b60e65bbc654937d`
> Verified Commit（已验证提交）: `NOT_EXECUTED`
> P2-03 Status（P2-03 状态）: `IMPLEMENTED_NOT_TESTED`
> P2-03B Status（P2-03B 状态）: `IMPLEMENTED_NOT_TESTED`
> Combined Merge State（联合合并状态）: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 任务目标

P2-03B 让 ChatGPT Export Adapter（ChatGPT 导出适配器）在继续生成 Vault Markdown（知识库 Markdown）的同时，输出 Structured Source/Conversation/Message（结构化来源、对话、消息），并通过 `SourceReadModel.upsert_bundle()` 幂等写入 P2-03 Structured Read Model（结构化读取模型）。

本轮联合收口同时修复：

- Structured Ingestion Audit Event（结构化采集审计事件）写入。
- Pipeline（处理管线）索引失败信息脱敏。
- ChatGPT 单条 Conversation（对话）失败 warning（警告）脱敏。
- Structured Sink（结构化写入器）错误摘要统一。
- 真实临时 SQLite 最小集成测试代码。

不开发 P2-04，不修改 Tauri，不访问生产数据。

## 2. 正式数据流

```text
Input / ChatGPT Export
-> preserve_raw()
-> Adapter.extract()
-> ExtractionBatch
     -> documents
     -> structured_sources
-> VaultExtractionSink.write_batch()
-> on_documents_written
-> StructuredReadModelSink.write_batch()
-> SourceReadModel.upsert_bundle()
-> Audit Event
-> execution response
```

Pipeline 不包含 ChatGPT 特殊分支，其他 Adapter（适配器）未来可以复用同一 StructuredSource 合同。

## 3. 数据权威

```text
Obsidian Vault + Git
= 永久知识正文权威

storage/raw
= 原始材料权威

lingji_memory.db / SourceReadModel
= 可重建结构化查询数据

Qdrant
= 可重建语义索引
```

SourceReadModel 不成为新的永久正文权威。

## 4. 结构化传输模型

`src/extraction/models.py` 提供：

- `StructuredMessage`
- `StructuredConversation`
- `StructuredSource`
- `ExtractionBatch.structured_sources`

数据类保持 frozen（不可变），旧 Adapter 未提供结构化数据时继续使用默认空 tuple（元组）。

## 5. ChatGPT 映射与错误脱敏

同一次 `_normalize_conversation()` 结果同时用于：

- Markdown Document（Markdown 文档）。
- StructuredConversation（结构化对话）。

Message（消息）映射包括：

```text
external_id = node_id
role = author.role
author = author.name
occurred_at = create_time
sequence = 稳定排序后的顺序
content = 标准化文本
metadata = parent/model/is_branch/original_position/attachments
```

单条 Conversation 失败时：

```text
<conversation_id>: conversation extraction failed; see local logs
```

完整异常通过 `logger.exception()` 写入本地日志，并携带 Conversation ID；异常原文、数据库路径和用户目录不进入 `batch.warnings`。

## 6. 统一安全错误摘要

唯一正式实现：

```text
src/extraction/errors.py::safe_extraction_error
```

合同：

```python
def safe_extraction_error(exc: Exception, *, message: str) -> str:
    del exc
    return message
```

它不通过正则保留部分异常原文，只返回调用方提供的稳定摘要。

当前稳定摘要：

```text
Post-extraction index synchronization failed; see local logs
conversation extraction failed; see local logs
structured read model write failed; see local logs
```

## 7. Audit Event（审计事件）

`StructuredReadModelSink._event()` 使用正式接口：

```python
state_db.append_event(
    event_type,
    "structured_ingestion",
    execution_id,
    dict(payload),
)
```

完成事件：

```text
structured_ingestion_completed
```

合同：

- `entity_type = structured_ingestion`
- `entity_id = execution_id`
- payload 只包含状态、计数和安全 warning
- 事件写入失败只记录 logger，不影响结构化采集主流程
- 不保留 `record_event` 旁路

## 8. Pipeline 失败降级

当 `on_documents_written` 抛出异常：

- Vault 结果继续返回。
- `indexed = false`。
- `index_error` 使用固定安全摘要。
- Structured Source/Conversation/Message 继续写入。
- Memory Link（记忆关联）按 `indexing_succeeded=False` 跳过。
- 完整异常只进入 logger。

## 9. Raw/Vault 安全引用

Raw 引用只允许：

```text
raw:<relative path under storage/raw>
```

Vault 引用只允许：

```text
vault:<relative_path>
```

Structured Read Model 不保存输入文件、Vault 或数据库的绝对路径。

## 10. Bootstrap（运行时装配）

`build_extraction_pipeline()` 使用当前 Workspace（工作区）的：

- `settings.memory_db_path`
- `settings.storage_path`
- `settings.state_db_path`

创建并复用：

- `MemoryDatabase`
- `SourceReadModel`
- `StateDatabase`
- `StructuredReadModelSink`

不启动 Qdrant、Ollama、Tauri、8765 或 8767。

## 11. 最小集成测试代码

`tests/test_structured_ingestion.py` 已覆盖：

1. `TemporaryDirectory` + 真实 `MemoryDatabase`。
2. 真实 `SourceReadModel`。
3. 真实 `StructuredReadModelSink`。
4. 真实 `StateDatabase`。
5. Source→Conversation→Message 写入临时 SQLite。
6. 重复执行不产生重复 Source、Conversation、Message。
7. Message detail（消息详情）正文读取。
8. `structured_ingestion_completed` 可通过 `recent_events()` 查询。
9. Audit payload 不包含绝对路径。
10. Vault→index callback→Structured Sink 顺序。
11. 索引异常包含 Windows 路径时的稳定降级。
12. ChatGPT warning 不包含异常原文和本机路径。
13. Audit Event 写入失败不影响结构化写入。

## 12. 测试命令

仅允许执行：

```powershell
python -m pytest `
  tests/test_structured_ingestion.py `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

当前环境无法解析 `github.com`，无法物化完整仓库测试环境，因此 pytest 尚未执行。

## 13. 数据安全

```text
读取 Production ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
启动 Ollama: NO
修改 Tauri: NO
合并正式分支: NO
```

## 14. 当前状态

```text
P2-03:  IMPLEMENTED_NOT_TESTED
P2-03B: IMPLEMENTED_NOT_TESTED
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 15. 下一步

停止开发并等待统一审查与一次集中测试。

不得自行开始：

```text
P2-04 Memory Inspector（记忆检查器）
```
