# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交当前任务结果的固定回执。
>
> 当前任务为 PR #88 的 M5 Phase 4 失败根因修复，并包含本机认证状态安全同步增强。旧 `171091fe` Artifact 已拒绝，不得在没有新产品 Head 和新 Artifact 的情况下重新真机验收。

## 1. 当前回执

```yaml
task_id: PR88-M5-PHASE4-FAILURE-REPAIR-171091FE
status: RUNNING
verdict: PENDING
execution_mode: FAILURE_REPORT_FIRST_THEN_ROOT_CAUSE_REPAIR
repository: wangduoyu001/lingji
product_pr: 88
product_commit: 171091fe764c6653cdc7325b4a1a71e0b7800822
task_instruction_commit: 286f678ef603aec333168e8afc1bb5c58da3b659
report_branch: acceptance/pr88-m5-phase4-failure-repair-171091fe
report_commit: 602d5326e8990796e8e9206f82d6fd9a37366adc
report_path: docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_SUMMARY.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_HASHES.txt
cleanup_before: PASS_OWNER_COMPLETED
cleanup_after: NOT_RUN
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: false
pr_comment_verified: true
pr_comment_id: 5254742686
local_temp_root_absent: false
owner_observation: NOT_REQUIRED
started_at: PENDING
finished_at: PENDING
source_failure_report_read: true
remote_failure_report_verified: true
identity_root_cause_fixed: false
identity_fix_branch: fix/pr88-m5-phase4-171091fe
identity_fix_head: 90b7a70de2a5053c1224ee810949256a378f582a
identity_gate_checkpoint: PASS_FINAL_DMG_METADATA_CONTRACT_PUBLISHED
identity_rust_tests: NOT_RUN_NO_CARGO_TOOLCHAIN
first_run_ux_root_cause_fixed: false
ux_local_checkpoint: PASS_FOCUSED_TEST_AND_FRONTEND_BUILD
ux_remote_product_head_verified: false
acceptance_isolation_root_cause_fixed: false
three_real_failure_regressions: NOT_RUN
auth_sync_contract_path: docs/AUTH_CREDENTIAL_STATE_SYNC.md
auth_state_sync_implemented: false
auth_status_regressions: NOT_RUN
auth_snapshot_generated: false
auth_snapshot_path: docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_PR88.json
auth_blockers: PENDING
secret_export_count: PENDING
full_ci: NOT_RUN
windows_release: NOT_RUN
macos_release: NOT_RUN
new_exact_product_head: PENDING
new_artifact_id: PENDING
new_artifact_hashes_verified: false
old_artifact_retry: false
```

## 2. 已闭环的失败报告证据

GitHub 远程已直接复读并确认：

```text
失败报告分支 = acceptance/pr88-m5-phase4-failure-repair-171091fe
失败报告内容 commit = 602d5326e8990796e8e9206f82d6fd9a37366adc
报告远程确认 commit = 36421dba21b3f36040493119a062988b77129c37
失败报告 = docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
PR #88 FAIL / DO NOT MERGE 评论 ID = 5254742686
```

因此以下状态已经成立：

```text
source_failure_report_read = true
remote_failure_report_verified = true
remote_branch_verified = true
remote_commit_verified = true
remote_report_verified = true
pr_comment_verified = true
```

这只表示失败证据闭环，不表示任何产品缺陷已经关闭。

## 3. 当前开发检查点

### M5-UX-003

本机 Codex 已完成第一条 UX 修复：

```text
手动选择资料目录不再与“自动准备”并列
手动路径选择降级到高级兜底
对应 UI 回归先 FAIL、修复后 PASS
React / 前端构建 PASS
```

当前仍保持：

```text
first_run_ux_root_cause_fixed = false
ux_remote_product_head_verified = false
```

因为该修改尚未进入最终产品 Head、完整 CI 和新 Artifact。

### M5-IDENTITY-002

远程修复分支已经存在：

```text
branch = fix/pr88-m5-phase4-171091fe
head = 90b7a70de2a5053c1224ee810949256a378f582a
```

已发布的身份门禁改造包括：

```text
从最终挂载 DMG 的真实 App 导出 release metadata
验证 metadata.commit == expected exact product Head
验证主程序 arm64
验证 Sidecar arm64 且来自同一 bundle
比较 build 前 App 与最终 DMG App metadata
不再只依赖 strings | grep
```

当前环境没有 cargo，因此 Rust 本机测试未执行；macOS UI / release 合同焦点测试已通过。这个检查点**不能**提前写成 `identity_root_cause_fixed=true`，必须等最终统一 Head 上完整 Rust/Tauri、macOS Gate 和新 Artifact 实证。

## 4. 下一执行顺序

不要生成中间 Artifact，也不要重新做 M5 真机验收。继续：

```text
A. 关闭 M5-ISOLATION-002
   → 定位谁绕过 LINGJI_ACCEPTANCE_DATA_ROOT 写入 ~/Documents/acceptance
   → 增加 packaged bootstrap + Sidecar 首次/再次启动隔离集成回归

B. 实现认证状态安全同步
   → OS CredentialStore
   → lingji_state.db 非敏感 AuthStatus
   → Desktop / Autopilot 只展示认证结论
   → allowlist sanitized snapshot
   → secret_export_count = 0

C. 统一收口已有 UX + Identity 修改
   → 合并到一个新的精确产品 Head
   → 三项真实失败回归 PASS
   → AuthStatus 回归 PASS
   → Python / Desktop / Rust / MCP 全量
   → P0 Windows + Windows Release
   → macOS Release Gate
   → 新 macOS Artifact / ZIP / DMG 哈希
   → 独立下载复核最终 DMG 内 metadata
   → 更新 M5 固定任务单
```

## 5. 当前已知失败身份

```text
failed product commit = 171091fe764c6653cdc7325b4a1a71e0b7800822
failed artifact id = 9102748834
failed DMG sha256 = 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
physical verdict = FAIL
```

旧 Artifact 不得重试。

## 6. 必须关闭的三个真实缺陷

```text
M5-IDENTITY-002
M5-UX-003
M5-ISOLATION-002
```

只有根因、对应真实回归、统一最终 Head、全量 CI、新 Artifact 和远程复读全部完成后，才能把对应 `*_root_cause_fixed` 改为 `true`。

## 7. 本轮必须完成的认证状态增强

认证同步不是第四个 M5 FAIL，但本轮必须实现：

```text
本机 Secret → OS 安全凭据存储
认证验证 → lingji_state.db 非敏感状态
Desktop / Autopilot → 只显示认证结论
验收/交接 → allowlist 脱敏快照
GitHub → 只保存认证状态，不保存 Secret
```

权威合同：

```text
docs/AUTH_CREDENTIAL_STATE_SYNC.md
```

最终必须回填：

```text
auth_state_sync_implemented = true
auth_status_regressions = PASS
auth_snapshot_generated = true
auth_snapshot_path = docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_PR88.json
auth_blockers = 0
secret_export_count = 0
```

任何 Token / Refresh Token / API Key / Cookie / Authorization Header / Secret 片段进入仓库，当前任务直接 FAIL。

## 8. 最终原则

只有新的精确产品 Head、三个真实失败根因关闭、认证状态同步增强完成、双平台 Release Gate、新 macOS Artifact 和独立哈希核验完成后，才允许把 M5 固定任务单重新切为 ACTIVE。

本回执 `COMPLETED` 只代表**开发修复和新包交付完成**，不代表真实 M5 已 PASS。
