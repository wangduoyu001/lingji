# UNIFIED_MEMORY_EXECUTION_STATUS.md — 统一记忆系统实时执行状态

> Updated（更新时间）: 2026-07-20  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Validated Code Commit（已验证代码提交）: `8a4860553edfbb698665c7dcb1f8bfaf3f556eba`  
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
| P2-03 | Structured Read Model（结构化读取模型） | `NEXT` | 待开发 |
| P2-04 | Memory Inspector（记忆检查器） | `BLOCKED_BY_P2_03` | 等待稳定读取合同 |
| P2-05 | Startup Contract/Test Quality（启动合同与测试质量） | `DEFERRED` | 下次集中回归处理 |
| P2-06 | Production bge-m3 Switch（生产模型切换） | `DEFERRED` | 等待检索质量对比和原子切换 |

## 3. 当前任务 P2-03

P2-03 目标：实现可重建、只读、Workspace 隔离的 Structured Read Model（结构化读取模型），供后续 Memory Inspector 使用。

目标实体：

```text
Source（来源）
Conversation（对话）
Message（消息）
Memory（记忆）
Chunk（文本分块）
Vector Linkage（向量关联）
```

必须先分析真实代码和数据，不得基于旧规划直接假设表结构。

最低能力：

- 列表和详情读取
- 分页
- 时间排序
- 来源筛选
- 项目筛选
- 关键词搜索
- Conversation/Message 关联
- Message/Memory 关联
- Memory/Chunk 关联
- Chunk/Vector 状态关联
- Privacy Filter（隐私过滤）
- Production/Acceptance Workspace 隔离
- 8766 Token Authentication（令牌认证）

## 4. P2-03 范围边界

本阶段不开发：

- Tauri Memory Inspector 页面
- 生产 `bge-m3` Collection
- 正式模型切换
- 历史分支删除
- 依赖管理重构
- 自动记忆蒸馏
- 自动修改 Core Memory

## 5. 完成条件

P2-03 完成必须包含：

```text
真实代码路径分析
数据权威说明
Read Model schema（读取模型结构）
Service/Repository 读取层
8766 只读 API
分页与筛选合同
隐私和 Workspace 测试
重点单元测试
API Integration Test（接口集成测试）
Markdown 测试报告
PROJECT_STATUS 更新
CHANGELOG 更新（合并正式分支后）
```

## 6. 后续顺序

```text
P2-03 Structured Read Model
-> P2-04 Memory Inspector
-> 集中 Regression Test（回归测试）与 Startup Contract 修复
-> Production bge-m3 candidate Collection（生产候选向量集合）
-> Retrieval Quality A/B Test（检索质量对比测试）
-> Controlled Activation（受控激活）
```
