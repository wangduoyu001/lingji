# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Development Branch（开发分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `0ce11ab56630d0d31c4828a0d63f0ea6e875729f`  
> Status（状态）: P2-03 `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_REVIEW`

## 1. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility/Migration Runtime
```

本轮没有修改 Tauri，也没有开始 P2-04。

## 2. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 队列、任务、Runtime 与 Audit Event

lingji_memory.db
= 可重建 Lexical/Metadata Index
  + Structured Read Model

Qdrant
= 可重建 Semantic Index
```

`second_brain.sqlite3` 仍是兼容与迁移数据，不是长期事实源。

## 3. 已完成并验证阶段

```text
P0 Workspace/Port Contract          MERGED_AND_VALIDATED
P1 Unified Semantic Memory          MERGED_AND_VALIDATED
P2-01 Tauri Vector Center           MERGED_AND_VALIDATED
P2-02 Collection Migration Tool     MERGED_AND_VALIDATED
```

生产 `bge-m3` 切换和生产 Collection 重建仍未执行。

## 4. P2-03 当前实现

P2-03 已在独立分支实现：

- Source、Conversation、Message 派生表。
- Message→Memory、Memory→Chunk、Chunk→Vector 只读关系。
- 稳定 ID、幂等 Upsert、分页、排序和筛选。
- Owner/Agent Privacy 与 Agent Scope。
- Workspace 隔离和 8766 Token Authentication。
- 只读 `/api/memory/inspector/*` GET 路由。

本轮最小修复：

### 4.1 权限继承

采用 inherited 标记：

```text
privacy_inherited
projects_inherited
agent_scope_inherited
```

Source 或 Conversation 更新时只同步继承型子级；显式子级权限不被覆盖。

### 4.2 Vector 三态

```text
True  -> true
False -> false
None  -> null
```

Memory Vector 顶层和 Chunk 明细保持一致。

### 4.3 503 脱敏

外部仅返回：

```text
READ_MODEL_UNAVAILABLE
Structured read model is unavailable
```

SQLite 原文、数据库路径和用户目录不进入 API 响应。

### 4.4 Schema Version

```text
不存在 -> 写入 1
等于 1 -> 正常
不等于 1 -> SourceReadModelError
```

未知或更高版本不被自动覆盖。

## 5. 当前测试状态

本轮新增或更新：

```text
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

要求运行的重点测试和直接相关回归尚未执行。

原因：当前执行环境尝试拉取远程分支时返回：

```text
Could not resolve host: github.com
```

因此当前准确状态仍是：

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_REVIEW
```

不得描述为测试通过，不得合并正式分支。

## 6. 本轮未执行

```text
完整 pytest
npm
Tauri
Ollama
Qdrant 真实验收
P2-01 重复验收
P2-02 重复验收
本机 Codex
```

## 7. 数据安全

```text
读取生产聊天正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
切换生产模型: NO
创建或删除生产 Collection: NO
修改 Tauri: NO
```

## 8. 下一阶段

下一步不是 P2-04。

```text
P2-03B Structured Ingestion Wiring
```

目标：把 ChatGPT Adapter 等采集结果显式、幂等地写入 `SourceReadModel`，使 Source、Conversation 和 Message 查询拥有真实派生数据。

正式顺序：

```text
P2-03 重点 pytest 与直接相关回归
-> P2-03 代码审查
-> P2-03B Structured Ingestion Wiring
-> P2-04 Memory Inspector
-> 集中 Regression Test 与 Startup Contract 修复
-> Production bge-m3 candidate 与受控切换
```

## 9. 开发冻结规则

- 新记忆能力只进入 `src/`。
- 新采集能力只进入 `src/extraction/`。
- 正式桌面能力只进入 `desktop/lingji-control/`。
- Tauri 不得直连 8765、8767、SQLite、Qdrant 或 Ollama。
- 未完成重点测试和审查前，不得合并 P2-03。
- 不 force push。
