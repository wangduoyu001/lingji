# P2-03 Structured Read Model 实施计划

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `0ce11ab56630d0d31c4828a0d63f0ea6e875729f`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_REVIEW`

## 1. 目标

P2-03 建立可重建、只读、Workspace 隔离的 Source/Conversation/Message/Memory/Chunk/Vector 读取合同。

数据权威保持不变：

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_memory.db
= 可重建词法、元数据和 Structured Read Model

Qdrant
= 可重建语义索引
```

`second_brain.sqlite3` 仅是兼容和迁移证据。

## 2. 当前实现

正式入口：

```text
src/sources/read_model.py
src/sources/read_model_contract.py
src/sources/service.py
src/gateway/memory_inspector.py
src/gateway/memory_inspector_contract.py
src/control/memory_inspector.py
src/control/api.py
src/control/api_contract.py
```

新增派生表：

```text
source_read_model_meta
source_records
conversation_records
message_records
message_memory_links
```

## 3. 权限继承方案

选择方案 A：显式 inherited 标记。

Conversation 和 Message 使用：

```text
privacy_inherited
projects_inherited
agent_scope_inherited
```

行为：

1. 子级没有显式字段时继承父级，并标记为 inherited。
2. Source 更新只同步 inherited Conversation 字段。
3. Conversation 更新只同步 inherited Message 字段。
4. 显式子级字段不被父级更新覆盖。
5. 权限同步与父级 Upsert 使用同一 SQLite 事务。

该方案避免查询时重复计算整条父子链，也保持现有分页 SQL 可复用。

## 4. Schema Version 合同

```text
不存在 schema_version -> 写入当前版本 1
schema_version == 1 -> 正常
schema_version != 1 -> SourceReadModelError
```

未知或更高版本禁止自动降级。

同版本的 additive columns 使用显式 `ALTER TABLE ADD COLUMN` 检查，不修改 schema_version。

## 5. Vector 三态

```text
True  -> true
False -> false
None  -> null
```

Memory Vector 顶层和 Chunk 明细必须读取同一个原始值，不使用 `bool(...)`。

## 6. 503 错误合同

外部响应：

```text
code: READ_MODEL_UNAVAILABLE
message: Structured read model is unavailable
```

SQLite 原始异常、Windows 路径、用户目录和数据库真实路径仅进入内部日志，不进入 API 响应。

## 7. 测试计划

重点测试：

```powershell
python -m pytest `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

直接相关回归：

```powershell
python -m pytest `
  tests/test_memory_retrieval.py `
  tests/test_permanent_memory_gateway.py `
  tests/test_workspace_contract.py `
  tests/test_control_api.py `
  -v --tb=short
```

当前环境无法解析 GitHub 主机，未取得完整仓库运行环境，因此 pytest 未执行。

## 8. 禁止范围

```text
不开发 Tauri
不开始 P2-04
不运行完整 pytest
不运行 npm
不运行 Ollama/Qdrant 真实验收
不重新验收 P2-01/P2-02
不调用本机 Codex
不合并正式分支
不 force push
```

## 9. 回滚

- 回退本分支新增合同模块和接线。
- 删除新增 inherited columns 需要重建派生 Read Model，不影响 Vault、raw、正式 Memory 或 Qdrant。
- API 脱敏包装可独立回退。

## 10. 下一阶段

P2-03 重点测试和审查完成后，下一阶段为：

```text
P2-03B Structured Ingestion Wiring
```

目标：

- ChatGPT Adapter 输出结构化 Source/Conversation/Message bundle。
- Extraction Pipeline 显式调用幂等 `SourceReadModel.upsert_bundle()`。
- 保持 raw/Vault 为来源证据。
- 失败时不破坏已写入 Vault 文档。
- 增加重新构建与删除来源后的派生数据清理测试。

P2-03B 完成后才进入：

```text
P2-04 Memory Inspector
```
