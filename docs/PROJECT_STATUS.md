# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Combined Development Branch（联合开发分支）: `work/p2-03b-ingestion-wiring`  
> P2-03 Base Commit（基础提交）: `9f5f444e389cd549db653471c3a34ef27a109e15`  
> Combined Implementation Commit（联合实现提交）: `82a13334d475584869e92801b60e65bbc654937d`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> P2-03 Status（P2-03 状态）: `IMPLEMENTED_NOT_TESTED`  
> P2-03B Status（P2-03B 状态）: `IMPLEMENTED_NOT_TESTED`  
> Combined Merge State（联合合并状态）: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）
```

本轮没有创建新分支，没有 rebase，没有 force push，没有修改 Tauri，没有开始 P2-04，也没有合并正式分支。

## 2. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、Runtime State（运行状态）和 Audit Event（审计事件）

lingji_memory.db
= 可重建 Lexical/Metadata Index（词法与元数据索引）
  + Structured Read Model（结构化读取模型）

Qdrant
= 可重建 Semantic Index（语义索引）
```

`second_brain.sqlite3` 仍是 Compatibility Data（兼容数据）和迁移证据，不是长期事实源。

## 3. 已完成并验证阶段

```text
P0 Workspace/Port Contract（工作区与端口合同）  MERGED_AND_VALIDATED
P1 Unified Semantic Memory（统一语义记忆）      MERGED_AND_VALIDATED
P2-01 Vector Center（向量中心）                 MERGED_AND_VALIDATED
P2-02 Collection Migration（向量集合迁移）      MERGED_AND_VALIDATED
```

Production bge-m3 Switch（生产模型切换）和生产 Collection（向量集合）重建仍未执行。

## 4. P2-03 Structured Read Model

状态：

```text
IMPLEMENTED_NOT_TESTED
```

已实现：

- Source/Conversation/Message（来源、对话、消息）派生表。
- Stable ID（稳定标识符）和 Idempotent Upsert（幂等更新或插入）。
- Privacy Filter（隐私过滤）和 Agent Scope（智能体范围）。
- `privacy_inherited`、`projects_inherited`、`agent_scope_inherited`。
- Source→Conversation 与 Conversation→Message 权限同步。
- 显式子级权限保护。
- Schema Version（数据库结构版本）验证。
- Message→Memory→Chunk→Vector 只读关联。
- `rebuild_required` true/false/null 三态。
- Inspector 503 稳定错误和路径脱敏。
- HTTP/HTTPS URL（统一资源定位符）认证信息和敏感查询参数脱敏。
- 只读 `/api/memory/inspector/*` GET API（接口）。

正式单一实现：

```text
src/sources/read_model.py::SourceReadModel
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

## 5. P2-03B Structured Ingestion Wiring

状态：

```text
IMPLEMENTED_NOT_TESTED
```

当前正式数据流：

```text
Raw Snapshot（原始快照）
-> Adapter（适配器）
-> Vault write（知识库写入）
-> on_documents_written
-> StructuredReadModelSink
-> SourceReadModel.upsert_bundle()
-> Audit Event（审计事件）
```

已实现：

- `StructuredMessage`、`StructuredConversation`、`StructuredSource`。
- ChatGPT Adapter 同时生成 Markdown 和结构化消息。
- Raw/Vault 安全相对引用。
- Structured Sink 幂等写入 Read Model。
- Memory Link 仅在索引成功且 Memory 可见时写入。
- Structured Sink 失败不回滚 Raw/Vault。
- `StateDatabase.append_event()` 正式审计事件接线。
- `entity_type = structured_ingestion`。
- `entity_id = execution_id`。
- Audit Event 写入失败不影响采集主流程。

## 6. 统一异常脱敏

唯一正式工具：

```text
src/extraction/errors.py::safe_extraction_error
```

使用位置：

```text
src/extraction/pipeline.py
src/extraction/adapters/chatgpt.py
src/extraction/structured_sink.py
```

对外稳定摘要：

```text
Post-extraction index synchronization failed; see local logs
<conversation_id>: conversation extraction failed; see local logs
structured read model write failed; see local logs
```

完整异常只进入本地 logger（日志记录器），不得进入 API response（接口响应）、`batch.warnings` 或 `index_error`。

## 7. 最小集成测试代码

`tests/test_structured_ingestion.py` 已增加：

- `TemporaryDirectory` + 真实 `MemoryDatabase`。
- 真实 `SourceReadModel`。
- 真实 `StructuredReadModelSink`。
- 真实 `StateDatabase`。
- Source/Conversation/Message 写入和正文读取。
- 重复写入幂等验证。
- Vault→index callback→Structured Sink 顺序验证。
- 索引异常包含 Windows 路径时的降级验证。
- `structured_ingestion_completed` 审计事件验证。
- Audit payload 绝对路径泄漏检查。
- ChatGPT warning 脱敏验证。
- Audit Event 写入失败不影响主流程验证。

## 8. 当前测试状态

计划执行：

```powershell
python -m pytest `
  tests/test_structured_ingestion.py `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

当前环境无法解析 `github.com`，无法物化完整仓库测试环境。

```text
pytest: NOT EXECUTED
py_compile: NOT EXECUTED
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

不得将代码已提交、测试文件存在或没有 CI 红灯解释为测试通过。

## 9. 未执行范围

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

## 10. 数据安全

```text
读取 Production ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
切换生产模型: NO
创建或删除生产 Collection: NO
修改 Tauri: NO
```

## 11. 当前联合状态

```text
P2-03:  IMPLEMENTED_NOT_TESTED
P2-03B: IMPLEMENTED_NOT_TESTED
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

当前不能合并正式分支。

## 12. 下一步

停止开发，等待联合代码审查和一次集中本机测试。

指定测试全部通过后，才允许更新为：

```text
P2-03:  IMPLEMENTED_FOCUSED_TESTED
P2-03B: IMPLEMENTED_FOCUSED_TESTED
Combined Merge State: NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

不要开始 P2-04 Memory Inspector（记忆检查器）。
