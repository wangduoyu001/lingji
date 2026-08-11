# LingJi macOS M5 当前真机验收任务单

> **当前状态：FAIL / CLOSED FOR THIS ARTIFACT。**
>
> 本文件仍是 M5 真机验收的固定入口，但 `171091fe...` / Artifact `9102748834` 已失败，禁止再次验收同一包。当前工作已切回开发修复，权威任务见 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`。

## 0. 失败任务身份

```yaml
status: FAILED_DO_NOT_RETRY
task_id: MACOS-M5-AUTOPILOT-PHASE4-171091FE
repository: wangduoyu001/lingji
product_commit: 171091fe764c6653cdc7325b4a1a71e0b7800822
product_branch: feature/owner-autopilot-ui-codexpp
pull_request: 88
platform: macOS Apple Silicon
target: aarch64-apple-darwin
artifact_name: lingji-macos-arm64
artifact_id: 9102748834
workflow_run_id: 31495013820
artifact_archive_sha256: 701680b5d89ef3dc1fa669afd038a13779cb755b3adc5d104df6a1fbee36e306
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46271781
dmg_sha256: 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
verdict: FAIL
retry_same_artifact: false
next_stage: DEVELOPMENT_ROOT_CAUSE_REPAIR
next_task: docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
expected_failure_report: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
expected_failure_report_branch: acceptance/macos-m5-autopilot-phase4-171091fe
```

## 1. 已确认的失败结论

主人已确认本轮 M5 复验已经结束，不是卡住，也不是等待继续。

当前三类阻断：

```text
1. 安装包身份不精确
2. 首次体验仍不清晰
3. 错误写入 ~/Documents/acceptance
```

因此：

```text
Artifact 9102748834 = REJECTED
产品 Commit 171091fe = REQUIRES_FIX
PR #88 = Draft / DO NOT MERGE
```

## 2. 现场收尾状态

主人已确认：

```text
新版本已停止
端口和后台进程已关闭
本轮测试数据已清理到废纸篓
旧的有效签名 App 已恢复到 /Applications/灵机.app
```

开发端不得要求主人再次执行这些收尾动作，也不得重新安装失败 Artifact 来“再确认一次”。

## 3. 失败报告远程状态异常

本机 Codex 声称失败报告和 PR #88 评论已推送，但 ChatGPT 于 2026-08-11 重新读取 GitHub 远程时发现：

```text
acceptance/macos-m5-autopilot-phase4-171091fe：未发现
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md：master / 产品分支未发现
GitHub acceptance refs：未发现本轮 Phase 4 分支
```

因此开发任务第一步不是猜根因，而是：

```text
读取本机失败报告
→ 核对本机 Git / reflog / 未推送提交
→ 必要时补交失败报告
→ 远程复读确认
→ 再开始开发修复
```

不得把“git push 命令执行过”当成远程报告已存在。

## 4. 禁止事项

在新的精确产品 Head 和新 Artifact 生成前：

- 禁止重新运行本任务；
- 禁止使用 Artifact `9102748834`；
- 禁止使用旧 DMG；
- 禁止把本任务状态改回 ACTIVE；
- 禁止把自动 CI PASS 当成真实 M5 PASS；
- 禁止合并 PR #88。

## 5. 下一步开发任务

固定入口：

```text
https://github.com/wangduoyu001/lingji/blob/master/docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

开发端必须关闭：

```text
M5-IDENTITY-002
M5-UX-003
M5-ISOLATION-002
```

并为三个真实失败路径新增自动回归。

## 6. 重新开放 M5 验收的条件

只有开发端全部完成以下条件，本文件才允许原地更新为新的 `status: ACTIVE`：

```text
三个根因已修复
三个真实失败回归测试 PASS
Python / Desktop / Rust 全量 PASS
P0 Windows Gate PASS
Windows Release PASS
macOS Gate PASS
新的精确 product_commit
新的 macOS artifact_id
新的 Artifact ZIP SHA256
新的 DMG SHA256 / size
最终 DMG 内 release_metadata.commit 与 product_commit 精确一致
任务根外 acceptance 写入 = 0
PR #88 仍为 Draft
```

重新验收必须使用**新 Artifact**。真实 M5 的最终 PASS 仍只能由新一轮物理验收得出。
