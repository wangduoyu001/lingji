# LingJi 本机执行任务单

> **当前状态：ACTIVE / READY FOR M5 REACCEPTANCE。**
>
> 本文件是本机 Codex 的唯一当前任务入口。PR #88 已完成 Owner Home v2 产品修复，并将产品候选锁定到精确 Commit `f3cba4136bd169619277279a55007fcd4ef609f4`。六道同 SHA 自动门禁全部 PASS，新的 macOS / Windows Artifact 已独立下载和复核哈希。
>
> 本轮只做真实 M5 复验、证据、远程回执与安全清理。**不得在验收分支修产品，不得重跑任何历史失败 Artifact。**

## 1. 当前任务元数据

```yaml
task_id: PR88-M5-OWNER-HOME-V2-F3CBA413
status: ACTIVE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: f3cba4136bd169619277279a55007fcd4ef609f4
artifact_name: lingji-macos-arm64
artifact_id: 9249367672
artifact_workflow_run_id: 31894132498
artifact_zip_sha256: 3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_sha256: a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
dmg_bytes: 46339959
windows_artifact_name: lingji-windows-0.1.0-f3cba413
windows_artifact_id: 9249378683
windows_artifact_workflow_run_id: 31894132475
windows_artifact_zip_sha256: 3415fb914d2ec50620634cc03ed5b5961424e314a0b2cdacdedebf5c72e7a049
windows_installer_sha256: e8261683f6e4a1afc4bd50094a80115684641095121050b152d122b25a83a13b
windows_portable_sha256: 6346a503bcad1fd1def02f4eca126ffb1298df1b5b7815a7cedacdd5c87b4cf2
report_branch: acceptance/pr88-m5-owner-home-v2-f3cba413
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_f3cba413.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_SUMMARY_f3cba413.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_HASHES_f3cba413.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
same_sha_artifacts_required: true
secret_export_count_required: 0
rejected_artifact_2c96: 9224368022
rejected_artifact_171091fe: 9102748834
retry_rejected_artifact: false
```

## 2. 已锁定的同 SHA 远程证据

产品 Commit `f3cba4136bd169619277279a55007fcd4ef609f4` 已通过：

```text
tests                            run 31894132471  PASS
P0 Windows Gate                  run 31894132505  PASS
macOS Desktop Gate               run 31894132498  PASS
Windows Desktop Release Baseline run 31894132475  PASS
acceptance-doc-sync              run 31894132538  PASS
local-execution-handoff          run 31894132477  PASS
```

macOS Artifact `9249367672` 已独立下载验证：ZIP SHA256 与 GitHub Artifact digest 一致；ZIP 内唯一 DMG 为 `灵机_0.1.0_aarch64.dmg`，DMG SHA256 与任务单一致。

Windows Artifact `9249378683` 已独立下载验证：`build-metadata.json.commit` 精确等于产品 Commit；NSIS 与 portable 哈希与包内 `SHA256SUMS.txt` 一致。

因此本机 Codex不得重新发包、切换 SHA、猜测“相同版本”或复用旧包。

## 3. 本轮任务根

只允许使用：

```text
ACCEPTANCE_ROOT="$HOME/LingJiAcceptance/PR88-M5-OWNER-HOME-V2-f3cba413"
LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
ISOLATED_HOME="$ACCEPTANCE_ROOT/isolated-home"
APP_BACKUP="$ACCEPTANCE_ROOT/app-backup/灵机.app"
```

本轮所有 Acceptance Runtime、日志、SQLite、Qdrant、raw、vault fixture、state 和普通证据必须位于任务根。不得创建 `~/Documents/acceptance`，不得写 Production DataRoot 或真实 Vault。

开始前若发现归属不明的既有 Acceptance 数据，不擅自删除，记录环境状态并按专项协议处理。

## 4. Artifact 与安装身份

只下载 Artifact `9249367672`。

必须依次确认：

```text
Artifact ZIP SHA256 = 3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36
DMG SHA256 = a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
DMG bytes = 46339959
embedded product commit = f3cba4136bd169619277279a55007fcd4ef609f4
Desktop architecture = arm64
Sidecar architecture = arm64
codesign --verify --deep --strict = PASS
```

旧 `/Applications/灵机.app` 必须 whole-bundle 移入 `$APP_BACKUP`，完整复制新 App 后再验证签名。禁止 overlay copy。

任一身份、哈希、架构或签名不一致立即 `FAIL / DO NOT MERGE`。

## 5. Owner Home v2 主人体验复验

这是本轮核心，不能用 CI 代替主人判断。

首次正常启动后，主人只需要看产品，不需要理解 DataRoot、Qdrant、Embedding、SQLite、MCP 或端口。

必须检查：

### A. 首屏主结构

主人在几秒内应能回答：

```text
现在有没有必须由我决定的事？
灵机此刻正在做什么？
自动工作流走到哪一步？
最近真正自动做过什么？
下一步是什么？
```

首屏结构必须明显区别于上一失败版，不得仍像一组并列技术卡片。

### B. 七阶段自动工作流

首页必须可见：

```text
发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回
```

每个状态必须与真实 queue / memory / review / vector 数据相符。不得用假的“运行中”动画或默认绿色掩盖未知状态。

### C. 最近自动完成

“最近自动完成”必须来自现有真实 `overview.events` / StateDatabase events。

- 有事件时：能看懂系统实际做过什么；
- 没有事件时：明确没有新的处理记录；
- 禁止制造虚假活动来显得系统很忙。

### D. 空闲降噪

没有真实 Codex activity、pending review 或读取异常时，首页不应常驻一个空的 Codex 工作卡。

### E. Memory Progress v2

主人应能直接理解：

- 已收纳多少资料；
- 当前更新中 / 等待 / 已完成；
- 当前索引覆盖；
- 没有验证样本时明确“不宣称准确率”。

不得把片段数、coverage 或向量数量包装成准确率。

## 6. 主窗口找回

必须至少验证：

1. 将主窗口最小化、隐藏或移到当前屏幕不可见区域；
2. 使用菜单 `窗口 → 将灵机带到当前屏幕`；
3. 主窗口恢复可见、回到合理位置并获得焦点；
4. 验证快捷键 `Cmd/Ctrl + Shift + L`；
5. macOS 上从 Dock 重新打开 App 时，至少验证一次 Reopen 能找回窗口。

该能力不得重置其他设置或影响 Runtime。

## 7. 安全、隔离与生命周期回归

继续强制验证：

```text
Acceptance task root 物理隔离 = PASS
Production pollution count = 0
secret_export_count = 0
AuthStatus 只含脱敏状态 = PASS
真实 Secret 只在系统安全凭据存储 = PASS
```

生命周期至少两轮：

```text
第一次启动 → authenticated 8766 healthy
→ 停止前保存当前 Sidecar PID 与 instance 身份
→ exact-instance stop
→ sidecar-state.json 消失
→ 记录 PID 真实退出
→ 8766 不再 LISTEN
→ 同一任务根第二次启动
→ authenticated 8766 healthy
→ 再次保存 PID / exact stop
→ state gone + PID gone + port free
```

**上一轮 first-stop 因未保存可复读 PID 只能 NOT_TESTED；本轮必须在停止前保存 PID 证据，不得再跳过。**

禁止 `killall`、全局 `pkill` 或结束不属于本轮精确实例的进程作为正常成功路径。

## 8. 主人参与边界

Codex 负责：下载、哈希、安装、签名、进程、端口、日志、API、隔离、生命周期、报告、Git、远程复读和清理。

主人只判断：

```text
首页是否一眼能看懂
自动化流程是否真的可见
新 UI 与上一失败版是否明显不同
Memory Progress 是否可理解
主窗口找回是否容易发现且实际有效
真正需要授权时动作是否清楚
```

Codex 不得替主人填写肉眼 PASS。

## 9. PASS / FAIL

只有以下全部成立才允许 `PASS`：

```text
精确 Artifact 身份 / arm64 / codesign PASS
首次正常启动 PASS
Owner Home v2 主人观察 PASS
七阶段工作流主人观察 PASS
真实事件流主人观察 PASS
Memory Progress v2 主人观察 PASS
主窗口菜单 / 快捷键 / Dock Reopen 复验 PASS
Acceptance 物理隔离 PASS
AuthStatus / secret_export_count=0 PASS
第一次启动/停止完整 PID 三重证据 PASS
第二次启动/停止完整 PID 三重证据 PASS
Production pollution count = 0
8766/8767 本轮结束后无任务残留
远程报告 / 结果回执 / PR #88 评论复读 PASS
安全清理或失败回滚 PASS
```

任一 P0/P1 或主人体验项失败：

```text
verdict: FAIL
PR #88: DRAFT / DO NOT MERGE
当前 Artifact: DO NOT RETRY
不在 acceptance 分支修产品
```

只有外部权限/提交环境导致无法完成报告闭环时才使用 BLOCKED；产品缺陷必须 FAIL。

## 10. 报告与远程闭环

报告分支：

```text
acceptance/pr88-m5-owner-home-v2-f3cba413
```

必须提交：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_f3cba413.md
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_SUMMARY_f3cba413.json
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_HASHES_f3cba413.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

报告与公开证据不得包含 Secret、Cookie、Authorization Header、真实私人绝对路径、对话正文或无必要截图原件。

第一次 push 后必须远程复读分支、Commit、报告、摘要、哈希、结果回执；完成安全清理/回滚后更新结果回执，再次 push 并远程复读；最后把 task_id、产品 Commit、报告 Commit 和 PASS/FAIL 写入 PR #88 评论。

**PR #88 在本轮真实 M5 主人 PASS 之前始终保持 Draft / DO NOT MERGE。**
