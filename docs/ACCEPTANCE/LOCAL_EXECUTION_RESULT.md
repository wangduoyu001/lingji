# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交 PR #88 M5 真机复验结果的固定回执。
>
> 当前任务已切换到精确产品 Commit `2c96b3ec54b066204cad8db75455be24822852a9` 的 M5 reacceptance。任务开始前保持 `PENDING`；本机 Codex 读取权威任务单后更新为 `RUNNING`，完成真机与远程闭环后更新为 `COMPLETED`。

## 1. 当前回执

```yaml
task_id: PR88-M5-REACCEPTANCE-2C96B3EC
status: PENDING
verdict: PENDING
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: 2c96b3ec54b066204cad8db75455be24822852a9
task_instruction_commit: PENDING
report_branch: acceptance/pr88-m5-reacceptance-2c96b3ec
report_commit: PENDING
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_2c96b3ec.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_SUMMARY_2c96b3ec.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_HASHES_2c96b3ec.txt
cleanup_before: NOT_RUN
cleanup_after: NOT_RUN
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: NOT_REQUIRED
started_at: PENDING
finished_at: PENDING
artifact_name: lingji-macos-arm64
artifact_id: 9224368022
artifact_workflow_run_id: 31813880672
artifact_zip_sha256: 6d7b4b8155d5f98abf3ec66fd2b793b51bac39833b08a92984781a7a07ac926e
dmg_sha256: 95b72565a30ca86c1eee1c2b0dd4c8239fcce774f32e66e7f24b33fe6b986372
windows_artifact_id: 9224405293
windows_artifact_zip_sha256: 33e5090e3e7052c9b38514d7c1c3fc7538a58eed609494acfa810b66e04d4d95
identity_result: NOT_RUN
first_run_ux_result: NOT_RUN
acceptance_isolation_result: NOT_RUN
window_recovery_result: NOT_RUN
memory_progress_dashboard_result: NOT_RUN
auth_status_boundary_result: NOT_RUN
secret_export_count: NOT_RUN
first_launch_result: NOT_RUN
first_stop_result: NOT_RUN
second_launch_result: NOT_RUN
second_stop_result: NOT_RUN
production_pollution_count: NOT_RUN
rejected_artifact_retry: false
```

## 2. 本轮固定身份

```text
Product Commit: 2c96b3ec54b066204cad8db75455be24822852a9
macOS Artifact: 9224368022 / lingji-macos-arm64
macOS ZIP SHA256: 6d7b4b8155d5f98abf3ec66fd2b793b51bac39833b08a92984781a7a07ac926e
DMG SHA256: 95b72565a30ca86c1eee1c2b0dd4c8239fcce774f32e66e7f24b33fe6b986372
Windows same-SHA Artifact: 9224405293
Windows ZIP SHA256: 33e5090e3e7052c9b38514d7c1c3fc7538a58eed609494acfa810b66e04d4d95
Rejected old Artifact: 9102748834 / DO NOT RETRY
```

## 3. 本机 Codex 完成后必须回填

至少回填并在正式报告中提供对应脱敏证据：

```text
identity_result = PASS / FAIL
first_run_ux_result = PASS / FAIL
acceptance_isolation_result = PASS / FAIL
window_recovery_result = PASS / FAIL
memory_progress_dashboard_result = PASS / FAIL
auth_status_boundary_result = PASS / FAIL
secret_export_count = 0 才允许 PASS
first_launch_result / first_stop_result / second_launch_result / second_stop_result = PASS / FAIL
production_pollution_count = 0 才允许 PASS
owner_observation = PASS / FAIL
cleanup_before / cleanup_after = PASS
```

最终 `COMPLETED / PASS` 还必须满足任务单规定的远程分支、Commit、报告、结果回执和 PR #88 评论复读全部成功。

任何阻断项失败时记录 `COMPLETED / FAIL`；只有无法自行解决的外部提交/权限阻断才使用 `BLOCKED_SUBMISSION / BLOCKED`。不得把产品缺陷标成 BLOCKED 逃避 FAIL。
