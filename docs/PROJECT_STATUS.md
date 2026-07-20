# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Development Branch（开发分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `d17d0bbca3d079c763b584df87578a5a8d312953`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: P2-03 `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_REVIEW`

## 1. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）
```

本轮没有创建新分支，没有修改 Tauri，没有开始 P2-03B，也没有合并正式分支。

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

Production bge-m3 Switch（生产 bge-m3 切换）和生产 Collection（向量集合）重建仍未执行。

## 4. P2-03 当前实现

P2-03 已在独立开发分支实现：

- Source/Conversation/Message（来源、对话、消息）派生表。
- Message→Memory、Memory→Chunk、Chunk→Vector 只读关系。
- Stable ID（稳定标识符）与 Idempotent Upsert（幂等更新或插入）。
- 分页、稳定排序、来源/项目/关键词筛选。
- Privacy Filter（隐私过滤）与 Agent Scope（智能体范围）。
- Workspace（工作区）隔离与 8766 Token Authentication（令牌认证）。
- 只读 `/api/memory/inspector/*` GET 路由。

## 5. 单一正式实现收口

当前唯一正式入口：

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

Package Export（包导出）直接引用正式类，`src/control/__init__.py` 不再通过 import side effect（导入副作用）或 Monkey Patch（猴子补丁）替换 `create_control_app()`。

## 6. 本轮合同修复

### 6.1 权限继承

正式 Schema（数据库结构）包含：

```text
privacy_inherited
projects_inherited
agent_scope_inherited
```

Source 更新只同步继承型 Conversation；Conversation 更新只同步继承型 Message；显式子级权限不被父级覆盖。

### 6.2 Schema Version

```text
不存在 schema_version -> 写入 1
schema_version == 1   -> 正常
schema_version != 1   -> SourceReadModelError
```

未知或更高版本不得被自动降级。

### 6.3 Vector Tri-state（向量三态）

```text
True  -> true
False -> false
None  -> null
```

Memory Vector（记忆向量）顶层和每个 Chunk（文本分块）保持一致。

### 6.4 503 脱敏

Inspector（检查器）故障对外固定返回：

```text
READ_MODEL_UNAVAILABLE
Structured read model is unavailable
```

SQLite 原文、数据库路径和用户目录不进入 HTTP Response（HTTP 响应）。

### 6.5 URL 脱敏

HTTP/HTTPS URL（统一资源定位符）现在会：

- 删除 username/password（用户名和密码）。
- 删除 fragment（片段）。
- 删除 token、access_token、api_key、apikey、key、secret、signature、sig、credential、authorization、session、cookie 等敏感 query parameter（查询参数）。
- 保留协议、主机、端口、安全路径和非敏感参数。

## 7. 当前测试状态

已编写或更新：

```text
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

已执行辅助检查：

```text
Python py_compile（静态编译）       PASS
临时 SQLite 继承同步冒烟            PASS
schema_version=2 拒绝且不降级       PASS
URL 示例脱敏                         PASS
平行包装引用静态扫描                 PASS
```

两组指定 pytest 尚未执行：

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

当前准确状态：

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_REVIEW
```

不得描述为测试通过，不得合并正式分支。

## 8. 本轮未执行

```text
完整 pytest
npm
Tauri
Ollama
真实 Qdrant
P2-01 重复验收
P2-02 重复验收
本机 Codex
```

## 9. 数据安全

```text
读取生产聊天正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
切换生产模型: NO
创建或删除生产 Collection: NO
修改 Tauri: NO
```

## 10. 集中测试门槛

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

两组全部通过后才更新为：

```text
IMPLEMENTED_FOCUSED_TESTED
NOT_MERGED_AWAITING_REVIEW
```

## 11. 下一阶段

下一步不是 P2-04。

正式顺序：

```text
P2-03 集中 pytest 与代码审查
-> P2-03B Structured Ingestion Wiring（结构化采集接线）
-> P2-04 Memory Inspector（记忆检查器）
-> 集中 Regression Test 与 Startup Contract（启动合同）修复
-> Production bge-m3 candidate Collection（生产候选向量集合）与受控切换
```

P2-03B 目标是把 ChatGPT Adapter（ChatGPT 适配器）等采集结果显式、幂等地写入 `SourceReadModel`，使 Source、Conversation 和 Message 页面拥有真实派生数据。

## 12. 开发冻结规则

- 新记忆能力只进入 `src/`。
- 新采集能力只进入 `src/extraction/`。
- 正式桌面能力只进入 `desktop/lingji-control/`。
- Tauri 不得直连 8765、8767、SQLite、Qdrant 或 Ollama。
- P2-03 未完成集中测试和审查前不得合并。
- 不 force push。
