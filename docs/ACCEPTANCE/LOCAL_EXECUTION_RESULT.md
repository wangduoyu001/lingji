# LingJi 本机执行结果回执

> 当前任务正在执行：`OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A`。
> 当前候选仅为 `OWNER_UI_SOURCE_FILTER_REPAIR_CANDIDATE`，`NOT_A_RELEASE_GATE`；
> prior candidates `6ea11e4`/`43009a0d`/`6baf4ee6` 的主人体验结论为 `OWNER_UI_REPAIR_REQUIRED`；
> 新候选 `4ce1e00a` 尚未运行，当前仅等待隔离构建与验收，
> `MEASURED_FAIL / NOT_RELEASE_READY`
> 质量事实保持延期。下方旧任务回执仅作历史记录，
> 不覆盖当前 ACTIVE 任务。

Prior candidate `43009a0dfdf3cd7b949d871cc9054286f17d607e` is explicitly
recorded as `OWNER_UI_REPAIR_REQUIRED` for raw source titles/English error and
duplicate macOS lexical-alias source cards; it is not a PASS result.

## 0. 当前 ACTIVE 任务回执

```yaml
task_id: OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A
status: PENDING
verdict: PENDING
execution_mode: MACOS_OWNER_UI_EXPERIENCE_ONLY
repository: wangduoyu001/lingji
product_pr: NONE_NOT_A_RELEASE_GATE
product_commit: 4ce1e00acb17bc5e4e4c183f58d30551ef76b101
task_instruction_commit: d3bbf9c82e185f846ac8b3349f7e7ee6f786cd39
report_branch: acceptance/owner-ui-source-filter-repair-4ce1e00a
report_commit: PENDING
report_path: docs/TEST_REPORTS/MACOS_OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A.md
public_summary_path: PENDING
public_hashes_path: PENDING
cleanup_before: PENDING
cleanup_after: PENDING
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: PENDING
started_at: PENDING
finished_at: PENDING
installed_app_hash: PENDING
installed_main_sha256: PENDING
installed_sidecar_sha256: PENDING
dmg_sha256: PENDING
desktop_pid: 0
sidecar_pid: 0
control_api_ping: PENDING
acceptance_root: /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a
acceptance_effective_data_root: /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/data-root/acceptance
acceptance_memory_cards: 0
acceptance_completed_scans: 0
acceptance_pending_actions: 0
production_pollution_count: 0
vault_pollution_count: 0
owner_observation_page: PENDING
```

当前 Acceptance 根目录为 `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a`，尚未运行；
其 DataRoot、Vault、source fixture、evidence 与整包安装备份将在执行时物理分离。旧根
`/tmp/LingJiAcceptance/owner-ui-redesign-43009a0`、`/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6`
和 `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-b299e5b` 及其 backup/evidence/DB/logs
必须原样只读保留，prior candidate failures 与当前 PENDING receipt 分离。

旧候选 `OWNER_UI_MENU_FAST_TRACK_TASK_2_6BAF4EE6` 与 `OWNER_UI_REDESIGN_MAC_43009A0D` 的
`OWNER_UI_REPAIR_REQUIRED` 失败记录、备份、fixture、DB、日志与 evidence 根必须保留，不得删除
或用于新候选验证。新候选的全部结果只写入 `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a`。

`6ea11e4` 的真实 Mac 来源页失败证据已保留：discovery 同时返回可用 Codex sessions
和 `not_found` archived_sessions，但普通页面显示两个同名 Codex cards，并把不存在目录
描述为已发现；该候选不构成本轮 PASS。新 seed 固定为 37 cards（3 history）、13 permanent、
3 conversations、36 messages、1 owner high-risk pending action only；至少 8 个 synthetic
主题使用不同的主人可读 conclusions，不得制造自动扫描 failure pending。普通来源页断言
available sessions + `not_found` archive 仅产生 1 个 Codex card，found count 与 visible count 一致。

> 最近一次任务已完成。权威结论：`COMPLETED / FAIL / DO NOT MERGE`。
>
> 原始验收分支：`acceptance/pr88-m5-owner-workbench-v4-bd1e7a17`。报告提交为 `5793e4ae22e17d1f4db2c57ecc66bf18ec65af2e`，清理/最终结果回执提交为 `3011d796ff1bb5bff7d5e37c24e0c6236ee51d34`。原报告正文中自引用字段仍保留 `PENDING` 占位；最终状态以本回执、验收分支最终 `LOCAL_EXECUTION_RESULT.md` 与 PR #88 评论 `5306178636` 为准。

## 1. 最终回执

```yaml
task_id: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
status: COMPLETED
verdict: FAIL
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
task_instruction_commit: 5d5c1b9261085416d3f34eeb2321007972a6e46f
report_branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
report_commit: 5793e4ae22e17d1f4db2c57ecc66bf18ec65af2e
cleanup_receipt_commit: 3011d796ff1bb5bff7d5e37c24e0c6236ee51d34
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_SUMMARY_bd1e7a17.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_HASHES_bd1e7a17.txt
artifact_name: lingji-macos-arm64
artifact_id: 9258682849
artifact_workflow_run_id: 31928631105
artifact_zip_sha256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
dmg_sha256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
started_at: 2026-08-16T14:20:00+08:00
finished_at: 2026-08-16T14:46:00+08:00
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: true
owner_observation: FAIL
identity_result: PASS
arm64_result: PASS
strict_codesign_result: PASS
first_run_ux_result: FAIL
primary_navigation_result: PASS
memory_workspace_result: FAIL
owner_attention_result: FAIL
exact_memory_target_result: FAIL
work_history_result: FAIL
global_command_result: FAIL
pagination_boundary_result: PASS
automatic_discovery_result: FAIL
advanced_information_result: PASS
window_recovery_menu_result: NOT_TESTED
window_recovery_shortcut_result: NOT_TESTED
window_recovery_dock_result: NOT_TESTED
acceptance_isolation_result: PASS
auth_status_boundary_result: PASS
secret_export_count: 0
first_launch_result: PASS
first_stop_result: PASS
first_stop_saved_pid_result: PASS
second_launch_result: PASS
second_stop_result: PASS
production_pollution_count: 0
rejected_artifact_retry: false
```

## 2. 主人失败观察

主人明确结论：**看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。**

具体失败：

- 首页“待确认候选”与“需要我 0 待办”相互矛盾；
- 工作履历为空，无法解释真实结果、下一步和执行者；
- `Cmd+K` 真实“记住”提交失败；
- 记忆缺少可读正文/摘要和可验证来源；
- 主动发现仅为静态说明，无法体现真实接管/执行链；
- Window Recovery 菜单、快捷键、Dock Reopen 三路径未全部得到主人确认。

对应阻塞：`M5-V4-WORKBENCH-001 / P1`。

## 3. 已通过技术项与清理

产品/Artifact 身份、arm64、strict codesign、whole-bundle replace、Acceptance 隔离、认证状态边界、两轮 exact-instance Runtime 生命周期与分页终点通过；`secret_export_count=0`，`production_pollution_count=0`。

失败后被测 Runtime 已停止，验收前应用已整体恢复并保持签名有效，本轮临时任务根已安全清理，远程报告/结果/PR 评论已复核。

## 4. 结论

```text
FAIL / DO NOT MERGE
Artifact 9258682849: DO NOT RETRY
PR #88: KEEP DRAFT
current local task: IDLE
```

下一轮不得通过修改验收标准、复用当前 Artifact 或继续堆首页展示规避本次失败。必须先修真实对象与执行数据链，产生新的产品 Commit 与新的同 SHA Artifact。
