# LingJi 本机执行结果回执

> 这是当前最近一次本机任务的权威回执。当前任务单已转为 `IDLE`，不会自动触发新的本机执行。

## 1. 最近一次回执

```yaml
task_id: PR88-M5-REACCEPTANCE-2C96B3EC
status: COMPLETED
verdict: FAIL
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: 2c96b3ec54b066204cad8db75455be24822852a9
task_instruction_commit: 17ab299c29e6ed37b355586a0d568d2e982bbf1b
report_branch: acceptance/pr88-m5-reacceptance-2c96b3ec
report_commit: 9fdbacf52c22ecaac7eab3a4676f80a81e0dfa95
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_2c96b3ec.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_SUMMARY_2c96b3ec.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_HASHES_2c96b3ec.txt
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: true
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

最终结论：`FAIL / DO NOT MERGE`。

技术侧通过：安装包身份、Apple Silicon、签名、Acceptance 隔离、认证状态边界、第二次启动/停止、失败后的 App 恢复与清理。

主人明确未通过以下体验项：

- `M5-UX-003`：首页看不出系统自动执行了什么；
- `M5-UX-004`：新 UI 与旧版没有明显、可感知的差异；
- `M5-UX-005`：信息层级不友好；
- `window_recovery_result: FAIL`；
- `memory_progress_dashboard_result: FAIL`。

首次停止没有在停止前保存可复读 Sidecar PID，因此保持 `NOT_TESTED`，不伪造 PASS。

## 3. 证据

- 报告分支：`acceptance/pr88-m5-reacceptance-2c96b3ec`
- 报告 Commit：`9fdbacf52c22ecaac7eab3a4676f80a81e0dfa95`
- 清理回执 Commit：`33982e1d5d3d567369e56484ade733a8b7228408`
- PR #88 回执评论：`5295519058`

新的产品修复完成并生成新 Commit / 新 Artifact 之前，本回执保持最终失败事实，不得改回 PENDING，也不得重跑 Artifact `9224368022`。
