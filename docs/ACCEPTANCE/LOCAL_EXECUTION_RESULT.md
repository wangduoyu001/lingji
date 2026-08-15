# LingJi 本机执行结果回执

> 本文件是当前 ACTIVE 任务 `PR88-M5-OWNER-HOME-V2-F3CBA413` 的唯一结果回执。任务尚未在真实 M5 上执行完成，因此保持 `PENDING / PENDING`。

## 1. 当前回执

```yaml
task_id: PR88-M5-OWNER-HOME-V2-F3CBA413
status: PENDING
verdict: PENDING
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: f3cba4136bd169619277279a55007fcd4ef609f4
task_instruction_commit: PENDING
report_branch: acceptance/pr88-m5-owner-home-v2-f3cba413
report_commit: PENDING
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_f3cba413.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_SUMMARY_f3cba413.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_HASHES_f3cba413.txt
cleanup_before: NOT_RUN
cleanup_after: NOT_RUN
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: PENDING
started_at: PENDING
finished_at: PENDING
artifact_name: lingji-macos-arm64
artifact_id: 9249367672
artifact_workflow_run_id: 31894132498
artifact_zip_sha256: 3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36
dmg_sha256: a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
identity_result: NOT_RUN
first_run_ux_result: NOT_RUN
owner_home_v2_result: NOT_RUN
automation_flow_result: NOT_RUN
recent_events_result: NOT_RUN
window_recovery_result: NOT_RUN
memory_progress_dashboard_result: NOT_RUN
acceptance_isolation_result: NOT_RUN
auth_status_boundary_result: NOT_RUN
secret_export_count: NOT_RUN
first_launch_result: NOT_RUN
first_stop_result: NOT_RUN
second_launch_result: NOT_RUN
second_stop_result: NOT_RUN
production_pollution_count: NOT_RUN
rejected_artifact_retry: false
```

## 2. 当前精确身份

```text
Product Commit: f3cba4136bd169619277279a55007fcd4ef609f4
macOS Artifact: 9249367672 / lingji-macos-arm64
macOS ZIP SHA256: 3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36
DMG SHA256: a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
Windows Artifact: 9249378683 / lingji-windows-0.1.0-f3cba413
Windows ZIP SHA256: 3415fb914d2ec50620634cc03ed5b5961424e314a0b2cdacdedebf5c72e7a049
```

历史失败 Artifact `9224368022` 与 `9102748834` 均不得重跑。

## 3. 完成时必须回填

至少回填：

```text
identity_result = PASS / FAIL
first_run_ux_result = PASS / FAIL
owner_home_v2_result = PASS / FAIL
automation_flow_result = PASS / FAIL
recent_events_result = PASS / FAIL
window_recovery_result = PASS / FAIL
memory_progress_dashboard_result = PASS / FAIL
acceptance_isolation_result = PASS / FAIL
auth_status_boundary_result = PASS / FAIL
secret_export_count = 0 才允许 PASS
first_launch_result / first_stop_result / second_launch_result / second_stop_result = PASS / FAIL
production_pollution_count = 0 才允许 PASS
owner_observation = PASS / FAIL
cleanup_before / cleanup_after = PASS
```

本轮第一次停止必须在停止前保存 Sidecar PID，随后证明 `state gone + PID gone + 8766 port free`；不得再次以 `NOT_TESTED` 跳过。

最终 `COMPLETED / PASS` 还必须满足远程分支、Commit、报告、结果回执与 PR #88 评论全部复读成功。

任何产品或主人体验 P0/P1 缺陷必须写 `COMPLETED / FAIL`。不得把产品缺陷写成 BLOCKED。
