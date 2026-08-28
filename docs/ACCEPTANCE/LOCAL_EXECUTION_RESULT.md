# LingJi 本机执行结果回执

> 当前任务为 `ACTIVE / IN_PROGRESS`。本回执只记录 Task8E Mac 体验候选准备进度，
> 不是 `COMPLETED`，也不是最终发布或 Phase 1 通过。

## 1. 当前回执

```yaml
task_id: TASK8E-MAC-EXPERIENCE-FFC2D885
status: RUNNING
verdict: PENDING
merge: DO NOT MERGE
execution_mode: MACOS_ARM64_RELEASE_CANDIDATE_OWNER_EXPERIENCE
repository: wangduoyu001/lingji
product_pr: none
product_branch: codex/phase1-automatic-memory
product_commit: ffc2d8851dc91b5f09b14d31a34c1e6988358933
artifact_name: lingji-macos-arm64-local-task8e
artifact_id: LOCAL-TASK8E-FFC2D885
task_instruction_commit: PENDING
report_branch: acceptance/task8e-mac-experience-ffc2d885
report_commit: PENDING
acceptance_root: /tmp/LingJiAcceptance/TASK8E-ffc2d8851
report_path: docs/TEST_REPORTS/MACOS_TASK8E_EXPERIENCE_CANDIDATE_ffc2d885.md
started_at: 2026-08-28T00:00:00+08:00
finished_at: null
cleanup_before: PASS
cleanup_after: NOT_STARTED
build_result: NOT_STARTED
install_result: NOT_STARTED
runtime_result: NOT_STARTED
ui_self_check_result: NOT_STARTED
owner_observation: NOT_STARTED
production_pollution_count: NOT_MEASURED
secret_export_count: NOT_MEASURED
quality_gate: BLOCKED_AT_MEASUREMENT_CAP
artifact_is_final_release: false
public_summary_path: docs/TEST_REPORTS/evidence/TASK8E_MAC_EXPERIENCE_SUMMARY_ffc2d885.json
public_hashes_path: docs/TEST_REPORTS/evidence/TASK8E_MAC_EXPERIENCE_HASHES_ffc2d885.txt
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
```

## 2. Preliminary evidence

- macOS and arm64 environment, exact build identity, artifact hashes, installation, runtime,
  UI self-check, and owner observation will be appended as they are freshly verified.
- The old IDLE task and rejected historical artifacts are not reused.
- No product code is authorized to change in this task.

## 3. Required closeout

The task remains ACTIVE until the candidate is open for owner observation. Closeout must use
`READY_FOR_OWNER_EXPERIENCE` if the candidate is running, or `BLOCKED`/`FAIL` with evidence if
it cannot be prepared. It must not use `COMPLETED` before owner confirmation and remote report
verification.
