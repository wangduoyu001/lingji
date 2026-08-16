# LingJi 本机执行结果回执

> 当前任务：`PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17`。
>
> **状态：PENDING / verdict: PENDING。** 真机未完成前，不得把自动 CI、静态 smoke 或构建成功写成主人体验 PASS。

## 1. 当前回执

```yaml
task_id: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
status: PENDING
verdict: PENDING
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
task_instruction_commit: PENDING
report_branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
report_commit: PENDING
cleanup_receipt_commit: PENDING
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_SUMMARY_bd1e7a17.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_HASHES_bd1e7a17.txt
artifact_name: lingji-macos-arm64
artifact_id: 9258682849
artifact_workflow_run_id: 31928631105
artifact_zip_sha256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
dmg_sha256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
cleanup_before: NOT_RUN
cleanup_after: NOT_RUN
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: NOT_RUN
identity_result: NOT_RUN
first_run_ux_result: NOT_RUN
primary_navigation_result: NOT_RUN
memory_workspace_result: NOT_RUN
owner_attention_result: NOT_RUN
exact_memory_target_result: NOT_RUN
work_history_result: NOT_RUN
global_command_result: NOT_RUN
pagination_boundary_result: NOT_RUN
automatic_discovery_result: NOT_RUN
advanced_information_result: NOT_RUN
window_recovery_menu_result: NOT_RUN
window_recovery_shortcut_result: NOT_RUN
window_recovery_dock_result: NOT_RUN
acceptance_isolation_result: NOT_RUN
auth_status_boundary_result: NOT_RUN
secret_export_count: NOT_RUN
first_launch_result: NOT_RUN
first_stop_result: NOT_RUN
first_stop_saved_pid_result: NOT_RUN
second_launch_result: NOT_RUN
second_stop_result: NOT_RUN
production_pollution_count: NOT_RUN
rejected_artifact_retry: false
```

## 2. 自动产品门禁

产品 SHA `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9` 已完成同 SHA 自动产品门禁：

```text
tests 31928631115: PASS
P0 Windows Gate 31928631099: PASS
macOS Desktop Gate 31928631105: PASS
Windows Desktop Release Baseline 31928631101: PASS
acceptance-doc-sync 31928631103: PASS
local-execution-handoff 31928631118: PASS
```

这些结果只说明进入 M5 的技术前置条件成立，不代表主人体验通过。

## 3. 最终填写规则

Codex 真机执行后必须把所有 `NOT_RUN/PENDING` 改成真实结果，并遵守：

- 主人明确体验 FAIL 时最终只能 `COMPLETED / FAIL / DO NOT MERGE`；
- 任一 Window Recovery 路径未执行则不得 PASS；
- 第一轮 stop 没有保存并验证 Sidecar PID 则不得 PASS；
- `secret_export_count` 必须为 `0`；
- `production_pollution_count` 必须为 `0`；
- 报告、远程复读和清理未闭环不得 PASS；
- 当前 Artifact 一旦得到最终 FAIL 即永久 `DO NOT RETRY`。
