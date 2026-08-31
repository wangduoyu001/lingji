# LingJi 本机执行任务单

> **当前状态：IDLE（最近任务 `OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_GATE` 已收口为 `COMPLETED / FAIL`）。**
>
> 本文件仍是本机 Codex 的唯一任务入口；下方第 0 节保留最近 release gate 的完整身份与结论。

## 0. 最近 release gate（已收口）

```yaml
task_id: OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_GATE
status: IDLE
execution_mode: RELEASE_VALIDATION_ONLY
candidate_label: OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_CANDIDATE_4F0D2A77
release_gate: RELEASE_INCLUDES_FULL
repository: wangduoyu001/lingji
product_pr: NONE_NOT_A_RELEASE_GATE
product_branch: codex/owner-memory-detail-drilldown
product_commit: 4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543
product_tests_commit: 81256c4242a6bb8062f1b591832a3313948e9ff9
artifact_name: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
artifact_id: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
artifact_workflow_run_id: LOCAL_ONLY_RELEASE_VALIDATION
artifact_zip_sha256: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
dmg_sha256: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
report_branch: acceptance/owner-memory-detail-drilldown-release-gate-4f0d2a77
report_path: docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_RELEASE_GATE.md
public_summary_path: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
public_hashes_path: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
acceptance_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_data_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_vault_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_source_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_backup_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_evidence_root: /tmp/LingJiAcceptance/owner-memory-detail-release-gate
production_roots_untouched: true
backup_before_install_required: false
whole_bundle_replace_required: false
rollback: no installation or runtime mutation is permitted
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
secret_export_count_required: 0
production_pollution_count_required: 0
live_8766_8767_forbidden: true
install_forbidden: true
owner_data_forbidden: true
full_is_included_by_release: true
duplicate_full_run_forbidden: true
power_shell_scope: isolated portable arm64 macOS tar.gz under acceptance_evidence_root/tooling
python_command: python3
keep_app_and_sidecar_open_for_owner: false
owner_observation_required: false
preserve_old_failed_evidence: true
quality_gate: automatic-memory-4r2-readiness MEASURED_FAIL; release must not be reported PASS if blocked
```

本轮是纯 release validation gate（已 `COMPLETED / FAIL`）：候选固定为当前 HEAD `4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543`，产品/测试代码提交为
`81256c4242a6bb8062f1b591832a3313948e9ff9`，不修改产品代码，不创建 Artifact，不安装，不启动 Desktop/sidecar，
不接触 live 8766/8767、Production/Vault、真实聊天/数据库或主人数据。`scripts/validate.ps1 -Mode release` 自含
full，不得另行重复运行 `-Mode full`。由于当前 Mac 没有系统 `pwsh`，只能在新的隔离临时根下载并记录微软官方
PowerShell GitHub release 的 arm64 macOS portable tar.gz URL、版本和 SHA256，解压后以该绝对路径执行真实
PowerShell；不得全局安装、修改系统 PATH 或用 Python 冒充 PowerShell。执行后必须确认无服务监听，并只读取
`output/validation/latest-summary.json|md` 与失败日志尾部；automatic-memory-4r2-readiness 已知 measured fail
时必须如实记录 release 阻断，不得写 PASS。

## 0. 最近收口任务（当前无 ACTIVE 任务）

```yaml
task_id: OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION
status: IDLE
execution_mode: FOCUSED_PRODUCT_IMPLEMENTATION_ONLY
candidate_label: OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION_BASELINE
release_gate: NOT_A_RELEASE_GATE
repository: wangduoyu001/lingji
product_pr: NONE_NOT_A_RELEASE_GATE
product_branch: codex/owner-memory-detail-drilldown
product_commit: c7388c08b495b1fbf1598358d76fe4176552f9ab
artifact_name: NOT_APPLICABLE_FOCUSED_ONLY
artifact_id: NOT_APPLICABLE_FOCUSED_ONLY
artifact_workflow_run_id: LOCAL_ONLY_FOCUSED_IMPLEMENTATION
artifact_zip_sha256: NOT_APPLICABLE_FOCUSED_ONLY
dmg_sha256: NOT_APPLICABLE_FOCUSED_ONLY
report_branch: acceptance/owner-memory-detail-drilldown-implementation
report_path: docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION.md
public_summary_path: NOT_APPLICABLE_FOCUSED_ONLY
public_hashes_path: NOT_APPLICABLE_FOCUSED_ONLY
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
acceptance_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_data_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_vault_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_source_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_backup_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_evidence_root: .superpowers/sdd/2026-08-31-owner-memory-detail-drilldown
production_roots_untouched: true
backup_before_install_required: false
whole_bundle_replace_required: false
rollback: no installation or runtime mutation is permitted; revert only this focused implementation branch if explicitly authorized
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: false
secret_export_count_required: 0
production_pollution_count_required: 0
quality_gate: MEASURED_FAIL_NOT_RELEASE_READY_DEFERRED
keep_app_and_sidecar_open_for_owner: false
owner_observation_required: false
preserve_old_failed_evidence: true
```

本任务负责的 Owner memory detail drilldown 产品代码、测试与验收文档已完成 focused 收口，具体实施计划为
`docs/superpowers/plans/2026-08-31-owner-memory-detail-drilldown.md`，已收束为 3 个实现任务 + 1 个
收口任务，共 4 个任务。允许修改产品代码，但
本轮仅运行 focused/product implementation 和合成 fixture；未启动 live 8766/8767、未进行 package/install、
未读取真实聊天/Vault/数据库、未操作主人数据。不得据此宣布主人体验/release/Phase 1 PASS。

范围固定为：四项普通导航和 current-only 列表不变；单卡详情通过现有 `/cards/{id}`、bounded
`/memories/{id}`、`/vector`、`/source` 与唯一新增的
`/api/memory/inspector/memories/{memory_id}/evidence` 按需显示 canonical 正文、当前结论、稳定
时间线、来源原文、raw/structured/vector/permanent 状态与主人处理语义。evidence 默认 20、最大
50，每 item excerpt<=240/content<=4000、单页 content<=24000 并带 truncated；不能暴露无界
`memory_evidence()`；不新建数据库、projector、状态源或 DELETE。`/memories/{id}` 仅可增加
`chunk_limit`/`max_chars`/`cursor` 且保留原 response fields；conversation-only 由前端依据
card kind/source conversation_id 显示“这是原始会话，尚未形成长期记忆”并使用现有 conversation
messages 分页，不调用 canonical。

旧 Mac 候选 `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A`（product SHA
`4ce1e00acb17bc5e4e4c183f58d30551ef76b101`）明确记录为 `COMPLETED / FAIL`，不再 ACTIVE；其
failure evidence、backup、fixture、DB、logs 与 Acceptance 根必须原样只读保留，不能复用或冒充
通过。该旧候选的主人结论为 `OWNER_UI_REPAIR_REQUIRED`，质量事实仍为
`MEASURED_FAIL / NOT_RELEASE_READY`。

本任务产生的新产品 SHA 为 `c7388c08b495b1fbf1598358d76fe4176552f9ab`；只有该 SHA 通过根代理的
full/release 门禁后，才允许创建新的 Mac acceptance task。新任务须使用新隔离根、同 SHA arm64 全包构建/安装和 Computer Use 全页遍历，至少打开五种
不同类型记忆并展开多个来源原文；主人明确确认前不得写完成。

## 1. 最近一次任务

```yaml
task_id: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
status: IDLE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
artifact_name: lingji-macos-arm64
artifact_id: 9258682849
artifact_workflow_run_id: 31928631105
artifact_zip_sha256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
dmg_sha256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
report_branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
report_commit: 5793e4ae22e17d1f4db2c57ecc66bf18ec65af2e
cleanup_receipt_commit: 3011d796ff1bb5bff7d5e37c24e0c6236ee51d34
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_SUMMARY_bd1e7a17.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_HASHES_bd1e7a17.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
pr_receipt_comment: 5306178636
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
same_sha_artifacts_required: true
secret_export_count_required: 0
production_pollution_count_required: 0
retry_rejected_artifact: false
```

## 2. 最终结论

```text
status: COMPLETED
verdict: FAIL
merge: DO NOT MERGE
PR #88: KEEP DRAFT
Artifact 9258682849: DO NOT RETRY
```

技术项通过：精确产品/Artifact 身份、arm64、strict codesign、whole-bundle replace、Acceptance 隔离、认证与 Secret 边界、两轮 Runtime 精确生命周期、分页终点、Production pollution=0、失败回滚与清理。

主人体验失败：

- 首页声称存在待确认候选，但“需要我”显示 `0` 个真实待办，事实链互相矛盾；
- “工作”履历为 `0`，无法说明真实做了什么、结果、下一步和执行者；
- `Cmd+K` 的真实“记住”提交失败，没有进入可追踪 Capture 流程；
- “记忆”只有泛化标题，缺少可读正文/摘要与可验证来源链；
- 主动发现只能看到静态说明，看不出接管了什么、已执行什么、下一步自动做什么；
- Window Recovery 三条路径未全部获得主人肉眼确认，保持 `NOT_TESTED`。

主人总评：**看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。**

## 3. 当前禁止事项

以下 macOS Artifact 均永久禁止重跑：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

当前没有本机验收任务。下一轮必须先完成新的产品级真实对象链修复，至少形成：

```text
真实资料 / 任务对象
→ 自动发现或主人输入
→ 真实执行事件
→ 可读执行结果
→ 下一动作 + 下一执行者
→ 真实待办（仅在需要主人时）
→ 可读永久记忆正文 / 摘要 + 可验证来源
```

首页、需要我、工作、记忆、Capture 必须读取同一条事实链，不允许再通过各自的投影/模板拼出互相矛盾的状态。

完成新的产品代码、focused/full/release CI、新产品 Commit、同 SHA macOS/Windows Artifact 与哈希锁定后，才允许创建新的 `ACTIVE` M5 任务。

不得在 acceptance 分支修改产品代码；历史报告只作为证据，不承担当前任务职责。
