# LingJi 本机执行结果回执

```yaml
task_id: PR88-M5-OWNER-HOME-V2-F3CBA413
status: COMPLETED
verdict: FAIL
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: f3cba4136bd169619277279a55007fcd4ef609f4
task_instruction_commit: 88438f36c4f4bee088be8dd7af010fadc328fb35
report_branch: acceptance/pr88-m5-owner-home-v2-f3cba413
report_commit: d9a32e28ceb5505546e3bb45d16bb459b6d5a051
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_f3cba413.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_SUMMARY_f3cba413.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_HOME_V2_HASHES_f3cba413.txt
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: true
owner_observation: FAIL
started_at: 2026-08-16T00:16:00+08:00
finished_at: 2026-08-16T00:21:00+08:00
artifact_name: lingji-macos-arm64
artifact_id: 9249367672
artifact_workflow_run_id: 31894132498
artifact_zip_sha256: 3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36
dmg_sha256: a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
identity_result: PASS
first_run_ux_result: FAIL
owner_home_v2_result: FAIL
automation_flow_result: FAIL
recent_events_result: FAIL
window_recovery_result: NOT_TESTED
memory_progress_dashboard_result: FAIL
acceptance_isolation_result: PASS
auth_status_boundary_result: PASS
secret_export_count: 0
first_launch_result: PASS
first_stop_result: PASS
second_launch_result: PASS
second_stop_result: PASS
production_pollution_count: 0
rejected_artifact_retry: false
```

主人确认首页只显示“已收纳 2 份资料”，却不知道资料是什么、系统已经做了什么、下一步是什么、自己是否要行动。因此 `FAIL / DO NOT MERGE`；没有在本验收分支修改产品代码。
