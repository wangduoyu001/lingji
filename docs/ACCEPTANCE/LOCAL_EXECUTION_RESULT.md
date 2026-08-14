# LingJi 本机执行结果回执

## 1. 当前回执

```yaml
task_id: PR88-M5-REACCEPTANCE-2C96B3EC
status: RUNNING
verdict: FAIL
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: 2c96b3ec54b066204cad8db75455be24822852a9
task_instruction_commit: 17ab299c29e6ed37b355586a0d568d2e982bbf1b
report_branch: acceptance/pr88-m5-reacceptance-2c96b3ec
report_commit: PENDING
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_2c96b3ec.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_SUMMARY_2c96b3ec.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_HASHES_2c96b3ec.txt
cleanup_before: PASS
cleanup_after: PENDING
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: FAIL
started_at: 2026-08-15T00:00:00+08:00
finished_at: 2026-08-15T00:05:00+08:00
artifact_name: lingji-macos-arm64
artifact_id: 9224368022
artifact_workflow_run_id: 31813880672
artifact_zip_sha256: 6d7b4b8155d5f98abf3ec66fd2b793b51bac39833b08a92984781a7a07ac926e
dmg_sha256: 95b72565a30ca86c1eee1c2b0dd4c8239fcce774f32e66e7f24b33fe6b986372
identity_result: PASS
first_run_ux_result: FAIL
acceptance_isolation_result: PASS
window_recovery_result: FAIL
memory_progress_dashboard_result: FAIL
auth_status_boundary_result: PASS
secret_export_count: 0
first_launch_result: PASS
first_stop_result: NOT_TESTED
second_launch_result: PASS
second_stop_result: PASS
production_pollution_count: 0
rejected_artifact_retry: false
```

## 2. 结论

本轮安装包身份、整包替换、签名、隔离和第二次启动/停止均通过；主人明确判定 UI 整体不合格，因此最终为 `FAIL / DO NOT MERGE`。没有在本验收分支修改产品代码。

首次停止发生于主人观察结束后，未在停止前保留可复读的 Sidecar PID；不得把它写成 PASS。第二次停止已完成状态文件消失、记录 PID 退出和 8766 释放的三重确认。
