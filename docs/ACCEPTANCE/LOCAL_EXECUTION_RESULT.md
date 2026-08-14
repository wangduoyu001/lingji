# LingJi 本机执行结果回执

> 本文件是本机 Codex 向主开发代理提交结果的唯一固定回执。当前唯一 `ACTIVE` 本机任务以 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 为准。

## 1. 当前回执

```yaml
task_id: MACOS-M5-AUTOPILOT-PHASE4-65DE7292
status: RUNNING
verdict: FAIL
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 65de729228b200869b118fd9c0798af6ad658bca
task_instruction_branch: docs/pr88-m5-task-65de7292
task_instruction_commit: PENDING
report_branch: acceptance/macos-m5-physical-acceptance-65de7292
report_commit: PENDING
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_65de7292.md
public_summary_path: docs/TEST_REPORTS/evidence/MACOS_M5_PHYSICAL_ACCEPTANCE_SUMMARY_65de7292.json
public_hashes_path: docs/TEST_REPORTS/evidence/MACOS_M5_PHYSICAL_ACCEPTANCE_HASHES_65de7292.txt
cleanup_before: PENDING
cleanup_after: PENDING
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: NOT_REQUIRED
local_temp_root_absent: PENDING
owner_observation: REQUIRED_FOR_PASS
started_at: PENDING
finished_at: PENDING
artifact_name: lingji-macos-arm64
artifact_id: 9213728587
workflow_run_id: 31786165138
artifact_archive_sha256: cf288e34bc8510540397489df9661fa72f8f4c4ec12ecfae14596a353e13ffeaa0
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46311297
dmg_sha256: 4666b0cda78baa81fc9150254f406f4c91faed520a2df850e4c8f52d2a1ff354
embedded_commit_exact: PRECHECK_PASS
ci_exact_head: PASS
artifact_integrity_precheck: PASS
physical_m5_acceptance: FAIL
production_pollution_count: 1
```

## 2. 已完成的远程与 Artifact 预检

```text
macOS Desktop Gate 31786165138 @ 65de729: PASS
P0 Windows Gate 31786165020 @ 65de729: PASS
Windows Desktop Release Baseline 31786165341 @ 65de729: PASS
tests 31786135735 @ 65de729: PASS
acceptance-doc-sync 31786135745 @ 65de729: PASS
local-execution-handoff 31786135834 @ 65de729: PASS
macOS DMG SHA256: PASS
macOS embedded Release Metadata Commit: PASS
Windows package SHA256SUMS: PASS
Windows build metadata Commit: PASS
```

这些预检不替代 M5 真机安装、启动、肉眼观察、退出和清理。本轮已因窗口找回缺失和 Production 根目录污染判定为 `FAIL`；临时根清理与最终远程回执仍待完成。

## 3. 本机必须回填

```text
预检与安全快照：PENDING
whole-bundle replace：PENDING
安装后 codesign：PENDING
首次启动 / 自动资料目录：PENDING
首页与自动接管的主人观察：PENDING
Runtime / 8766 / 生命周期：PENDING
二次启动：PENDING
Production 污染检查：PENDING
结束清理：PENDING
远程报告复读：PENDING
```

## 4. 失败处理

若发现产品缺陷，保留最小脱敏证据、执行安全清理并填入 `FAIL` 或 `BLOCKED`；不得修改被测产品 Commit、不得复用旧 DMG、不得把未执行写为 PASS。
