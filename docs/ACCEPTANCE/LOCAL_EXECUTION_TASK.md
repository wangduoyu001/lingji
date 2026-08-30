# LingJi 本机执行任务单

> **当前状态：ACTIVE / OWNER_UI_MENU_FAST_TRACK_TASK_2_6BAF4EE6。**
>
> 本文件仍是本机 Codex 的唯一任务入口；只允许执行下方 `status: ACTIVE` 的精确候选。

## 0. 当前唯一 ACTIVE 任务

```yaml
task_id: OWNER_UI_MENU_FAST_TRACK_TASK_2_6BAF4EE6
status: ACTIVE
execution_mode: MACOS_OWNER_UI_EXPERIENCE_ONLY
candidate_label: OWNER_UI_EXPERIENCE_CANDIDATE
release_gate: NOT_A_RELEASE_GATE
repository: wangduoyu001/lingji
product_pr: NONE_NOT_A_RELEASE_GATE
product_branch: codex/owner-real-history-memory-cards
product_commit: 6baf4ee6d15256e44164bcbe3f7ce227af0b5d07
artifact_name: lingji-local-macos-arm64-tauri
artifact_id: LOCAL_TAURI_BUILD_6BAF4EE6
artifact_workflow_run_id: LOCAL_ONLY_NOT_CI
artifact_zip_sha256: PENDING
dmg_sha256: PENDING
report_branch: acceptance/owner-ui-menu-fast-track-task-2-6baf4ee6
report_path: docs/TEST_REPORTS/MACOS_OWNER_UI_EXPERIENCE_ONLY_6baf4ee6.md
public_summary_path: docs/TEST_REPORTS/evidence/MACOS_OWNER_UI_EXPERIENCE_ONLY_6baf4ee6.json
public_hashes_path: docs/TEST_REPORTS/evidence/MACOS_OWNER_UI_EXPERIENCE_ONLY_6baf4ee6.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
acceptance_root: /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6
acceptance_data_root: /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/data-root
acceptance_vault_root: /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/vault
acceptance_source_root: /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/source-fixture
acceptance_backup_root: /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/installed-app-backup
acceptance_evidence_root: /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/evidence
production_roots_untouched: true
backup_before_install_required: true
whole_bundle_replace_required: true
rollback: restore the pre-install whole /Applications/灵机.app bundle from acceptance_backup_root only; never delete or overwrite an existing backup
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
secret_export_count_required: 0
production_pollution_count_required: 0
quality_gate: MEASURED_FAIL_NOT_RELEASE_READY_DEFERRED
keep_app_and_sidecar_open_for_owner: true
```

本任务只负责 macOS arm64 Tauri 构建、严格签名核验、现有安装包整包备份/替换、Acceptance
物理隔离、认证 `127.0.0.1:8766` sidecar 健康证明和交接准备。必须覆盖 current、superseded、
stale、conflict、raw/vector/permanent 记忆与至少一个真实 pending action；Production、主人
真实聊天、真实 Vault、正式记忆、用户配置和未知进程均不得读取或修改。根代理负责 Computer
Use 全部 UI/菜单/窗口遍历和主人观察；本任务不得替主人宣布 PASS，不得宣称 release、Phase 1
或 merge 通过。遇到 DMG 失败但 `.app`、arm64 和 strict codesign 均成功时，记录失败并继续
whole-bundle 安装；其他真实 blocker 立即停止并报告。

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
