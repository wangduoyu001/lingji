# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。只有 `status: ACTIVE` 才允许执行真机任务。

## 1. 当前任务

```yaml
task_id: NONE
status: IDLE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
development_pr: 105
development_branch: fix/pr88-owner-fact-chain-v5
implementation_sha: 79955a09f42b7eb525fff1f11c454c373df8aa6c
self_review: PASS_FOR_M5_PREPARATION
local_execution_allowed: false
```

## 2. 为什么当前必须 IDLE

PR #105 已完成 Owner Fact Chain V5 代码、自审和开发分支自动前置门禁，但新的 M5 产品身份尚未锁定。

在以下条件全部成立前，本文件不得改为 ACTIVE：

```text
PR #105 squash merge → feature/owner-autopilot-ui-codexpp
→ 得到新的 product exact SHA
→ tests PASS
→ P0 Windows Gate PASS
→ Windows Desktop Release Baseline PASS
→ macOS Desktop Gate PASS
→ acceptance-doc-sync PASS
→ local-execution-handoff PASS
→ Mac/Windows Artifact 同一 product SHA
→ Artifact 身份/架构/哈希核对完成
```

因此旧 PR60、旧 PR88 V4、旧 M5 任务和历史 Artifact 均不是当前可执行任务。

## 3. 当前禁止使用的历史任务/Artifact

以下只保留为历史证据，禁止执行或重试：

```text
PR60-MEMORY-QUALITY-TRIAL-F0956F67
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

## 4. 下一次激活时必须写入

新的 ACTIVE M5 任务至少必须固定：

```text
task_id
product_commit
macOS artifact run/id/name/hash
Windows artifact run/id/name/hash
exact architecture
Acceptance data root
report branch/path
cleanup contract
10 秒主人体验检查
Window Recovery 菜单/快捷键/Dock Reopen 三路径
Production pollution=0
```

## 5. 当前主人动作

```text
NONE
```

当前阶段不要求主人下载、安装、运行旧包或执行任何命令。

## 6. 相关权威

```text
docs/PROJECT_STATUS.md
docs/PROJECT_PROGRESS.md
docs/TEST_REPORTS/PR88_OWNER_FACT_CHAIN_V5_IMPLEMENTATION.md
docs/TEST_REPORTS/OWNER_WORKBENCH_10_SECOND_EXPERIENCE_CHECK.md
docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
```
