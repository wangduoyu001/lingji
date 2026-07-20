# AI_COLLABORATION_RULES.md — LingJi AI 协作规则

> Updated（更新时间）: 2026-07-20  
> Status（状态）: ACTIVE（生效中）  
> Documentation Contract（文档维护合同）: `docs/DOCUMENTATION_MAINTENANCE.md`

## 1. 目的

定义多个 AI Agent（AI 智能体）、Codex 和不同开发环境同时处理 LingJi 仓库时的协作规则。

目标：

- 避免重复开发
- 避免覆盖代码
- 避免反复拉取和重复验证
- 保证文档与真实项目状态同步
- 节省本机 Codex 积分

## 2. GitHub Remote（远程仓库）是代码权威

GitHub 远程分支是项目代码基线。

开发任务开始前必须：

1. 确认仓库名称。
2. 确认目标分支存在。
3. 确认 Remote HEAD（远程最新提交）。
4. 比较本地 HEAD 与远程 HEAD。
5. 分支状态未知时不得直接开发。

Local Worktree（本地独立工作树）只是开发环境，不是项目权威来源。

但是已经确认 Remote HEAD 且没有新提交证据时，不得无意义地反复 `fetch/pull`。

## 3. 分支同步流程

标准流程：

```text
GitHub remote（远程仓库）
  -> fetch（拉取引用）
  -> confirm branch and commit（确认分支和提交）
  -> sync local workspace（同步本地工作区）
  -> develop（开发）
  -> focused test（重点测试）
  -> update documents（更新文档）
  -> commit（提交）
  -> push（推送）
```

分支发生 Divergence（分叉）时：

- 先检查 Common Ancestor（共同祖先）
- 检查双方修改文件
- 判断是否真正冲突
- 已发布开发分支优先使用普通 Merge（合并）同步
- 未经批准不得 Force Push（强制推送）

## 4. 多 AI 并行开发

多个对话可以并行工作，但必须满足：

- File Ownership（文件所有权范围）不重叠
- API Contract（接口合同）明确
- 数据权威明确
- 分支基线明确
- 测试责任明确

接受其他对话的结果前必须检查：

- Commit 来源
- Changed Files（修改文件）
- 测试是否真实执行
- 文档是否同步
- 是否修改生产数据

不得假设其他 AI 工作区代表最新项目状态。

## 5. 任务路由与低积分模式

使用能完成任务的最简单方式。

直接通过 GitHub 完成：

- 文档修正
- Architecture Decision（架构决策）
- Code Review（代码审查）
- 小型非运行时修改
- 项目状态同步
- 变更日志维护

只有以下任务使用本机 Codex：

- 运行真实测试
- Windows/Tauri（桌面应用框架）验证
- Ollama/Qdrant（本地模型与向量数据库）验证
- 本地文件系统行为验证
- 安装完整依赖
- 调试运行中的服务

已经验证通过且相关代码没有变化时，不重复运行同一套测试。

多个待验证功能应尽量合并到一个 Codex 验收节点，而不是每个小改动都重新运行完整仓库。

## 6. 开发前阅读要求

新开发对话必须读取：

1. `AGENTS.md`
2. `docs/AI_CONTEXT.md`
3. `docs/DEVELOPMENT_RULES.md`
4. `docs/AI_COLLABORATION_RULES.md`
5. `docs/DOCUMENTATION_MAINTENANCE.md`
6. `docs/PROJECT_STATUS.md`
7. `docs/ARCHITECTURE.md`
8. 当前任务对应模块计划、Code Map（代码地图）和测试报告

当文档与代码冲突时，以真实代码和正式分支为准，并立即修正文档。

## 7. 安全合并要求

合并前必须：

1. 比较共同祖先。
2. 检查修改文件范围。
3. 检查是否存在真实冲突。
4. 运行与修改范围直接相关的测试。
5. 确认生产数据没有被意外修改。
6. 更新测试报告和项目状态。

不得闭着眼睛合并，也不得因为“没有 CI 红灯”就宣称验证通过。

CI（持续集成）未配置时，本机测试报告仍是主要证据。

## 8. 文档实时更新要求

每个重要任务在以下三个节点更新文档：

```text
实现完成
真实验证完成
合并正式分支完成
```

必须更新：

- 对应 Test Report（测试报告）
- `docs/PROJECT_STATUS.md`
- `docs/CHANGELOG.md`，仅当正式分支发生变化
- Code Map，仅当入口路径变化
- Roadmap，仅当开发顺序变化

代码已经合并但文档仍显示“开发中”，属于 Delivery Incomplete（交付不完整）。

英文术语在项目文档中首次出现时必须带中文解释；Codex 指令不强制执行该规则。

## 9. 测试报告规则

测试报告必须区分：

- 实现完成但未执行测试
- 重点测试通过
- 本机真实环境验证通过
- 已合并正式分支
- 已知限制

禁止：

- 把未运行测试写成 PASS
- 删除测试获得零失败
- 降低断言获得零失败
- 用 Skip（跳过）隐藏真实代码错误
- 把不同测试范围的数字直接比较

测试数量显著变化时必须解释原因。

## 10. 最终验收

任务完成必须同时满足：

```text
代码或文档已经提交
要求的测试状态已记录
当前分支状态已确认
对应报告已更新
PROJECT_STATUS 已更新
CHANGELOG 已更新（正式分支变化时）
下一开发步骤已记录
```

少一项都不能标记为完成。

## 11. 当前下一任务

当前正式开发顺序：

```text
P2-03 Structured Read Model（结构化读取模型）
-> P2-04 Memory Inspector（记忆检查器）
-> 集中 Regression Test（回归测试）与 Startup Contract（启动合同）修复
-> 正式 bge-m3 候选 Collection 与受控切换
```
