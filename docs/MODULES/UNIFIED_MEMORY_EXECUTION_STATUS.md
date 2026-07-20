# UNIFIED_MEMORY_EXECUTION_STATUS.md — 统一记忆系统实时执行状态

> Updated（更新时间）: 2026-07-20  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Verified Commit（已验证提交）: `b9950b4066fbb0b602c2ffba5109da2fa8371cf3`  
> Status（状态）: ACTIVE EXECUTION TRACKER（生效中的执行状态表）

## 1. 本文定位

`UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md` 是 Roadmap（路线图：完整任务分解和长期规划）。

本文是 Execution Tracker（执行状态表：记录哪些任务已经实现、验证、合并，以及下一任务是什么）。

当路线图中的“未开始”描述与本文冲突时：

```text
真实代码
-> 最新测试报告
-> PROJECT_STATUS.md
-> 本执行状态表
-> 原始路线图规划文字
```

## 2. 阶段状态

| 阶段 | 任务 | 状态 | 证据 |
|---|---|---|---|
| P0-02 | Port Contract（端口合同） | `MERGED_AND_VALIDATED` | `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md` |
| P0-03 | Workspace Contract（工作区合同） | `MERGED_AND_VALIDATED` | `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md` |
| P1-01 | EmbeddingProvider（向量嵌入提供器） | `MERGED_AND_VALIDATED` | P1-05 本机验收 |
| P1-02 | QdrantSemanticProvider（Qdrant 语义提供器） | `MERGED_AND_VALIDATED` | P1-05 本机验收 |
| P1-03 | MemoryIndexCoordinator（记忆索引协调器） | `MERGED_AND_VALIDATED` | P1-05 本机验收 |
| P1-04 | Runtime Wiring（运行时接线） | `MERGED_AND_VALIDATED` | P1-05 本机验收 |
| P1-05 | Memory/Vector Status（记忆与向量状态） | `MERGED_AND_VALIDATED` | `P1_05_LOCAL_ACCEPTANCE_SUMMARY.md` |
| P2-01 | Vector Center（向量中心） | `MERGED_AND_VALIDATED` | `P2_01_VECTOR_CENTER_UI_TEST_REPORT.md` |
| P2-02 | Collection Migration（向量集合迁移工具） | `MERGED_AND_VALIDATED` | `P2_02_VECTOR_COLLECTION_MIGRATION_TEST_REPORT.md` |
| P2-03 | Structured Read Model（结构化读取模型） | `IMPLEMENTED_NOT_TESTED` | `P2_03_STRUCTURED_READ_MODEL_TEST_REPORT.md` |
| P2-04 | Memory Inspector（记忆检查器） | `BLOCKED_BY_P2_03_REVIEW` | 等待重点测试、代码审查和正式合并 |
| P2-05 | Startup Contract/Test Quality（启动合同与测试质量） | `DEFERRED` | 下次集中回归处理 |
| P2-06 | Production bge-m3 Switch（生产模型切换） | `DEFERRED` | 等待检索质量对比和原子切换 |

## 3. 当前任务 P2-03

P2-03 已在独立分支实现可重建、只读、Workspace（工作区）隔离的 Structured Read Model（结构化读取模型），供后续 Memory Inspector 使用。

实现实体：

```text
Source（来源）
Conversation（对话）
Message（消息）
MessageMemoryLink（消息与记忆关联）
Memory（记忆）
Chunk（文本分块）
Vector Linkage（向量关联诊断）
```

已实现能力：

- 独立派生 Schema（数据库结构版本）
- 稳定 ID 与幂等 Upsert（更新或插入）
- 列表和详情读取
- `limit/offset` 分页
- 稳定时间排序
- 来源、项目、角色、时间和关键词筛选
- Conversation/Message 关联
- Message/Memory 关联
- Memory/Chunk 关联
- Chunk/Vector 状态关联
- Privacy Filter（隐私过滤）
- Agent Scope（智能体读取范围）
- Production/Acceptance Workspace 隔离合同
- 8766 Token Authentication（令牌认证）
- 只读 `/api/memory/inspector/*` GET 路由

## 4. P2-03 范围边界

本阶段没有开发：

- Tauri Memory Inspector 页面
- 生产 `bge-m3` Collection
- 正式模型切换
- 生产 ChatGPT 历史导入
- `second_brain.sqlite3` 自动迁移
- 历史分支删除
- 依赖管理重构
- 自动记忆蒸馏
- 自动修改 Core Memory

本阶段没有让 Local Control Process（本地控制进程）重新打开 Embedded Qdrant（嵌入式 Qdrant）。单个 Chunk 无法安全确认向量存在时，返回 `exists=null`。

## 5. 当前验证状态

已执行辅助检查：

```text
Python py_compile                    PASS
临时 SQLite 隔离冒烟                 PASS
禁止端口/Qdrant/raw vector 静态扫描 PASS
```

尚未执行：

```text
P2-03 四个重点 pytest
Memory/Gateway/Workspace/Control API 直接回归
完整 pytest
```

因此当前状态必须保持：

```text
IMPLEMENTED_NOT_TESTED
```

现有全量测试数字差异仍为：

```text
UNRECONCILED_TEST_COUNT_DELTA
```

## 6. P2-03 完成条件

已完成：

```text
真实代码路径分析
数据权威说明
Read Model schema
Service/Repository 读取层
8766 只读 API
分页与筛选合同
隐私与 Workspace 测试代码
API Integration Test 代码
Markdown 计划和测试报告
PROJECT_STATUS 更新
```

待完成：

```text
重点 pytest 执行
直接相关回归执行
代码审查
正式分支合并
CHANGELOG 更新（仅合并后）
```

## 7. 后续顺序

```text
P2-03 重点测试与代码审查
-> 合并 feature/second-brain-memory
-> P2-04 Memory Inspector
-> 集中 Regression Test（回归测试）与 Startup Contract 修复
-> Production bge-m3 candidate Collection（生产候选向量集合）
-> Retrieval Quality A/B Test（检索质量对比测试）
-> Controlled Activation（受控激活）
```
