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
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_SUMMARY.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_HASHES.txt
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
source_failure_report_read: true
remote_failure_report_verified: false
identity_root_cause_fixed: false
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

## 2. 当前开发检查点

本机 Codex 当前报告：

```text
Phase 4 FAIL 报告：已在本机重建并声称完成远程核验
旧 Artifact 9102748834：永久拒绝
M5-UX-003：第一条 UX 修复已完成本地回归
身份精确性：待修
~/Documents/acceptance 隔离：待修
认证状态同步：待实现
```

UX 当前已完成的本地检查点：

```text
手动选择资料目录不再与“自动准备”并列
手动路径选择降级到高级兜底
对应回归测试先 FAIL、修复后 PASS
React / 前端构建 PASS
```

**注意：这仍不是 `M5-UX-003` 正式关闭。** 当前 GitHub PR #88 远程产品 Head 仍是旧 `171091fe...`，在 UX 修改进入新的产品 Head、完成远程 CI 并生成新 Artifact 前：

```text
first_run_ux_root_cause_fixed = false
ux_remote_product_head_verified = false
```

不得把本地焦点测试 PASS 写成产品 Release PASS。

## 3. 远程证据复读状态

截至 ChatGPT 本轮直接读取 GitHub：

```text
PR #88 = Draft / DO NOT MERGE
PR #88 remote product Head = 171091fe764c6653cdc7325b4a1a71e0b7800822
预期 acceptance/macos-m5-autopilot-phase4-171091fe ref 仍未由 GitHub API 直接解析到
```

因此本回执暂时保留：

```text
remote_failure_report_verified = false
remote_report_verified = false
```

这不否定本机已经生成报告；它表示**仓库权威状态尚未被当前远程读取证据闭环证明**。Codex 下一次提交/推送后必须再次 `git ls-remote` + GitHub API/`gh api` 复读，并把真实分支名、报告 Commit、PR 评论 ID 写入修复报告。

## 4. 下一执行顺序

不要重新发起旧包验收，也不要停在 UX 检查点。接下来按以下顺序连续执行：

```text
A. 安装包精确身份
   → 找到 CI exact-head 与真机 installed App 身份不一致的根因
   → 增加最终 DMG / installed App release_metadata 回归

B. acceptance 隔离
   → 找到谁绕过 LINGJI_ACCEPTANCE_DATA_ROOT 写入 ~/Documents/acceptance
   → 增加首次启动 + 再次启动的 packaged-chain 隔离集成测试

C. 认证状态安全同步
   → OS CredentialStore
   → lingji_state.db 非敏感 AuthStatus
   → Desktop / Autopilot 状态
   → allowlist sanitized snapshot
   → secret_export_count = 0

D. 统一收口
   → 三项真实失败回归全部 PASS
   → 认证状态回归 PASS
   → Python / Desktop / Rust / MCP 全量
   → P0 Windows + Windows Release
   → macOS Release Gate
   → 新精确产品 Head
   → 新 Artifact / 哈希
   → 更新 M5 固定任务单
```

这样可以避免每修一项就发一次包、真机再测一次，减少无意义的版本轮转。

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

根因、修复、回归测试、新 CI、新 Artifact 和远程复读全部完成后再把对应 `*_root_cause_fixed` 改为 `true`。

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
