# DOCUMENTATION_MAINTENANCE.md — 文档角色与防漂移规则

> Updated: 2026-08-25
> Status: ACTIVE ROUTING CONTRACT
> 完整开发与验收规则：`docs/DEVELOPMENT_RULES.md`、`docs/ACCEPTANCE/README.md`

本文件只定义文档如何分类和避免误导，不复制当前进度、架构、测试数字、分支状态或验收细节。

## 1. 唯一权威分工

| 事实 | 详细权威 |
|---|---|
| 当前阶段、真实进度、阻塞、下一步 | `docs/PROJECT_STATUS.md` |
| 稳定架构、数据权威、端口和长期边界 | `docs/ARCHITECTURE.md` |
| 代码入口、模块所有权、局部测试 | `docs/MODULES/CODE_MAP.md` |
| 尚未进入当前阶段的需求 | `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md` |
| 当前验收治理、任务、结果 | `docs/ACCEPTANCE/README.md` 及其列出的权威文件 |
| 用户可感知或发布相关变化 | `docs/CHANGELOG.md` |
| 特定提交和测试的历史证据 | `docs/TEST_REPORTS/` |

同一个事实只保留一个详细权威。入口文档可以链接权威，但不复制会随开发变化的清单和结论。

## 2. 文档角色

每份长期保留的文档必须能归入以下一种角色：

```text
CURRENT_AUTHORITY
= 当前状态、架构、代码导航或验收的唯一权威

SUPPORTING_GUIDE
= 稳定使用说明；冲突时服从 CURRENT_AUTHORITY

FUTURE_BACKLOG
= 尚未进入当前阶段的需求，不得直接开工

HISTORICAL_EVIDENCE
= 特定分支、提交、实现或测试快照，不代表当前状态

GENERATED_DATA
= 生成内容或业务快照，不代表工程健康度或产品阶段

MACHINE_CONFIGURATION
= 依赖、约束和锁文件，不承担开发进度说明
```

历史文件可以保留旧分支、旧测试数字和旧结论，但必须有明显角色说明，不能使用未限定的“当前”“正常”“已完成”冒充今天的状态。

## 3. 最小读取顺序

所有开发、优化、修复、发布和验收任务严格按 `AGENTS.md` 的最小读取顺序执行。不要恢复已删除的旧 AI Context、旧 Roadmap、并行计划或阶段状态文档。

历史模块记录的入口是 `docs/MODULES/README.md`；历史测试和验收记录的入口是 `docs/TEST_REPORTS/README.md`。

## 4. 更新触发条件

- 代码真实进度变化：更新 `PROJECT_STATUS.md`；代码入口或局部测试变化时同步 `CODE_MAP.md`。
- 产品代码、Runtime、UI、数据链路、脚本、依赖或发布流程变化：同一变更更新 `CHANGE_ACCEPTANCE_LOG.md`。
- 用户可感知或发布相关变化：更新 `CHANGELOG.md`。
- 测试执行：在现有权威文档或 `TEST_REPORTS` 记录命令、提交、通过/失败/跳过和限制。
- 路线改变：当前阶段只改 `PROJECT_STATUS.md`；未来需求只改 `FUTURE_DEVELOPMENT_TODO.md`。

未执行测试只能写 `NOT_RUN` 或 `IMPLEMENTED_NOT_TESTED`，不能根据测试文件存在、旧 CI 通过或子代理报告推断 PASS。

## 5. 清理规则

优先更新现有权威，删除真正重复且已失去职责的当前计划。以下内容默认保留：

- 历史测试/验收报告、失败证据、哈希和清理回执；
- 已发布实现的历史设计记录；
- 为回归和兼容承诺提供证据的旧结论；
- PEMIS opportunity 等生成业务数据。

保留不等于当前有效。历史和生成数据必须通过目录入口或文件头明确降级。

## 6. 交付检查

文档变更完成前至少检查：

```text
git diff --check
当前权威是否引用已删除文件
当前状态是否与代码和直接测试一致
验收任务/结果是否被意外改变
历史证据是否被删除或改写
本地 Markdown 相对链接是否存在
```

纯文档治理不自动触发产品安装、Artifact、full/release 或主人 UI 验收；具体范围以本次 `CHANGE_ACCEPTANCE_LOG.md` 条目为准。
