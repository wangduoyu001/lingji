# LingJi 本机执行任务单

> 本文件是当前本机 Codex 的唯一权威任务入口；macOS 具体安装与验收步骤以 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 为准。

## 1. 当前任务元数据

```yaml
task_id: MACOS-M5-AUTOPILOT-PHASE5-90398FD
status: ACTIVE
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 90398fd87f3419c598632479d2a00626b4554122
artifact_name: lingji-macos-arm64
artifact_id: 9215481793
artifact_archive_sha256: 7da451ae16a2e651647fa81114783aa60bcf7033b0a1a468984366e676c17f43
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46320916
dmg_sha256: 795c5099db13033812bc7006966246e6650ea362002722807b7e8aa8d655689d
artifact_workflow_run_id: 31790726207
protocol_path: docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
macos_task_path: docs/ACCEPTANCE/MACOS_M5_LOCAL_EXECUTION_TASK.md
report_branch: acceptance/macos-m5-physical-acceptance-90398fd
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_90398fd.md
public_summary_path: docs/TEST_REPORTS/evidence/MACOS_M5_PHYSICAL_ACCEPTANCE_SUMMARY_90398fd.json
public_hashes_path: docs/TEST_REPORTS/evidence/MACOS_M5_PHYSICAL_ACCEPTANCE_HASHES_90398fd.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 已锁定的远程基线

```text
产品 Commit：90398fd87f3419c598632479d2a00626b4554122
macOS Desktop Gate：31790726207（success）
P0 Windows Gate：31790726271（success）
Windows Desktop Release Baseline：31790726220（success）
tests：31790726216（success）
acceptance-doc-sync：31790726195（success）
local-execution-handoff：31790726267（success）
```

所有门禁必须与产品 Commit 精确一致。旧 Artifact、旧任务或 PR merge commit 均不得替代。

## 3. 执行与结论规则

- 先完成只读现场盘点；上轮失败建立的 Production 数据目录须保留并仅记录，绝不删除或迁移。
- 仅使用 Artifact `9215481793` 和 task-scoped `LINGJI_ACCEPTANCE_DATA_ROOT`。
- 验收必须覆盖窗口找回和记忆进度看板：进度数据必须源于实际 API，且未建立验证样本时不得声称检索准确率。
- 真实 M5 安装、启动、主人肉眼确认、退出、清理和报告远程复读全部完成前，结果只能是 `PENDING`、`FAIL` 或 `BLOCKED`，不得写 `PASS`。
- 发现产品缺陷时保存最小脱敏证据，完成安全清理后回传；不得修改被测产品 Commit 来规避失败。
