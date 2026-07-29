# LingJi 验收权威入口

> 本目录是灵机所有开发、优化、修复、发布和本机执行的统一验收权威。
>
> Codex 拉取仓库后，先读根目录 `AGENTS.md`，再读本文件。聊天记录不得作为本机任务或验收结果的权威来源。

## 1. 权威文件

| 文件 | 唯一职责 |
|---|---|
| `README.md` | 验收治理、更新规则和读取顺序 |
| `LOCAL_EXECUTION_TASK.md` | ChatGPT / 主开发代理下达给本机 Codex 的唯一当前任务单 |
| `LOCAL_EXECUTION_RESULT.md` | Codex 提交给 ChatGPT / 主开发代理的唯一固定结果回执 |
| `CODEX_ACCEPTANCE_INSTRUCTIONS.md` | Codex 可直接执行的通用真机验收基线 |
| `CHANGE_ACCEPTANCE_LOG.md` | 每次代码变更对应的新增、删除和回归验收项 |
| `REPORT_TEMPLATE.md` | 最终验收报告固定结构 |

历史实施报告放在 `docs/TEST_REPORTS/`，只能作为证据，不能覆盖本目录的当前规则。

## 2. 人与代理的职责

用户只负责：

```text
告诉 Codex：去看仓库任务单干活
或
告诉 ChatGPT：Codex 已经完成
```

用户不负责：

- 复制长指令；
- 理解 Git 分支、Commit、push 或 Artifact；
- 选择报告路径；
- 上传报告；
- 检查远程分支；
- 清理本机验收垃圾。

ChatGPT / 主开发代理负责更新 `LOCAL_EXECUTION_TASK.md`，写清唯一任务身份、被测 Commit、Artifact、执行范围、报告分支、报告路径和清理规则。

Codex 负责读取任务单、执行、生成报告、提交远程、重新读取远程结果、更新 `LOCAL_EXECUTION_RESULT.md`、清理本机垃圾，然后才允许向用户回复完成。

## 3. 本机任务读取顺序

Codex 收到“去看任务单干活”后固定读取：

```text
AGENTS.md
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
→ docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
→ docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前任务条目
→ docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

只允许执行 `LOCAL_EXECUTION_TASK.md` 中：

```yaml
status: ACTIVE
```

的任务。不得根据聊天旧内容、本机残留目录、旧报告或自己的猜测补全任务。

## 4. 每次开发的强制流程

```text
理解需求和现有代码
→ 确定受影响模块和风险
→ 开发前定义验收标准
→ 修改代码和测试
→ 同步 CHANGE_ACCEPTANCE_LOG.md
→ 必要时更新 CODEX_ACCEPTANCE_INSTRUCTIONS.md
→ 需要本机执行时更新 LOCAL_EXECUTION_TASK.md
→ 运行 focused 验证
→ 最终树运行 full 或 release
→ Codex 按任务单真机执行
→ Codex 提交报告和结果回执
→ ChatGPT 读取远程结果
→ 决定修复、继续或合并
```

任何产品代码、运行时、Desktop、Sidecar、连接器、数据链路、脚本、依赖或发布流程发生变化，都必须在同一个 PR 中同步更新 `docs/ACCEPTANCE/`。

不得以“只是小优化”“测试已经覆盖”“以后再补”为理由跳过。人类对“以后再补”的执行率已经经过长期实验，结果并不神秘。

## 5. 变更时必须更新什么

每次代码变更至少更新：

```text
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
```

以下情况还必须更新 `CODEX_ACCEPTANCE_INSTRUCTIONS.md`：

- 用户操作流程变化；
- 页面、按钮、路由或状态文案变化；
- Runtime、端口、进程、安装、升级或重启行为变化；
- 数据路径、Workspace、Vault、数据库、索引或备份行为变化；
- MCP、API、认证、Token 或连接器变化；
- 导入、队列、幂等、审核或永久记忆边界变化；
- 新增外部客户端、模型、插件或依赖；
- 新增必须由主人肉眼确认的行为；
- 新增安全、隐私或回滚风险；
- 发布 Artifact、安装器或构建合同变化。

需要本机执行时还必须更新：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

任务完成时 Codex 必须在报告分支更新：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

## 6. 每条验收要求的最低信息

`CHANGE_ACCEPTANCE_LOG.md` 中每次变更必须记录：

```text
变更标识
影响范围
风险
新增或修改的验收项
自动测试
真机测试
主人肉眼确认
清理与回滚
不在范围
最终报告路径
```

验收结论只允许：

```text
PASS
FAIL
BLOCKED
NOT_TESTED
SKIPPED_NOT_INSTALLED
```

禁止写“应该可以”“大致正常”“代码上没问题”。

## 7. 开始前清理硬门禁

每次本机任务开始前必须：

```text
拉取最新任务单
→ 确认 task_id 和产品身份
→ 删除上一轮临时验收目录
→ 删除重复 Artifact、解压内容、普通成功日志、截图、fixture、checkpoint 和临时配置副本
→ 关闭 LingJi 残留进程
→ 释放 8766 / 8767
→ 确认没有孤儿 MCP
→ 才能开始测试
```

默认直接覆盖安装，不卸载旧版，不删除主人正式数据。

禁止删除：

- Production DataRoot；
- 主人正式 Acceptance 数据；
- Obsidian Vault；
- 正式记忆；
- 用户自己的 Codex、Claude、WorkBuddy 配置。

开始前清理未通过时，结果必须为 `BLOCKED_PRE_CLEANUP`，不得继续验收。

## 8. 报告提交与远程确认硬门禁

执行 `git push` 不代表提交成功。Codex 必须从 GitHub 远程重新读取并确认：

- 报告分支存在；
- 报告内容 Commit 存在；
- 最终报告可读取；
- 公开证据可读取；
- `LOCAL_EXECUTION_RESULT.md` 可读取；
- 产品 PR 评论包含 task_id、产品 Commit、报告分支、报告 Commit、报告路径和结论。

任何一项远程复读失败，必须写：

```text
BLOCKED_REPORT_NOT_VISIBLE_ON_GITHUB
```

不得对用户声称“已上传”或“已完成”。用户不需要也不应该参与排查 Git 提交。

## 9. 完成后清理硬门禁

远程报告第一次确认后，Codex 必须清理：

- 本轮 Artifact 和重复安装包；
- 临时解压目录；
- fixture 和 checkpoint；
- 临时配置副本；
- 普通成功日志和截图；
- 临时 worktree；
- 带本轮前缀的 Acceptance 测试数据；
- 本轮临时验收根目录。

清理后更新 `LOCAL_EXECUTION_RESULT.md`，再次提交、push 并从远程复读。

只有以下字段全部成立才算完成：

```text
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: true
```

结束清理未通过时，结果必须为 `BLOCKED_POST_CLEANUP`。

允许保留：

- 最终 Markdown 验收报告；
- 脱敏公开证据摘要；
- 哈希清单；
- 远程报告 Commit；
- 主人明确要求保留的失败证据。

## 10. 自动验收与主人验收边界

Codex 可以自动完成：

- Git、Commit、Artifact 和 SHA256 核验；
- 单元、Smoke、构建和发布合同测试；
- 进程、端口、文件、配置差异和 API 检查；
- MCP 工具调用；
- 导入、队列、候选和审计链检查；
- 报告和脱敏证据生成；
- Git 提交、push、远程复读和本地清理。

必须由主人最终确认：

- 是否出现 PowerShell、CMD 或黑窗；
- 第一次打开是否知道下一步；
- 页面是否能看懂；
- 真实客户端 GUI 的连接结果；
- Windows 重启后的主观窗口行为；
- 任何无法被自动证据可靠证明的 UI 体验。

Codex 只能记录主人结论，不能替主人声称“肉眼已确认”。

## 11. 自动门禁

仓库必须运行：

```powershell
python scripts/check_acceptance_sync.py
python scripts/check_local_execution_handoff.py
python -m pytest -q tests/test_acceptance_sync.py
python -m pytest -q tests/test_local_execution_handoff.py
```

`local-execution-handoff` CI 在 `acceptance/**` 报告分支上要求最终回执为 `COMPLETED`。缺少清理、远程确认或报告 Commit 时必须失败。

## 12. 合并边界

以下条件全部满足前不得合并产品 PR：

- 精确产品 Commit 的 CI 通过；
- 精确 Artifact 身份和哈希通过；
- 自动验收通过；
- 必须的真机验收通过；
- 主人观察项已确认；
- 最终报告已提交并远程复读；
- 结果回执为 `COMPLETED`；
- 开始前和结束后清理均通过；
- `docs/ACCEPTANCE/` 已与本次代码同步；
- 没有未披露的 P0/P1 阻塞缺陷。

验收报告必须与被测产品 Commit 分离提交，避免为了补报告移动产品 Head，导致安装包和代码身份再次错位。