# UNIFIED_MEMORY_EXECUTION_STATUS.md — 统一记忆系统实时执行状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Development Branch（开发分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `d17d0bbca3d079c763b584df87578a5a8d312953`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: ACTIVE EXECUTION TRACKER（生效中的执行状态表）

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
| P2-03B | Structured Ingestion Wiring（结构化采集接线） | `BLOCKED_BY_P2_03_REVIEW` | 等待 P2-03 集中测试与审查 |
| P2-04 | Memory Inspector（记忆检查器） | `BLOCKED_BY_P2_03B` | 不得提前开始 |
| P2-05 | Startup Contract/Test Quality（启动合同与测试质量） | `DEFERRED` | 后续集中回归 |
| P2-06 | Production bge-m3 Switch（生产模型切换） | `DEFERRED` | 等待质量对比和受控切换 |

## 3. P2-03 单一正式实现

仓库当前只保留以下正式入口：

```text
src/sources/read_model.py::SourceReadModel
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

Package Export（包导出）直接引用同一类对象。

已删除平行包装层：

```text
src/sources/read_model_contract.py
src/gateway/memory_inspector_contract.py
src/control/api_contract.py
```

`src/control/__init__.py` 不再通过 import side effect（导入副作用）或 Monkey Patch（猴子补丁）修改 API Factory（接口工厂）。

## 4. P2-03 已实现合同

- Source/Conversation/Message（来源、对话、消息）派生 Schema（数据库结构）。
- 稳定 ID 与 Idempotent Upsert（幂等更新或插入）。
- 分页、稳定时间排序、来源/项目/关键词筛选。
- Message→Memory、Memory→Chunk、Chunk→Vector 只读关联。
- Privacy Filter（隐私过滤）与 Agent Scope（智能体范围）。
- Workspace（工作区）隔离和 8766 Token Authentication（令牌认证）。
- 只读 `/api/memory/inspector/*` GET 路由。
- `privacy_inherited`、`projects_inherited`、`agent_scope_inherited`。
- Source→Conversation 与 Conversation→Message 继承同步。
- 显式子级权限覆盖保护。
- Schema Version（数据库结构版本）不兼容时拒绝初始化且不降级。
- `rebuild_required` true/false/null 三态。
- Inspector 503 稳定错误和本机路径脱敏。
- HTTP/HTTPS URL（统一资源定位符）用户名、密码、敏感查询参数和 fragment（片段）脱敏。
- 单一类对象与包装文件不存在测试。

## 5. 当前测试状态

已执行辅助检查：

```text
Python py_compile（静态编译）       PASS
临时 SQLite 继承同步冒烟            PASS
schema_version=2 拒绝且不降级       PASS
URL 示例脱敏                         PASS
平行包装引用静态扫描                 PASS
```

尚未执行指定 pytest：

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

不得把辅助检查、代码提交或没有 CI 红灯解释为重点测试通过。

## 6. 集中测试门槛

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

两组全部通过后才允许更新为：

```text
IMPLEMENTED_FOCUSED_TESTED
NOT_MERGED_AWAITING_REVIEW
```

## 7. 禁止范围

```text
不创建新分支
不开始 P2-03B
不修改 Tauri
不运行完整 pytest
不运行 npm
不运行 Ollama 或真实 Qdrant
不重复 P2-01/P2-02 验收
不调用本机 Codex
不合并正式分支
不 force push
```

## 8. 下一开发顺序

```text
P2-03 集中 pytest 与代码审查
-> P2-03B Structured Ingestion Wiring
-> P2-04 Memory Inspector
-> 集中 Regression Test 与 Startup Contract（启动合同）修复
-> Production bge-m3 candidate Collection（生产候选向量集合）与受控切换
```

P2-03B 的目标是把 ChatGPT Adapter（ChatGPT 适配器）等采集结果显式、幂等地写入 `SourceReadModel`，使查询拥有真实派生数据。
