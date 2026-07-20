# DOCUMENTATION_MAINTENANCE.md — 文档实时维护合同

> Updated（更新时间）: 2026-07-20  
> Applies to（适用范围）: `feature/second-brain-memory` 及其后续开发分支  
> Status（状态）: ACTIVE（生效中）

## 1. 目标

LingJi 的文档必须跟随真实代码、真实测试和真实合并状态更新。

Documentation drift（文档漂移：文档描述落后于代码真实状态）不得作为正常现象长期存在。

任何 AI Agent（AI 智能体）、Codex 或人工开发任务，都不能只提交代码而不更新相关文档。

## 2. 文档权威顺序

当多个文档出现冲突时，按以下顺序判断：

1. `docs/PROJECT_STATUS.md`
   - Current State（当前状态）的唯一权威入口。
   - 只记录已经确认的实现、测试、合并和阻塞状态。

2. `docs/ARCHITECTURE.md` 与模块架构文档
   - Architecture Contract（架构合同：长期设计边界和数据权威）。
   - 不用于记录短期测试数字。

3. `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`
   - Roadmap（开发路线图：后续任务顺序和阶段目标）。

4. `docs/TEST_REPORTS/`
   - Test Evidence（测试证据：命令、环境、结果和限制）。
   - 报告必须区分“已执行”和“计划执行”。

5. `docs/CHANGELOG.md`
   - Changelog（变更日志：按时间记录已经进入正式分支的变化）。

6. Milestone Report（里程碑报告）
   - 例如 `docs/FINAL_P2_MERGE_REPORT.md`。
   - 用于冻结某一阶段的交付快照，不代替持续更新的项目状态。

## 3. 强制更新时间点

### 3.1 功能实现完成

必须更新：

- 对应模块计划或实现报告
- Code Map（代码地图），仅当入口路径发生变化时
- 对应测试报告中的“实现完成、待验证”状态

### 3.2 本机或真实环境验证完成

必须在同一任务中更新：

- 对应测试报告
- `docs/PROJECT_STATUS.md`
- 验证 Commit（提交）
- 测试命令、通过数、失败数、跳过数
- 未执行项目和已知限制

不得把未执行测试写成 PASS（通过）。

### 3.3 合并正式分支完成

必须在同一任务中更新：

- `docs/PROJECT_STATUS.md`
- `docs/CHANGELOG.md`
- 对应报告中的 Branch（分支）、HEAD（最新提交）和 Merge State（合并状态）
- 下一开发任务

如果代码已经合并但文档尚未更新，该任务仍视为未完整交付。

### 3.4 路线或优先级变化

必须更新：

- `docs/PROJECT_STATUS.md` 的 Next Development Sequence（下一开发顺序）
- 对应 Roadmap（路线图）
- 被推迟任务的原因和恢复条件

## 4. 标准状态词

所有实现和测试状态必须使用以下明确状态，禁止使用模糊的“基本完成”“应该可以”。

```text
PLANNED
= 已规划，未实现

IMPLEMENTED_NOT_TESTED
= 已实现，尚未执行要求的测试

IMPLEMENTED_FOCUSED_TESTED
= 已实现，相关重点测试已通过

IMPLEMENTED_LOCALLY_VALIDATED
= 已在真实本机环境验证

MERGED_AND_VALIDATED
= 已验证并合并正式分支

BLOCKED
= 被明确问题阻塞

DEPRECATED_COMPATIBILITY_ONLY
= 已弃用，仅兼容用途
```

## 5. 文档头部标准

所有 Current State（当前状态）、Test Report（测试报告）和 Implementation Plan（实施计划）应包含：

```text
Updated（更新时间）
Branch（分支）
Verified Commit（已验证提交）
Status（状态）
Evidence（证据来源）
```

若报告不是基于当前正式 HEAD，必须明确写出验证基线，不得让读者自行猜测。

## 6. 英文术语规则

项目文档中 English Term（英文术语）首次出现时，必须带 Chinese Explanation（中文解释）。

推荐格式：

```text
Read Model（读取模型：面向查询整理的可重建数据结构）
Workspace（工作区：隔离生产和验收数据的运行环境）
Smoke Test（冒烟测试：快速确认核心功能能否运行）
```

代码标识符、命令、路径、类名和函数名保持原始英文，不强制翻译。

同一文档中术语首次解释后，后文可以直接使用英文名称。

## 7. 测试数字规则

每次记录测试结果必须同时写出：

- 测试范围
- 执行命令或脚本
- passed（通过）
- failed（失败）
- skipped（跳过）
- xfailed（预期失败，如存在）
- 执行日期
- 验证 Commit

不同测试范围的数字不得直接比较。

如果总测试数发生明显变化，必须解释原因；无法解释时标记为 `UNRECONCILED_TEST_COUNT_DELTA`（测试数量差异未核对），不得假装没有问题。

## 8. 低积分执行规则

Documentation-only Change（纯文档修改）默认通过 GitHub 直接完成，不调用本机 Codex。

只有以下情况才需要 Codex：

- 真实 Windows/Tauri（桌面运行框架）验证
- Ollama/Qdrant（本地模型与向量数据库）验证
- 本地文件系统行为
- 完整依赖安装
- 本机测试和构建

已经通过且代码未受相关影响的测试，不重复执行。

## 9. 多对话交接规则

新对话开始开发前必须读取：

1. `AGENTS.md`
2. `docs/AI_CONTEXT.md`
3. `docs/DEVELOPMENT_RULES.md`
4. `docs/AI_COLLABORATION_RULES.md`
5. `docs/DOCUMENTATION_MAINTENANCE.md`
6. `docs/PROJECT_STATUS.md`
7. 与当前任务直接相关的模块计划和测试报告

新对话必须先确认 Remote HEAD（远程最新提交），但不得无意义地反复拉取和重复验证。

## 10. 任务完成门槛

任务只有同时满足以下条件才算完成：

```text
实现已提交
相关测试状态已记录
对应报告已更新
PROJECT_STATUS 已更新
CHANGELOG 已更新（正式分支变化时）
下一步已记录
远程分支状态已确认
```

少一项都属于 Delivery Incomplete（交付不完整）。
