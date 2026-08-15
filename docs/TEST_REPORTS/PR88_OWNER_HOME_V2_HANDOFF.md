# PR #88 Owner Home v2 M5 交接报告

日期：2026-08-15

## 1. 目的

把 PR #88 在上一轮真实 M5 `FAIL / DO NOT MERGE` 后完成的 Owner Home v2 产品修复，正式转换为一个新的、可执行的 M5 真机复验任务。

本报告只记录交接和远程身份锁定，不宣称主人真机体验已 PASS。

## 2. 产品身份

```text
Repository: wangduoyu001/lingji
PR: #88
Product branch: feature/owner-autopilot-ui-codexpp
Product commit: f3cba4136bd169619277279a55007fcd4ef609f4
Task: PR88-M5-OWNER-HOME-V2-F3CBA413
```

上一失败候选：

```text
2c96b3ec54b066204cad8db75455be24822852a9
M5 verdict: FAIL / DO NOT MERGE
macOS Artifact: 9224368022 / DO NOT RETRY
```

更早失败 Artifact `9102748834` 同样保持 `DO NOT RETRY`。

## 3. 本轮产品修复

Owner Home v2 将首页改为：

```text
现在发生什么
→ 自动工作流走到哪一步
→ 最近真正自动做过什么
```

实现范围：

- 首屏优先展示主人事项；
- “此刻正在做”读取真实 queue/recent action；
- 七阶段自动流程：`发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回`；
- 最近自动完成读取已有 `overview.events`；
- 空闲 CurrentWork 隐藏；
- Memory Progress v2；
- macOS `窗口 → 将灵机带到当前屏幕`；
- `Cmd/Ctrl+Shift+L`；
- Dock Reopen 找回窗口。

产品实现与回归说明：

`docs/TEST_REPORTS/PR88_OWNER_HOME_V2_IMPLEMENTATION.md`

## 4. 精确产品门禁

Commit `f3cba4136bd169619277279a55007fcd4ef609f4`：

```text
tests                            31894132471 PASS
P0 Windows Gate                  31894132505 PASS
macOS Desktop Gate               31894132498 PASS
Windows Desktop Release Baseline 31894132475 PASS
acceptance-doc-sync              31894132538 PASS
local-execution-handoff          31894132477 PASS
```

六套 workflow 均绑定同一精确产品 Commit。

## 5. macOS Artifact

```text
Run: 31894132498
Artifact ID: 9249367672
Name: lingji-macos-arm64
Artifact ZIP SHA256:
3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36

DMG: 灵机_0.1.0_aarch64.dmg
DMG bytes: 46339959
DMG SHA256:
a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
```

复核方式：GitHub Artifact 下载后本地重新计算 ZIP SHA256，解压确认只有一份 DMG，并重新计算 DMG SHA256。

## 6. Windows 同 SHA Artifact

```text
Run: 31894132475
Artifact ID: 9249378683
Name: lingji-windows-0.1.0-f3cba413
Artifact ZIP SHA256:
3415fb914d2ec50620634cc03ed5b5961424e314a0b2cdacdedebf5c72e7a049

NSIS SHA256:
e8261683f6e4a1afc4bd50094a80115684641095121050b152d122b25a83a13b

Portable SHA256:
6346a503bcad1fd1def02f4eca126ffb1298df1b5b7815a7cedacdd5c87b4cf2
```

下载后已复读 `build-metadata.json`：

```text
commit = f3cba4136bd169619277279a55007fcd4ef609f4
target = x86_64-pc-windows-msvc
installer_format = nsis
```

包内 `SHA256SUMS.txt` 与独立读取到的 NSIS / portable 哈希一致。

## 7. 当前验收任务

`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 已切换为：

```text
task_id: PR88-M5-OWNER-HOME-V2-F3CBA413
status: ACTIVE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
```

`LOCAL_EXECUTION_RESULT.md` 已重置为：

```text
status: PENDING
verdict: PENDING
```

本次真机报告固定为：

```text
Branch:
acceptance/pr88-m5-owner-home-v2-f3cba413

Report:
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_f3cba413.md

Summary:
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_SUMMARY_f3cba413.json

Hashes:
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_HASHES_f3cba413.txt
```

## 8. 本轮必须补齐的历史缺口

上一轮首次 stop 没有在停止前保存可复读 Sidecar PID，因此只能 `NOT_TESTED`。

本轮每一次 stop 必须：

```text
停止前保存 Sidecar PID / exact instance
→ exact-instance stop
→ sidecar-state.json 消失
→ 原 PID 真实退出
→ 8766 无 LISTEN
```

两轮启动/停止都必须满足三重退出证据。

## 9. 主人体验门禁

主人必须实际确认：

- 首页与上一失败版有明显差异；
- 几秒内知道是否需要自己决定；
- 能看懂灵机此刻做什么；
- 能看懂七阶段自动化流程；
- 最近自动完成不是假事件；
- Memory Progress 是工作进度而非数字墙；
- 主窗口找回菜单容易发现并有效；
- 快捷键和 Dock Reopen 至少完成真实回归路径。

自动测试不能替代这些主人判断。

## 10. 安全边界

不改变：

- Production / Acceptance 物理隔离；
- 正文读取授权；
- 永久记忆人工确认；
- Production Qdrant 破坏性操作边界；
- CredentialStore / AuthStatus；
- `secret_export_count=0`；
- exact-instance Sidecar stop；
- whole-bundle 安装与失败回滚。

## 11. 合并边界

本交接完成后 PR #88 仍是：

```text
DRAFT / DO NOT MERGE
```

只有本任务真实 M5 `COMPLETED / PASS`、主人体验 PASS、技术回归 PASS、远程报告可复读、清理完成之后，才允许进入最终合并判断。
