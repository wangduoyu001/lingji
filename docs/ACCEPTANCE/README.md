# LingJi 验收权威入口

> 本目录是灵机所有开发、优化、修复和发布的统一验收权威。
>
> Codex 拉取仓库后，先读根目录 `AGENTS.md`，再读本文件和 `CODEX_ACCEPTANCE_INSTRUCTIONS.md`。不得继续使用聊天记录里的旧验收指令。

## 1. 权威文件

| 文件 | 唯一职责 |
|---|---|
| `README.md` | 验收治理、更新规则和读取顺序 |
| `CODEX_ACCEPTANCE_INSTRUCTIONS.md` | Codex 可直接执行的通用真机验收指令 |
| `CHANGE_ACCEPTANCE_LOG.md` | 每次代码变更对应的新增、删除和回归验收项 |
| `REPORT_TEMPLATE.md` | 最终验收报告固定结构 |

历史实施报告放在 `docs/TEST_REPORTS/`，只能作为证据，不能覆盖本目录的当前规则。

## 2. 每次开发的强制流程

```text
理解需求和现有代码
→ 确定受影响模块和风险
→ 在开发前定义验收标准
→ 修改代码和测试
→ 同步更新 docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
→ 必要时更新 CODEX_ACCEPTANCE_INSTRUCTIONS.md
→ 运行 focused 验证
→ 最终树运行 full 或 release
→ 真机验收
→ 提交最终报告
```

任何产品代码、运行时、Desktop、Sidecar、连接器、数据链路、脚本、依赖或发布流程发生变化，都必须在同一个 PR 中同步更新 `docs/ACCEPTANCE/`。

不得以“只是小优化”“测试已经覆盖”“以后再补”为理由跳过。人类对“以后再补”的执行率已经经过长期实验，结果并不神秘。

## 3. 变更时必须更新什么

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

## 4. 每条验收要求的最低信息

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

## 5. 环境清理和磁盘规则

统一使用：

```text
清理旧验收目录
→ 关闭旧 LingJi 进程
→ 释放 8766 / 8767
→ 直接覆盖安装新版本
→ 验收
→ 提交报告
→ 删除临时安装包、日志、截图、fixture 和配置临时副本
```

默认不卸载旧版，不删除主人正式数据，不长期保留重复 ZIP、安装包、日志、截图或配置备份。

允许保留：

- 最终 Markdown 验收报告；
- 脱敏公开证据摘要；
- 哈希清单；
- 报告 Commit；
- 主人明确要求保留的失败证据。

禁止删除：

- Production DataRoot；
- 主人正式 Acceptance 数据；
- Obsidian Vault；
- 正式记忆；
- 用户自己的 Codex、Claude、WorkBuddy 配置。

## 6. 自动验收与主人验收边界

Codex 可以自动完成：

- Git、Commit、Artifact 和 SHA256 核验；
- 单元、Smoke、构建和发布合同测试；
- 进程、端口、文件、配置差异和 API 检查；
- MCP 工具调用；
- 导入、队列、候选和审计链检查；
- 报告和脱敏证据生成。

必须由主人最终确认：

- 是否出现 PowerShell、CMD 或黑窗；
- 第一次打开是否知道下一步；
- 页面是否能看懂；
- 真实客户端 GUI 的连接结果；
- Windows 重启后的主观窗口行为；
- 任何无法被自动证据可靠证明的 UI 体验。

Codex 只能记录主人结论，不能替主人声称“肉眼已确认”。

## 7. 合并边界

以下条件全部满足前不得合并产品 PR：

- 精确产品 Commit 的 CI 通过；
- 精确 Artifact 身份和哈希通过；
- 自动验收通过；
- 必须的真机验收通过；
- 主人观察项已确认；
- 最终报告已提交；
- `docs/ACCEPTANCE/` 已与本次代码同步；
- 没有未披露的 P0/P1 阻塞缺陷。

验收报告必须与被测产品 Commit 分离提交，避免为了补报告移动产品 Head，导致安装包和代码身份再次错位。