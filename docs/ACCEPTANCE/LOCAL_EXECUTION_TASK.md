# LingJi 本机执行任务单

> **当前状态：IDLE / NO ACTIVE LOCAL TASK。**
>
> `PR88-M5-OWNER-HOME-V2-F3CBA413` 已在真实 M5 上完成，最终结论为 `FAIL / DO NOT MERGE`。失败原因是 Owner Home v2 仍无法让主人看懂资料对象、系统动作、下一步与是否需要主人行动。
>
> 本文件仍是本机 Codex 的唯一任务入口。`status: IDLE` 时不得下载、安装、启动、重跑 Artifact，也不得从历史报告自行推断下一任务。

## 1. 最近一次任务身份

```yaml
task_id: PR88-M5-OWNER-HOME-V2-F3CBA413
status: IDLE
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

## 2. 最终结论

```text
status: COMPLETED
verdict: FAIL
report commit: d9a32e28ceb5505546e3bb45d16bb459b6d5a051
cleanup receipt commit: 2a515a04540274809557d7f12ccdee1308a355e3
PR #88 receipt comment: 5303141355
```

技术侧通过：

- 包身份、ZIP / DMG 哈希、内嵌 Commit；
- Apple Silicon arm64 与 strict codesign；
- whole-bundle replace；
- Acceptance 数据隔离；
- `secret_export_count=0`；
- 首次与第二次启动/精确停止；
- Production pollution count = 0；
- FAIL 后恢复上一版 App 并完成任务根清理。

主人体验失败：

- `M5-OWNER-HOME-001`：只看到“已收纳 2 份资料”，不知道资料具体是什么；
- `M5-OWNER-HOME-002`：不知道灵机做了什么、接下来做什么、是否需要自己行动；
- `M5-OWNER-HOME-003`：七阶段没有形成可理解、可追溯的工作流。

`window_recovery_result` 因首页主结构已失败而保持 `NOT_TESTED`，不得伪造 PASS。

## 3. 当前禁止事项

Artifact `9249367672` 已完成失败验收，**永久 DO NOT RETRY**。Artifact `9224368022` 与 `9102748834` 同样不得重跑。

当前没有本机验收任务。下一轮必须先完成新的产品修复，形成：

```text
新产品 Commit
→ 同一精确 SHA 全部自动门禁
→ 新 macOS / Windows Artifact
→ 新 Artifact 哈希锁定
→ 新 task_id + status: ACTIVE
→ 才允许再次进入 M5
```

## 4. 下一轮产品最低要求

下一版首页必须从“数字/阶段展示”升级为“可追溯对象 + 明确动作”：

1. 每份资料可见标题/来源/时间/当前阶段；
2. 每份资料可追溯系统已经完成的动作；
3. 明确下一步由灵机自动做还是等待主人决定；
4. 首页第一屏直接回答“我现在需要做什么”；
5. 没有事件/任务时明确显示空闲，不用统计数字冒充过程。

历史验收细节以对应 `docs/TEST_REPORTS/` 和报告分支为证据，不得覆盖本文件当前 `IDLE` 状态。
