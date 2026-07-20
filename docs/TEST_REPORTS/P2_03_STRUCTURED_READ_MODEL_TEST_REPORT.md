# P2-03 Structured Read Model 测试报告

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `0ce11ab56630d0d31c4828a0d63f0ea6e875729f`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_REVIEW`

## 1. 本轮目标

本轮只修复 P2-03 后端读取合同，不开发 P2-04，不修改 Tauri，不访问生产 Vault、生产 SQLite、Ollama 或 Qdrant。

修复范围：

1. Source/Conversation/Message 权限继承漂移。
2. `rebuild_required` 的 `true/false/null` 三态。
3. 503 错误脱敏。
4. Source Read Model Schema Version 合同。

## 2. 权限继承修复

采用方案 A：显式继承标记。

Conversation 和 Message 增加：

```text
privacy_inherited
projects_inherited
agent_scope_inherited
```

规则：

- 子级未显式提供字段时，标记为 inherited。
- Source 更新后，只同步 inherited Conversation 字段。
- Conversation 更新后，只同步 inherited Message 字段。
- 显式子级权限、项目和 Agent Scope 不被父级无条件覆盖。
- 同步与父级 Upsert 在同一 SQLite 事务中完成，查询立即生效。

实现入口：

```text
src/sources/read_model_contract.py
src/sources/__init__.py
```

新增测试覆盖：

- Source 从 `private` 收紧为 `restricted` 后，旧继承型 Conversation/Message 不再对 ChatGPT 可见。
- 显式子级权限不被 Source 更新覆盖。
- Agent Scope 从 ChatGPT 改为 Ollama 后立即生效。

## 3. Vector 三态修复

禁止把未知状态转换为 `False`。

合同：

```text
True  -> true
False -> false
None  -> null
```

Memory Vector 顶层与每个 Chunk 使用同一个原始 `snapshot.get("rebuild_required")` 值。

实现入口：

```text
src/gateway/memory_inspector_contract.py
src/gateway/__init__.py
src/control/memory_inspector.py
```

新增测试：

```text
snapshot rebuild_required=None
-> vector.rebuild_required is None
-> vector.chunks[0].rebuild_required is None
```

## 4. 503 脱敏修复

Inspector 503 对外只返回：

```json
{
  "detail": {
    "code": "READ_MODEL_UNAVAILABLE",
    "message": "Structured read model is unavailable"
  }
}
```

SQLite 原始异常、数据库路径和本机绝对路径不进入响应体。完整异常仅写入内部 logger。

实现入口：

```text
src/control/api_contract.py
src/control/__init__.py
```

新增测试构造包含以下内容的 SQLite 异常：

```text
D:\Users\Secret\lingji_memory.db
C:\Users\Owner\memory.db
```

并验证响应不包含：

```text
C:\
D:\
Users
lingji_memory.db
memory.db
```

## 5. Schema Version 合同

初始化规则：

```text
schema_version 不存在 -> 写入 1
schema_version == 1   -> 正常初始化
schema_version != 1   -> 抛出 SourceReadModelError
```

未知或更高版本不得被自动覆盖为 1。

新增测试：

```text
预置 schema_version=2
-> SourceReadModel 初始化失败
-> 数据库中版本仍为 2
```

## 6. 本次测试文件

```text
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

## 7. 要求执行的重点测试

```powershell
python -m pytest `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

## 8. 要求执行的直接相关回归

```powershell
python -m pytest `
  tests/test_memory_retrieval.py `
  tests/test_permanent_memory_gateway.py `
  tests/test_workspace_contract.py `
  tests/test_control_api.py `
  -v --tb=short
```

## 9. 实际执行结果

当前执行环境尝试拉取同一远程分支时失败：

```text
Could not resolve host: github.com
```

因此无法取得完整仓库和依赖环境，未执行上述 pytest。

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

已执行辅助检查：

```text
新修复模块 py_compile: PASS
远程文件与分支写入: PASS
真实 pytest: NOT EXECUTED
```

不得将本状态描述为测试通过。

## 10. 未执行项目

```text
完整 pytest
npm
Tauri
Ollama
Qdrant 真实验收
P2-01 验收
P2-02 验收
本机 Codex
```

## 11. 数据安全

```text
读取生产聊天正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
切换生产模型: NO
创建或删除生产 Collection: NO
修改 Tauri: NO
```

## 12. 当前结论

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_REVIEW
```

P2-03 仍不允许合并。

## 13. 下一阶段

下一步不是 P2-04。

```text
P2-03B Structured Ingestion Wiring
```

目标：把 ChatGPT Adapter 等采集结果显式、幂等地写入 `SourceReadModel`，让 Source、Conversation 和 Message 查询拥有真实派生数据。

顺序：

```text
P2-03 重点测试与审查
-> P2-03B Structured Ingestion Wiring
-> P2-04 Memory Inspector
```
