# P2-03 Structured Read Model（结构化读取模型）测试报告

> Updated（更新时间）: 2026-07-20  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Verified Commit（已验证提交）: `b9950b4066fbb0b602c2ffba5109da2fa8371cf3`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Evidence（证据来源）: 真实代码与 Schema 审计、`py_compile` 静态编译、临时 SQLite 隔离冒烟；重点 pytest 待完整本机仓库执行

## 1. 任务目标

为 P2-04 Memory Inspector（记忆检查器）建立可重建、只读、权限感知、Workspace（工作区）隔离的 Source/Conversation/Message/Memory/Chunk/Vector 读取合同。

## 2. 开始基线

```text
Repository: wangduoyu001/lingji
Formal branch: feature/second-brain-memory
Baseline: 098a062ca3e3fd50fdf7029716bc18ba2a1c4008
Development branch: work/p2-03-structured-read-model
```

开始前正式分支与预期提交一致。只执行了一次远程基线确认。

## 3. 真实代码分析

### Canonical Memory

`src/retrieval/memory_db.py`：

- `memory_documents`
- `memory_chunks`
- `memory_meta`
- `memory_fts`
- WAL、foreign_keys、busy_timeout 和事务 context manager

### Compatibility Schema

`second_brain/db.py`：

- sources
- conversations
- messages
- memories
- memory_versions
- memory_relations
- conflicts

兼容表只作为迁移证据，不作为长期查询权威。

### Extraction Gap

ChatGPT Adapter 在解析阶段拥有逐条 message 的 node ID、角色、正文、时间、模型和顺序，但现有 Sink 最终仅保存整段对话 Markdown。P2-03 因此建立派生表和显式导入接口，不自动执行生产历史导入。

## 4. 实现文件

```text
src/sources/__init__.py
src/sources/read_model.py
src/sources/service.py
src/gateway/memory_inspector.py
src/gateway/__init__.py
src/control/memory_inspector.py
src/control/api.py

tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

## 5. Schema（数据库结构）

新增：

```text
source_read_model_meta
source_records
conversation_records
message_records
message_memory_links
```

Schema migration（结构迁移）使用 `CREATE TABLE/INDEX IF NOT EXISTS`，独立版本号为 `1`。

## 6. Stable ID（稳定 ID）

实现：

- Source stable ID
- Conversation stable ID
- Message stable ID
- existing external identity 优先复用
- repeated upsert 不新增重复记录

## 7. Pagination（分页）

合同：

```text
limit default 50
limit range 1..200
offset >= 0
```

响应：

```json
{
  "items": [],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 0,
    "has_more": false
  }
}
```

排序增加稳定 ID tie-breaker（并列排序补充键），相同时间不会随机跳动。

## 8. Privacy（隐私）与 Agent Scope（智能体范围）

已实现：

- Source privacy/project/scope 继承到 Conversation
- Conversation privacy/project/scope 继承到 Message
- Owner 显式返回 `viewer_scope=owner`
- Agent 查询复用 `AIProfileRegistry`
- restricted 对远程 Profile 不可见
- 无权限 privacy 请求返回空集
- 列表不返回完整 Message content

## 9. Filters（筛选）

支持：

### Source

- source_type
- privacy
- project
- status
- q

### Conversation

- source_id
- source_type
- privacy
- project
- from_time
- to_time
- q

### Message

- conversation_id
- source_id
- role
- from_time
- to_time
- q

### Memory

- memory_type
- status
- privacy
- project
- q

Memory 查询直接使用 `memory_documents`，不复制 HybridRetriever 排名。

## 10. Linkage（关联）

支持：

```text
Source -> Conversation
Conversation -> Message
Message -> Memory
Memory -> Chunk
Chunk -> Vector diagnostics
```

MessageMemoryLink 使用参数化 SQL、外键和唯一主键。

## 11. Vector Degraded State（向量降级状态）

有 live Semantic Provider 时：

```text
exists = true/false
source = live
```

只有 snapshot 或 provider 不可用时：

```text
exists = null
source = unavailable
```

未创建第二个 Embedded Qdrant Client，未返回 vector array 或完整 Qdrant payload。

## 12. API

新增 authenticated read-only GET routes（带认证的只读 GET 路由）：

```text
GET /api/memory/inspector/status
GET /api/memory/inspector/sources
GET /api/memory/inspector/sources/{source_id}
GET /api/memory/inspector/conversations
GET /api/memory/inspector/conversations/{conversation_id}
GET /api/memory/inspector/conversations/{conversation_id}/messages
GET /api/memory/inspector/messages
GET /api/memory/inspector/messages/{message_id}
GET /api/memory/inspector/memories
GET /api/memory/inspector/memories/{memory_id}
GET /api/memory/inspector/memories/{memory_id}/source
GET /api/memory/inspector/memories/{memory_id}/vector
```

无 POST/PATCH/DELETE Inspector route。

## 13. 已执行检查

### 13.1 Python 静态编译

执行范围：

```text
src/sources/*.py
src/gateway/memory_inspector.py
src/control/memory_inspector.py
src/control/api.py
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

结果：

```text
py_compile: PASS
syntax failures: 0
```

这不是 pytest，不得解释为功能测试通过。

### 13.2 临时 SQLite 隔离冒烟

执行内容：

- 创建临时 SQLite
- 创建临时 canonical memory/chunk
- 初始化 Structured Read Model
- repeated bundle upsert
- Source/Conversation/Message 查询
- Message→Memory 查询
- Owner 列表不返回正文
- snapshot-only vector 返回 unknown/null
- Acceptance 与 Production 数据库路径隔离

结果：

```text
isolated smoke: PASS
production data touched: NO
```

该冒烟是当前对话内的辅助证据，不代替仓库重点 pytest。

### 13.3 禁止项静态扫描

结果：

```text
8765 reference in new implementation: 0
8767 reference in new implementation: 0
QdrantClient construction: 0
qdrant_client direct import: 0
raw vector response: 0
Inspector write route: 0
```

## 14. 未执行测试

未执行：

```powershell
python -m pytest `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

未执行直接相关回归：

```powershell
python -m pytest `
  tests/test_memory_retrieval.py `
  tests/test_permanent_memory_gateway.py `
  tests/test_workspace_contract.py `
  tests/test_control_api.py `
  -v --tb=short
```

未运行完整 pytest，符合低积分任务要求。

## 15. Passed / Failed / Skipped

针对要求的 pytest：

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

针对已执行辅助检查：

```text
py_compile checks: passed
isolated SQLite smoke: passed
static forbidden scan: passed
```

## 16. 已知限制

1. P2-03 不自动把生产 ChatGPT 导出写入 Read Model。
2. `second_brain.sqlite3` 导入器未实现，因为本阶段没有必要自动迁移兼容数据。
3. Read Model 首次初始化只创建派生表，不产生 Source/Conversation/Message 数据。
4. 完整正文仅来自显式 Message Detail API，但仍属于派生副本，权威仍是 Vault/raw provenance。
5. snapshot 无法证明单个 chunk 是否存在于 Qdrant，因此返回 null。
6. 当前测试数量差异仍为 `UNRECONCILED_TEST_COUNT_DELTA`，本任务未运行完整 pytest 核对。

## 17. 数据安全

```text
读取生产聊天正文: NO
修改 Production Vault: NO
修改 Production SQLite runtime data: NO
访问 Production Qdrant: NO
切换生产模型: NO
创建生产 bge-m3 Collection: NO
删除旧 Collection: NO
暴露原始向量: NO
调用本机 Codex: NO
```

开发与辅助冒烟只使用临时目录和临时 SQLite。

## 18. 回滚

回滚本分支提交即可。

派生表可以显式删除并重新建立，不影响：

- Vault
- Git history
- raw archive
- canonical memory text
- Qdrant collection

## 19. 合并状态

```text
NOT_MERGED_AWAITING_REVIEW
```

## 20. 下一步

仅在 P2-03 代码审查和重点测试通过后：

```text
P2-04 Memory Inspector
```
