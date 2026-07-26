# P2-03 Structured Read Model（结构化读取模型）实施计划

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `d17d0bbca3d079c763b584df87578a5a8d312953`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_REVIEW`

## 1. 目标

P2-03 建立可重建、只读、Workspace（工作区）隔离的 Source/Conversation/Message（来源、对话、消息）读取合同，为后续 Memory Inspector（记忆检查器）提供稳定后端能力。

数据权威保持不变：

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

storage/raw
= 原始导入材料

lingji_memory.db
= 可重建 Lexical/Metadata Index（词法与元数据索引）
  + Structured Read Model（结构化读取模型）

Qdrant
= 可重建 Semantic Index（语义索引）
```

`second_brain.sqlite3` 仅作为 Compatibility Data（兼容数据）和迁移证据。

## 2. 单一正式实现

P2-03 不再使用平行包装层或运行时 Monkey Patch（猴子补丁：导入后动态替换函数或类）。

正式入口只有：

```text
src/sources/read_model.py::SourceReadModel
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

已删除：

```text
src/sources/read_model_contract.py
src/gateway/memory_inspector_contract.py
src/control/api_contract.py
```

`src/sources/__init__.py` 与 `src/gateway/__init__.py` 直接导出正式类，`src/control/__init__.py` 不再通过导入副作用修改 API Factory（接口工厂）。

## 3. Schema Version（数据库结构版本）合同

初始化规则：

```text
schema_version 不存在 -> 写入当前版本 1
schema_version == 1   -> 正常初始化
schema_version != 1   -> 抛出 SourceReadModelError
```

未知或更高版本不得被自动覆盖为 `1`。

同版本的新增继承列通过显式列检查和 `ALTER TABLE` 添加，不改变版本号。

## 4. 权限继承合同

Conversation 和 Message 直接在正式 Schema（数据库结构）中维护：

```text
privacy_inherited
projects_inherited
agent_scope_inherited
```

规则：

1. 子级未显式提供字段时，从父级继承并记录 inherited（继承）标记。
2. Source 更新时只同步继承型 Conversation。
3. Source 更新后，继承型 Message 通过其 Conversation 的有效权限同步。
4. Conversation 更新时只同步继承型 Message。
5. 显式子级权限、项目和 Agent Scope（智能体范围）不被父级无条件覆盖。
6. 父级 Upsert（更新或插入）与继承同步处于同一 SQLite 事务。
7. 旧 v1 表增加继承列时，根据当前父子值进行保守回填，避免把明显不同的显式子级误标为继承。

## 5. Vector Tri-state（向量三态）合同

`rebuild_required` 必须保持三态：

```text
True  -> true
False -> false
None  -> null
```

Memory Vector（记忆向量）顶层和每个 Chunk（文本分块）使用同一个原始 Snapshot（快照）值，禁止 `bool(snapshot.get(...))`。

## 6. Inspector 503 错误合同

`src/control/api.py` 直接处理 Read Model（读取模型）和 SQLite 故障。

外部响应固定为：

```json
{
  "detail": {
    "code": "READ_MODEL_UNAVAILABLE",
    "message": "Structured read model is unavailable"
  }
}
```

完整异常只进入内部 logger（日志记录器），不得把数据库路径、Windows 用户目录或 SQLite 原文返回给 HTTP Client（HTTP 客户端）。

## 7. URL（统一资源定位符）脱敏合同

`src/sources/service.py::_safe_reference()` 对 HTTP/HTTPS URL 执行：

- 保留 scheme（协议）、host（主机）、port（端口）、安全 path（路径）。
- 删除 username/password（用户名和密码）。
- 删除 fragment（片段）。
- 删除以下敏感 query parameter（查询参数）：

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

- 非敏感查询参数可保留。

示例：

```text
输入:
https://user:pass@example.com/file?id=123&token=secret#private

输出:
https://example.com/file?id=123
```

## 8. 测试合同

单一实现检查：

```python
from src.sources import SourceReadModel as A
from src.sources.read_model import SourceReadModel as B
assert A is B

from src.gateway import MemoryInspectorFacade as C
from src.gateway.memory_inspector import MemoryInspectorFacade as D
assert C is D
```

同时检查三个平行包装文件不存在，并确认 `create_control_app` 直接定义于 `src.control.api`，不依赖导入顺序或 Monkey Patch。

## 9. 集中测试命令

重点测试：

```powershell
python -m pytest `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

直接相关 Regression Test（回归测试）：

```powershell
python -m pytest `
  tests/test_memory_retrieval.py `
  tests/test_permanent_memory_gateway.py `
  tests/test_workspace_contract.py `
  tests/test_control_api.py `
  -v --tb=short
```

当前开发对话无法取得完整仓库运行环境，pytest 尚未执行，因此状态保持 `IMPLEMENTED_NOT_TESTED`。

## 10. 禁止范围

```text
不创建新分支
不开始 P2-03B
不开发或修改 Tauri
不运行完整 pytest
不运行 npm
不运行 Ollama 或真实 Qdrant 验收
不重复 P2-01/P2-02 验收
不调用本机 Codex
不合并正式分支
不 force push
```

## 11. 下一阶段

当前下一步仍是先完成 P2-03 集中测试和代码审查。

通过后进入：

```text
P2-03B Structured Ingestion Wiring（结构化采集接线）
```

目标是把 ChatGPT Adapter（ChatGPT 适配器）等采集结果显式、幂等地写入 `SourceReadModel`。

正式顺序：

```text
P2-03 集中测试与审查
-> P2-03B Structured Ingestion Wiring
-> P2-04 Memory Inspector
```
