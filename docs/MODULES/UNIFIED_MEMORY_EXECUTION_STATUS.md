# UNIFIED_MEMORY_EXECUTION_STATUS.md — 统一记忆系统实时执行状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Development Branch（开发分支）: `work/p2-03-structured-read-model`  
> Implementation Commit（实现提交）: `0ce11ab56630d0d31c4828a0d63f0ea6e875729f`  
> Status（状态）: ACTIVE EXECUTION TRACKER

## 1. 权威顺序

```text
真实代码
-> 最新测试报告
-> PROJECT_STATUS.md
-> 本执行状态表
-> Roadmap 原始规划
```

## 2. 阶段状态

| 阶段 | 任务 | 状态 | 证据 |
|---|---|---|---|
| P0-02 | Port Contract | `MERGED_AND_VALIDATED` | P0-02 报告 |
| P0-03 | Workspace Contract | `MERGED_AND_VALIDATED` | P0-03 报告 |
| P1-01 ~ P1-05 | Unified Semantic Memory | `MERGED_AND_VALIDATED` | P1-05 本机验收 |
| P2-01 | Vector Center | `MERGED_AND_VALIDATED` | P2-01 报告 |
| P2-02 | Collection Migration | `MERGED_AND_VALIDATED` | P2-02 报告 |
| P2-03 | Structured Read Model | `IMPLEMENTED_NOT_TESTED` | `P2_03_STRUCTURED_READ_MODEL_TEST_REPORT.md` |
| P2-03B | Structured Ingestion Wiring | `BLOCKED_BY_P2_03_REVIEW` | 等待 P2-03 重点测试与审查 |
| P2-04 | Memory Inspector | `BLOCKED_BY_P2_03B` | 不得提前开始 |
| P2-05 | Startup Contract/Test Quality | `DEFERRED` | 后续集中回归 |
| P2-06 | Production bge-m3 Switch | `DEFERRED` | 等待质量对比与受控切换 |

## 3. P2-03 当前实现

已实现：

- Source/Conversation/Message 派生 Schema。
- 稳定 ID 与幂等 Upsert。
- 分页、时间排序、来源/项目/关键词筛选。
- Message→Memory、Memory→Chunk、Chunk→Vector 只读关联。
- Owner/Agent Privacy 与 Agent Scope 过滤。
- Production/Acceptance Workspace 隔离。
- 8766 Token Authentication。
- 只读 Inspector API。
- 权限 inherited 标记与父子同步。
- `rebuild_required` true/false/null 三态。
- 503 稳定错误与本机路径脱敏。
- 未知 Schema Version 拒绝初始化且不降级。

## 4. P2-03 当前限制

- 指定 pytest 尚未执行。
- 当前环境无法解析 `github.com`，不能获得完整远程仓库运行环境。
- 没有自动把 ChatGPT Adapter 结构化结果写入 Read Model。
- 生产 Source/Conversation/Message 派生数据仍为空或依赖显式写入。
- 本分支不得合并。

当前准确状态：

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_REVIEW
```

## 5. 禁止范围

```text
不开发 Tauri
不开始 P2-04
不运行完整 pytest
不运行 npm
不运行 Ollama/Qdrant 真实验收
不重复 P2-01/P2-02 验收
不调用本机 Codex
不合并正式分支
不 force push
```

## 6. 下一开发顺序

```text
P2-03 重点 pytest 与直接相关回归
-> P2-03 代码审查
-> P2-03B Structured Ingestion Wiring
-> P2-04 Memory Inspector
-> 集中 Regression Test 与 Startup Contract 修复
-> Production bge-m3 candidate 与受控切换
```

P2-03B 目标：把 ChatGPT Adapter 等采集结果显式、幂等地写入 `SourceReadModel`，让 Source、Conversation 和 Message 查询拥有真实派生数据。
