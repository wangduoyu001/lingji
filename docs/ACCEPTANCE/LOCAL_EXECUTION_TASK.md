# LingJi 本机执行任务单

> **当前状态：ACTIVE / READY FOR M5 REACCEPTANCE。**
>
> 本文件是本机 Codex 的唯一当前任务入口。PR #88 的新候选已经锁定到精确产品 Commit `1d99d10cdcb151c0a0257f7d0a93937cdb817b49`；六道同 SHA 产品门禁全部 PASS，macOS / Windows Artifact 已独立下载复核。
>
> 本轮只执行真实 M5 复验、主人体验确认、证据、远程回执与安全清理。**不得在验收分支修改产品代码，不得重跑任何历史失败 Artifact。**

## 1. 当前任务元数据

```yaml
task_id: PR88-M5-OWNER-WORK-FEED-V3-1D99D10C
status: ACTIVE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 1d99d10cdcb151c0a0257f7d0a93937cdb817b49
artifact_name: lingji-macos-arm64
artifact_id: 9250384637
artifact_workflow_run_id: 31897950589
artifact_zip_sha256: 8be6bc89dcbc9869d310879e23168f3f9474233e41c23c39526afdc5c9d665c0
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_sha256: 2973311a02311e0fad1f6ccc666a90d966509e95f54a8e3895dbea283d6fdc49
dmg_bytes: 46344072
windows_artifact_name: lingji-windows-0.1.0-1d99d10c
windows_artifact_id: 9250362769
windows_artifact_workflow_run_id: 31897950511
windows_artifact_zip_sha256: a7612cd57036a8d46c5f93399d14f8509ab00dc801be5c04c7bff38a877ee9bb
windows_installer_sha256: d263bb43ca4d86465a5eedd7637b9da5a625c72d28a0006909c1c943f81cf08e
windows_portable_sha256: bbb4c3d198d9c6e3ffa19773c1cac78788cb78750d75ca758383c37d96e8582f
report_branch: acceptance/pr88-m5-owner-work-feed-v3-1d99d10c
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_1d99d10c.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORK_FEED_V3_SUMMARY_1d99d10c.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORK_FEED_V3_HASHES_1d99d10c.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
same_sha_artifacts_required: true
secret_export_count_required: 0
rejected_artifact_f3cba413: 9249367672
rejected_artifact_2c96: 9224368022
rejected_artifact_171091fe: 9102748834
retry_rejected_artifact: false
```

## 2. 已锁定的同 SHA 远程证据

产品 Commit `1d99d10cdcb151c0a0257f7d0a93937cdb817b49`：

```text
tests                            run 31897950526  PASS
P0 Windows Gate                  run 31897950577  PASS
macOS Desktop Gate               run 31897950589  PASS
Windows Desktop Release Baseline run 31897950511  PASS
acceptance-doc-sync              run 31897950532  PASS
local-execution-handoff          run 31897950587  PASS
```

macOS Artifact `9250384637` 已独立下载复核：GitHub digest 与本地 ZIP SHA256 均为 `8be6bc89...`；ZIP 内唯一 DMG 为 `灵机_0.1.0_aarch64.dmg`，DMG SHA256 为 `2973311a...`。

Windows Artifact `9250362769` 已独立下载复核：ZIP SHA256 为 `a7612cd5...`，`build-metadata.json.commit` 精确等于产品 Commit，NSIS / portable 哈希与包内 `SHA256SUMS.txt` 一致。

本机 Codex 不得重新发包、替换 SHA、使用“同版本”猜测身份或复用旧 Artifact。

## 3. 本轮任务根

只允许使用：

```text
ACCEPTANCE_ROOT="$HOME/LingJiAcceptance/PR88-M5-OWNER-WORK-FEED-V3-1d99d10c"
LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
ISOLATED_HOME="$ACCEPTANCE_ROOT/isolated-home"
APP_BACKUP="$ACCEPTANCE_ROOT/app-backup/灵机.app"
```

本轮 Acceptance Runtime、日志、SQLite、Qdrant、raw、fixture、state 与普通证据必须位于任务根。不得创建 `~/Documents/acceptance`，不得写 Production DataRoot 或真实 Vault。

开始前若发现归属不明的既有目录、进程或端口占用，不擅自删除；记录并按 M5 专项协议处理。

## 4. Artifact 与安装身份

只下载 macOS Artifact `9250384637`。

必须逐项确认：

```text
Artifact ZIP SHA256 = 8be6bc89dcbc9869d310879e23168f3f9474233e41c23c39526afdc5c9d665c0
DMG SHA256 = 2973311a02311e0fad1f6ccc666a90d966509e95f54a8e3895dbea283d6fdc49
DMG bytes = 46344072
embedded product commit = 1d99d10cdcb151c0a0257f7d0a93937cdb817b49
Desktop architecture = arm64
Sidecar architecture = arm64
codesign --verify --deep --strict = PASS
```

旧 `/Applications/灵机.app` 必须 whole-bundle 移入 `$APP_BACKUP`，完整替换安装，禁止 overlay copy。任一身份、架构、哈希或签名不一致立即 `FAIL / DO NOT MERGE`。

## 5. 本轮核心：Owner Work Feed v3

至少使用 **2 份真实或任务专用资料**。主人不看开发文档、不理解 Qdrant / Embedding / SQLite / queue / 端口，也必须能直接从首页回答：

```text
1. 目前有哪些具体资料？
2. 每份资料灵机已经做了什么？
3. 每份资料下一步是什么？
4. 哪些需要我行动，哪些不用？
```

任一问题无法直接回答即 `FAIL / DO NOT MERGE`。

### A. 具体资料身份

首页每份资料至少应能看懂：

```text
标题或安全文件名
来源类型
时间
当前状态
```

禁止再次只出现“已收纳 2 份”“共有 N 条”等无法追溯到具体对象的数字。

### B. 灵机已做 / 下一步

每份资料必须明确两栏或等价信息：

```text
灵机已做：<真实完成动作>
下一步：<自动继续 / 等待主人 / 已可检索 / 失败原因入口>
```

不得要求主人根据七阶段名称自己推断发生了什么。

### C. 主人动作一致性

若任一资料显示 `需要你处理 / 等你确认`：

- 首页顶部不得同时显示“现在不用你做任何事”；
- 顶部必须出现对应主人待办；
- “去确认”必须直接进入相关审核/确认页面；
- 未批准前不得静默写入永久记忆。

没有主人事项时，首页必须明确说明当前无需主人操作。

### D. 明细不可用时必须诚实降级

若统计层显示有资料，但具体明细接口暂时不可读：

- 明确显示“具体明细暂不可用 / 正在重试”；
- 不得用一个数量替代资料清单；
- 此状态不能记为 Owner Work Feed PASS。

### E. 最近活动与统计

- 最近活动只能来自真实 allowlisted events；没有活动时明确空闲；禁止虚构“系统很忙”。
- 技术统计、片段数、coverage、Qdrant / Embedding 等保持次级或折叠。
- 没有验证样本时不得宣称“准确率”。

## 6. 主窗口找回，本轮不得再跳过

上一轮因为首页先失败，`window_recovery_result` 保持 `NOT_TESTED`。本轮最终 PASS 必须真实验证：

1. 将主窗口最小化、隐藏或移到不可见区域；
2. `窗口 → 将灵机带到当前屏幕`；
3. 窗口恢复可见、位置合理并获得焦点；
4. `Cmd/Ctrl + Shift + L`；
5. macOS Dock Reopen 至少一次。

任何一条核心找回路径实际失效均为 FAIL，不得用代码存在替代体验通过。

## 7. 安全、隔离与生命周期回归

继续强制：

```text
Acceptance task root 物理隔离 = PASS
Production pollution count = 0
secret_export_count = 0
AuthStatus 只含脱敏状态 = PASS
真实 Secret 只在系统安全凭据存储 = PASS
```

生命周期两轮都必须：

```text
启动 → authenticated 8766 healthy
→ 停止前保存 Sidecar PID + instance_id
→ exact-instance stop
→ sidecar-state.json gone
→ recorded PID gone
→ 8766 port free
```

同一任务根执行两轮。禁止把 `killall`、全局 `pkill` 或结束未知进程当正常成功路径。

## 8. 主人参与边界

Codex 负责下载、哈希、安装、签名、进程、端口、API、隔离、生命周期、日志、报告、Git、远程复读和清理。

主人只判断：

```text
能否看懂具体资料
能否看懂每份资料已经做了什么
能否看懂下一步
能否明确知道自己要不要行动
窗口找回是否真实好用
```

Codex 不得代替主人填写肉眼 PASS。

## 9. PASS / FAIL

只有以下全部成立才允许 `PASS`：

```text
精确 Artifact 身份 / arm64 / codesign PASS
首次正常启动 PASS
至少 2 份资料具体身份可理解 PASS
每份“灵机已做”可理解 PASS
每份“下一步”可理解 PASS
主人动作顶部/资料行一致 PASS
明细降级语义真实 PASS
真实活动流 PASS
Memory/统计真实性 PASS
窗口菜单 / 快捷键 / Dock Reopen PASS
Acceptance 物理隔离 PASS
AuthStatus / secret_export_count=0 PASS
第一次启动/停止 PID 三重证据 PASS
第二次启动/停止 PID 三重证据 PASS
Production pollution count = 0
8766/8767 本轮结束后无任务残留
远程报告 / 结果回执 / PR #88 评论复读 PASS
安全清理或失败回滚 PASS
```

任一 P0/P1 或主人体验项失败：

```text
verdict: FAIL
PR #88: DRAFT / DO NOT MERGE
Artifact 9250384637: DO NOT RETRY
不在 acceptance 分支修产品
```

外部权限/提交环境导致无法完成报告闭环才使用 BLOCKED；产品缺陷必须 FAIL。

## 10. 报告与远程闭环

报告分支：

```text
acceptance/pr88-m5-owner-work-feed-v3-1d99d10c
```

必须提交：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_1d99d10c.md
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORK_FEED_V3_SUMMARY_1d99d10c.json
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORK_FEED_V3_HASHES_1d99d10c.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

公开报告不得包含 Secret、Cookie、Authorization Header、真实私人绝对路径、对话正文或无必要截图原件。

第一次 push 后必须远程复读报告分支、Commit、报告、摘要、哈希与结果回执；完成安全清理/回滚后更新回执、再次 push 和复读；最后把 task_id、产品 Commit、报告 Commit 与 PASS/FAIL 写入 PR #88 评论。

**PR #88 在本轮真实 M5 主人 PASS 前始终保持 Draft / DO NOT MERGE。**
