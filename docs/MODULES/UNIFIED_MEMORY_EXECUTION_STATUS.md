# UNIFIED_MEMORY_EXECUTION_STATUS.md — 统一记忆系统实时执行状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Combined Development Branch（联合开发分支）: `work/p2-03b-ingestion-wiring`  
> P2-03 Base Commit（基础提交）: `9f5f444e389cd549db653471c3a34ef27a109e15`  
> Combined Implementation Commit（联合实现提交）: `82a13334d475584869e92801b60e65bbc654937d`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Combined Merge State（联合合并状态）: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 权威顺序

```text
真实代码
-> 最新 Test Report（测试报告）
-> PROJECT_STATUS.md
-> 本执行状态表
-> Roadmap（路线图）原始规划
```

## 2. 阶段状态

| 阶段 | 任务 | 状态 | 证据 |
|---|---|---|---|
| P0-02 | Port Contract（端口合同） | `MERGED_AND_VALIDATED` | P0-02 报告 |
| P0-03 | Workspace Contract（工作区合同） | `MERGED_AND_VALIDATED` | P0-03 报告 |
| P1-01 ~ P1-05 | Unified Semantic Memory（统一语义记忆） | `MERGED_AND_VALIDATED` | P1-05 本机验收 |
| P2-01 | Vector Center（向量中心） | `MERGED_AND_VALIDATED` | P2-01 报告 |
| P2-02 | Collection Migration（向量集合迁移） | `MERGED_AND_VALIDATED` | P2-02 报告 |
| P2-03 | Structured Read Model（结构化读取模型） | `IMPLEMENTED_NOT_TESTED` | P2-03 测试报告 |
| P2-03B | Structured Ingestion Wiring（结构化采集接线） | `IMPLEMENTED_NOT_TESTED` | P2-03B 测试报告 |
| P2-04 | Memory Inspector（记忆检查器） | `BLOCKED_BY_COORDINATED_REVIEW` | 不得提前开始 |
| P2-05 | Startup Contract/Test Quality（启动合同与测试质量） | `DEFERRED` | 后续集中回归 |
| P2-06 | Production bge-m3 Switch（生产模型切换） | `DEFERRED` | 等待质量对比和受控切换 |

## 3. 联合开发分支

```text
work/p2-03b-ingestion-wiring
```

该分支包含：

```text
P2-03 Structured Read Model
+
P2-03B Structured Ingestion Wiring
```

当前不合并 `feature/second-brain-memory`。

## 4. P2-03 当前合同

- Source/Conversation/Message（来源、对话、消息）派生 Schema（数据库结构）。
- Stable ID（稳定标识符）和 Idempotent Upsert（幂等更新或插入）。
- Privacy Filter（隐私过滤）和 Agent Scope（智能体范围）。
- 父子权限继承同步和显式子级保护。
- Schema Version（数据库结构版本）验证。
- Message→Memory→Chunk→Vector 只读关联。
- `rebuild_required` true/false/null 三态。
- Inspector 503 稳定错误和路径脱敏。
- HTTP/HTTPS URL（统一资源定位符）认证信息与敏感参数脱敏。
- 8766 只读 Inspector API（检查器接口）。

状态：

```text
IMPLEMENTED_NOT_TESTED
```

## 5. P2-03B 当前合同

正式数据流：

```text
Raw Snapshot（原始快照）
-> Adapter（适配器）
-> Vault write（知识库写入）
-> on_documents_written
-> StructuredReadModelSink
-> SourceReadModel.upsert_bundle()
-> StateDatabase.append_event()
```

已实现：

- ChatGPT Markdown 与结构化消息一次标准化生成。
- Raw/Vault 相对引用。
- Structured Sink 幂等写入。
- Memory Link 安全条件。
- 索引失败不回滚 Vault 或结构化来源。
- `structured_ingestion_completed` Audit Event（审计事件）。
- `entity_type=structured_ingestion`。
- `entity_id=execution_id`。
- Audit Event 写入失败不影响主流程。
- Pipeline、ChatGPT 和 Structured Sink 统一稳定错误摘要。

状态：

```text
IMPLEMENTED_NOT_TESTED
```

## 6. 唯一安全错误摘要

正式入口：

```text
src/extraction/errors.py::safe_extraction_error
```

使用位置：

```text
src/extraction/pipeline.py
src/extraction/adapters/chatgpt.py
src/extraction/structured_sink.py
```

外部只返回稳定摘要，完整异常只进入 logger（日志记录器）。

## 7. 联合最小测试

指定测试：

```powershell
python -m pytest `
  tests/test_structured_ingestion.py `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

新增集成测试代码使用：

```text
TemporaryDirectory
MemoryDatabase
SourceReadModel
StructuredReadModelSink
StateDatabase
Fake Adapter
Fake Vault Sink
```

验证：

- 真实临时 SQLite 写入。
- 幂等 Source/Conversation/Message。
- 正文详情。
- Pipeline 顺序。
- 索引失败降级。
- Windows 路径不进入 `index_error`。
- Audit Event 可查询。
- ChatGPT warning 脱敏。

## 8. 当前测试结果

当前环境无法解析 `github.com`，未能物化完整仓库运行环境。

```text
pytest: NOT EXECUTED
py_compile: NOT EXECUTED
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

辅助代码审查不能替代 pytest。

## 9. 禁止范围

```text
不创建新分支
不 rebase
不 force push
不修改 Tauri
不运行完整 pytest
不运行第二批历史回归
不运行 npm
不运行 Ollama
不运行真实 Qdrant
不读取生产 ChatGPT Export
不访问生产 Vault/SQLite
不调用本机 Codex
不合并正式分支
不开始 P2-04
```

## 10. 当前联合状态

```text
P2-03:  IMPLEMENTED_NOT_TESTED
P2-03B: IMPLEMENTED_NOT_TESTED
Combined Development Branch: work/p2-03b-ingestion-wiring
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 11. 测试通过后的状态

仅当指定测试全部通过时更新为：

```text
P2-03:  IMPLEMENTED_FOCUSED_TESTED
P2-03B: IMPLEMENTED_FOCUSED_TESTED
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 12. 下一步

停止开发，等待联合代码审查和一次集中测试。

不要开始 P2-04 Memory Inspector（记忆检查器），等待统一审查后再安排3号开发工程师。
