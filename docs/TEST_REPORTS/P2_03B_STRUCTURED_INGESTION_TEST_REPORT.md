# P2-03B Structured Ingestion Test Report（结构化采集测试报告）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03b-ingestion-wiring`  
> Base Commit（基础提交）: `9f5f444e389cd549db653471c3a34ef27a109e15`  
> Combined Implementation Commit（联合实现提交）: `82a13334d475584869e92801b60e65bbc654937d`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> P2-03 Status（P2-03 状态）: `IMPLEMENTED_NOT_TESTED`  
> P2-03B Status（P2-03B 状态）: `IMPLEMENTED_NOT_TESTED`  
> Combined Merge State（联合合并状态）: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 测试范围

本轮统一测试范围：

```text
tests/test_structured_ingestion.py
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

不运行完整 pytest，不单独运行第二批历史回归。

## 2. 新增最小真实集成测试

`tests/test_structured_ingestion.py` 现在包括：

### 2.1 真实临时 SQLite

使用：

```text
TemporaryDirectory
MemoryDatabase
SourceReadModel
StructuredReadModelSink
StateDatabase
```

执行：

```text
StructuredSource
-> StructuredConversation
-> StructuredMessage
-> SourceReadModel.upsert_bundle()
-> 临时 lingji_memory.db
```

验证：

- Source 数量为 1。
- Conversation 数量为 1。
- Message 数量为 1。
- Message detail（消息详情）能读取完整正文。
- 重复执行两次后记录数仍为 1/1/1。

### 2.2 Pipeline 顺序

使用轻量 Fake Adapter（伪适配器）和 Fake Vault Sink（伪知识库写入器），并使用真实 Structured Sink（结构化写入器）。

验证顺序：

```text
raw
-> adapter
-> vault
-> index callback
-> structured sink
```

核心合同：

```text
Vault write
-> on_documents_written
-> Structured Sink
```

### 2.3 索引失败降级

索引回调抛出：

```text
D:\Users\Secret\lingji_memory.db is locked
```

验证：

- Vault 结果仍返回。
- `indexed == false`。
- `index_error` 等于稳定安全摘要。
- `index_error` 不包含 `D:\`、`Users` 或数据库文件名。
- Structured Source/Conversation/Message 仍进入临时 SQLite。
- `structured_ingestion_completed` 事件仍产生。

### 2.4 Audit Event（审计事件）

使用真实 `StateDatabase` 验证：

```text
event_type  = structured_ingestion_completed
entity_type = structured_ingestion
entity_id   = execution_id
```

同时解析 `payload_json` 并确认不包含临时目录绝对路径。

另有测试验证 `append_event()` 抛出异常时，结构化写入仍返回 `written`。

### 2.5 ChatGPT warning 脱敏

构造单条 Conversation 失败，异常包含 Windows 绝对路径。

对外 warning 固定为：

```text
conv-1: conversation extraction failed; see local logs
```

验证 warning 不包含：

```text
D:\
Users
conversations.json
异常原文
```

## 3. 审计接口修复

`StructuredReadModelSink._event()` 现在只调用：

```python
state_db.append_event(
    event_type,
    "structured_ingestion",
    entity_id,
    dict(payload),
)
```

不存在 `record_event` 旁路。

事件写入失败：

- 不影响采集主流程。
- 完整异常只进入 logger（日志记录器）。
- 响应不包含数据库路径。

## 4. 统一异常脱敏

唯一安全摘要实现：

```text
src/extraction/errors.py::safe_extraction_error
```

使用位置：

```text
src/extraction/pipeline.py
src/extraction/adapters/chatgpt.py
src/extraction/structured_sink.py
```

稳定摘要：

```text
Post-extraction index synchronization failed; see local logs
conversation extraction failed; see local logs
structured read model write failed; see local logs
```

完整异常只通过 `logger.exception()` 留在本地日志。

## 5. 计划执行命令

```powershell
python -m pytest `
  tests/test_structured_ingestion.py `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

## 6. 实际执行结果

当前环境尝试获取完整远程仓库时失败：

```text
Could not resolve host: github.com
```

因此无法在当前对话中运行实际分支上的 pytest 或 py_compile（静态编译）。

```text
pytest: NOT EXECUTED
py_compile: NOT EXECUTED
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

代码存在、测试文件存在以及没有 CI 红灯都不等于测试通过。

## 7. 未执行项目

```text
完整 pytest
第二批历史回归
npm
Tauri
Ollama
真实 Qdrant
生产 ChatGPT Export
生产 Vault
生产 SQLite
本机 Codex
```

## 8. 数据安全

```text
读取 Production ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
启动生产导入: NO
修改 Tauri: NO
合并正式分支: NO
```

所有新增集成测试只使用临时目录和临时 SQLite。

## 9. 当前结论

```text
P2-03:  IMPLEMENTED_NOT_TESTED
P2-03B: IMPLEMENTED_NOT_TESTED
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

不能标记为测试通过，不能自行合并正式分支。

## 10. 测试通过后的状态

仅当指定命令全部通过时，更新为：

```text
P2-03:  IMPLEMENTED_FOCUSED_TESTED
P2-03B: IMPLEMENTED_FOCUSED_TESTED
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

届时必须记录：

- 实际执行命令。
- passed（通过数）。
- failed（失败数）。
- skipped（跳过数）。
- 最终验证 HEAD（最新提交）。

## 11. 下一步

停止开发并等待联合代码审查与一次集中本机测试。

不得开始 P2-04 Memory Inspector（记忆检查器）。
