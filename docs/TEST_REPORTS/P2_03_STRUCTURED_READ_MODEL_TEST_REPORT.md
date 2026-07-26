# P2-03 Structured Read Model（结构化读取模型）测试报告

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `d17d0bbca3d079c763b584df87578a5a8d312953`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_REVIEW`

## 1. 本轮目标

本轮只完成 P2-03 后端合同收口：

1. 把平行 `*_contract.py` 包装层合并回正式实现。
2. 保留权限继承、Schema Version（数据库结构版本）、Vector Tri-state（向量三态）和 503 脱敏修复。
3. 增加 HTTP/HTTPS URL（统一资源定位符）认证信息和敏感查询参数脱敏。
4. 增加单一实现检查。
5. 不开始 P2-03B，不开发 Tauri，不合并正式分支。

## 2. 单一正式实现

当前唯一正式类和工厂：

```text
src/sources/read_model.py::SourceReadModel
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

Package Export（包导出）合同：

```python
from src.sources import SourceReadModel as A
from src.sources.read_model import SourceReadModel as B
assert A is B

from src.gateway import MemoryInspectorFacade as C
from src.gateway.memory_inspector import MemoryInspectorFacade as D
assert C is D
```

已删除：

```text
src/sources/read_model_contract.py
src/gateway/memory_inspector_contract.py
src/control/api_contract.py
```

`src/control/__init__.py` 不再调用 `install_control_api_contract()`，`create_control_app()` 不依赖 package import side effect（包导入副作用）或 Monkey Patch（猴子补丁）。

## 3. SourceReadModel 合同

正式 `src/sources/read_model.py` 直接包含：

- Schema Version validation（结构版本验证）。
- `privacy_inherited`。
- `projects_inherited`。
- `agent_scope_inherited`。
- Source→Conversation 继承同步。
- Conversation→Message 继承同步。
- 显式子级覆盖保护。
- 旧 v1 表的继承列增量添加与保守回填。

Schema Version 合同：

```text
不存在 -> 写入 1
等于 1 -> 正常
不等于 1 -> SourceReadModelError
```

预置 `schema_version=2` 时，初始化失败且数据库中的版本必须仍为 `2`。

## 4. 权限继承测试

测试代码覆盖：

- Source 从 `private` 收紧为 `restricted` 后，旧继承型 Conversation/Message 立即不可被原 Agent（智能体）读取。
- 显式 Conversation/Message 权限不被 Source 更新覆盖。
- Agent Scope（智能体范围）更新后立即生效。
- Source Upsert（更新或插入）未提供权限字段时保留已有值，避免部分更新意外重置权限。

## 5. Vector Tri-state 合同

`rebuild_required` 直接保留 Snapshot（快照）原值：

```text
True  -> true
False -> false
None  -> null
```

测试覆盖 Memory Vector（记忆向量）顶层和每个 Chunk（文本分块）在 `None` 时均返回 `null`。

## 6. Inspector 503 脱敏

正式实现位于 `src/control/api.py`。

外部固定响应：

```json
{
  "detail": {
    "code": "READ_MODEL_UNAVAILABLE",
    "message": "Structured read model is unavailable"
  }
}
```

测试构造包含以下内容的 SQLite 异常：

```text
D:\Users\Secret\lingji_memory.db
C:\Users\Owner\memory.db
```

响应不得包含：

```text
C:\
D:\
Users
lingji_memory.db
memory.db
```

原始异常只允许写入内部 logger（日志记录器）。

## 7. URL 脱敏

`src/sources/service.py::_safe_reference()` 现在：

- 删除 URL username/password（用户名和密码）。
- 删除 fragment（片段）。
- 删除敏感 query parameter（查询参数）。
- 保留协议、主机、端口、安全路径和非敏感查询参数。

敏感键：

```text
token
access_token
api_key
apikey
key
secret
signature
sig
credential
authorization
session
cookie
```

测试示例：

```text
https://user:pass@example.com/file?id=123&token=secret#private
-> https://example.com/file?id=123
```

并验证结果中不存在 `user`、`pass`、`token`、`secret` 和 fragment 内容。

## 8. 修改文件

正式代码：

```text
src/sources/read_model.py
src/sources/service.py
src/sources/__init__.py
src/gateway/memory_inspector.py
src/gateway/__init__.py
src/control/api.py
src/control/__init__.py
```

测试：

```text
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

删除：

```text
src/sources/read_model_contract.py
src/gateway/memory_inspector_contract.py
src/control/api_contract.py
```

未修改：

```text
desktop/lingji-control/
second_brain/
生产 Vault
生产 SQLite
生产 Qdrant
```

## 9. 已执行辅助检查

在隔离临时目录执行：

```text
Python py_compile（静态编译）             PASS
临时 SQLite Schema 初始化                PASS
继承型 Source 权限同步                   PASS
显式 Conversation 权限保留               PASS
schema_version=2 拒绝且不降级             PASS
URL 示例脱敏                              PASS
单一实现文件静态扫描                      PASS
```

这些检查不是正式 pytest，不得替代集中测试结果。

## 10. 要求执行的重点测试

```powershell
python -m pytest `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

## 11. 要求执行的直接相关回归

```powershell
python -m pytest `
  tests/test_memory_retrieval.py `
  tests/test_permanent_memory_gateway.py `
  tests/test_workspace_contract.py `
  tests/test_control_api.py `
  -v --tb=short
```

## 12. 实际 pytest 结果

当前开发对话无法取得完整远程仓库运行环境，先前网络检查返回：

```text
Could not resolve host: github.com
```

因此两组 pytest 尚未执行。

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

`Verified Commit` 保持 `NOT_EXECUTED`，不得把实现提交自动写成验证提交。

## 13. 未执行项目

```text
完整 pytest
npm
Tauri
Ollama
真实 Qdrant
P2-01
P2-02
本机 Codex
```

## 14. 数据安全

```text
读取生产聊天正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
切换生产模型: NO
创建或删除生产 Collection: NO
修改 Tauri: NO
```

## 15. 当前结论

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_REVIEW
```

P2-03 当前不允许合并。

## 16. 测试通过后的状态更新

仅当两组指定测试全部通过，才更新为：

```text
IMPLEMENTED_FOCUSED_TESTED
NOT_MERGED_AWAITING_REVIEW
```

届时报告必须记录：

- 实际执行命令。
- passed（通过数）。
- failed（失败数）。
- skipped（跳过数）。
- 最终验证 HEAD（最新提交）。

## 17. 下一阶段

下一步不是 P2-04。

P2-03 集中测试和代码审查通过后进入：

```text
P2-03B Structured Ingestion Wiring（结构化采集接线）
```

P2-03B 完成后才开始：

```text
P2-04 Memory Inspector（记忆检查器）
```
