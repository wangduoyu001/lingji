# LingJi 本机执行任务单

> 本文件是当前本机 Codex 的唯一权威任务入口；macOS 具体安装与验收步骤以 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 为准。

## 1. 当前任务元数据

```yaml
task_id: MACOS-M5-AUTOPILOT-PHASE4-65DE7292
status: ACTIVE
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 65de729228b200869b118fd9c0798af6ad658bca
artifact_name: lingji-macos-arm64
artifact_id: 9213728587
artifact_archive_sha256: cf288e34bc8510540397489df9661fa72f8f4c4ec12ecfae14596a353e13ffeaa0
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46311297
dmg_sha256: 4666b0cda78baa81fc9150254f406f4c91faed520a2df850e4c8f52d2a1ff354
artifact_workflow_run_id: 31786165138
protocol_path: docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
macos_task_path: docs/ACCEPTANCE/MACOS_M5_LOCAL_EXECUTION_TASK.md
report_branch: acceptance/macos-m5-physical-acceptance-65de7292
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_65de7292.md
public_summary_path: docs/TEST_REPORTS/evidence/MACOS_M5_PHYSICAL_ACCEPTANCE_SUMMARY_65de7292.json
public_hashes_path: docs/TEST_REPORTS/evidence/MACOS_M5_PHYSICAL_ACCEPTANCE_HASHES_65de7292.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 已锁定的远程基线

```text
产品 Commit：65de729228b200869b118fd9c0798af6ad658bca
macOS Desktop Gate：31786165138（success）
P0 Windows Gate：31786165020（success）
Windows Desktop Release Baseline：31786165341（success）
tests：31786135735（success）
acceptance-doc-sync：31786135745（success）
local-execution-handoff：31786135834（success）
```

所有门禁必须与产品 Commit 精确一致。旧 Artifact、旧任务或 PR merge commit 均不得替代。

## 3. 执行与结论规则

- 先完成只读现场盘点和必要安全快照；不得删除或迁移主人正式数据。
- 仅使用 Artifact `9213728587` 和 task-scoped `LINGJI_ACCEPTANCE_DATA_ROOT`。
- 真实 M5 安装、启动、主人肉眼确认、退出、清理和报告远程复读全部完成前，结果只能是 `PENDING`、`FAIL` 或 `BLOCKED`，不得写 `PASS`。
- 发现产品缺陷时保存最小脱敏证据，完成安全清理后回传；不得修改被测产品 Commit 来规避失败。
