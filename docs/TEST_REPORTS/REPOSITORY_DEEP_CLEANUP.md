# Repository Deep Cleanup — 2026-09-19

## 1. Scope

Repository: `wangduoyu001/lingji`  
Baseline: `master@ced1128e50d3b3758585573042ea6bcc6f315384`  
Cleanup branch: `chore/repository-deep-cleanup-20260919`

This cleanup removes stale documentation from the default branch and retires obsolete open PRs without changing product code, Vault content, databases, Qdrant data, production settings, or the active Phase 1 implementation branch.

## 2. Authority preserved

The following remain authoritative and were not removed:

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATUS.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`
- `docs/DEVELOPMENT_RULES.md`
- current `docs/ACCEPTANCE/` governance and task/result contracts
- `docs/TEST_REPORTS/` evidence library

## 3. Documentation cleanup

Removed 54 current-tree documents that were one or more of:

- implementation plans for completed P0/P2 nodes;
- reports tied to closed/rejected Draft PRs;
- old machine-specific environment audits;
- parallel architecture/design documents superseded by current authorities;
- historical technical research that no longer governs implementation.

Git history remains the historical archive. No formal knowledge/Vault content was removed.

### Removed paths

- `docs/ACCEPTANCE/AUTOPILOT_PHASE4_ACCEPTANCE.md`
- `docs/DESKTOP_UI_MODULARIZATION_REPORT.md`
- `docs/DOCUMENTATION_MAINTENANCE.md`
- `docs/EXTRACTION_FRAMEWORK_REPORT.md`
- `docs/EXTRACTION_HARDENING_WEB_SKILLS_UI_REPORT.md`
- `docs/FINAL_P2_MERGE_REPORT.md`
- `docs/HARDWARE_COMPUTE_MODE_REPORT.md`
- `docs/LINGJI_TOOL_SERVICE_REPORT.md`
- `docs/LOCAL_CONTROL_CENTER_ARCHITECTURE.md`
- `docs/LOCAL_MODEL_CENTER_REPORT.md`
- `docs/MEDIA_EXTRACTION_REPORT.md`
- `docs/MEMORY_PIPELINE_DESIGN.md`
- `docs/MEMORY_SYSTEM.md`
- `docs/MODULES/P0_ENGINEERING_HYGIENE_IMPLEMENTATION.md`
- `docs/MODULES/P2_03B_STRUCTURED_INGESTION_WIRING.md`
- `docs/MODULES/P2_03C_CAPTURE_SOURCES_FOUNDATION.md`
- `docs/MODULES/P2_04_MEMORY_INSPECTOR_UI.md`
- `docs/MODULES/P2_05A_CAPTURE_CONTROL_API.md`
- `docs/MODULES/P2_05B_MANUAL_IMPORT_WIRING.md`
- `docs/MODULES/P2_05C_CAPTURE_CENTER_UI.md`
- `docs/MODULES/P2_05_INTEGRATED_IMPLEMENTATION.md`
- `docs/MODULES/P2_06_OBSIDIAN_CLI_MIGRATION_IMPLEMENTATION.md`
- `docs/MODULES/P2_07A_CODEX_SESSION_PROJECT.md`
- `docs/MODULES/P2_07B_CONTEXT_MEMORY_REVIEW.md`
- `docs/MODULES/P2_07C_LOCAL_UI_MEMORY_LOOP.md`
- `docs/MODULES/P2_08A_AUTO_REVIEW_CORE.md`
- `docs/MODULES/P2_08B_LOCAL_AI_REVIEWER.md`
- `docs/MODULES/P2_08B_SHADOW_API.md`
- `docs/MODULES/P2_09A_RUNTIME_TRUTH.md`
- `docs/MODULES/P2_09B_CANONICAL_IDEMPOTENCY.md`
- `docs/MODULES/P2_09C_DESKTOP_DATA_LAYER.md`
- `docs/MODULES/P2_09D_DESKTOP_UX_AUTO_REVIEW.md`
- `docs/MODULES/P2_10A_SETTINGS_GOVERNANCE_CORE.md`
- `docs/MODULES/P2_10B_NATIVE_DESKTOP_UI.md`
- `docs/MODULES/P2_10C_MEMORY_WORKSPACE_UI.md`
- `docs/MODULES/P2_11A_WINDOWS_RELEASE_BASELINE.md`
- `docs/MODULES/P2_11B_RUNTIME_SIDECAR_MANAGER.md`
- `docs/MODULES/P2_12A_OBSERVATION_FIRST_DESKTOP_UI.md`
- `docs/OBSIDIAN_CLI_AUDIT.md`
- `docs/OBSIDIAN_CLI_INTEGRATION_REPORT.md`
- `docs/OBSIDIAN_INTERACTION_AND_METADATA.md`
- `docs/PERMANENT_MEMORY_AND_RECALL.md`
- `docs/PHASE_02_OBSIDIAN_MANAGEMENT_REPORT.md`
- `docs/PHASE_03B_AI_CONNECTION_CONFIG_REPORT.md`
- `docs/PHASE_03_PERMANENT_MEMORY_GATEWAY_REPORT.md`
- `docs/REAL_ENVIRONMENT_ACCEPTANCE_REPORT.md`
- `docs/RUNTIME_MEDIA_SETTINGS_AND_HEALTH_REPORT.md`
- `docs/SINGLE_VAULT_ARCHITECTURE.md`
- `docs/TECH_RESEARCH/MACOS_M5_ACCEPTANCE.md`
- `docs/TECH_RESEARCH/MEMORY_INSPECTOR_CODE_ANALYSIS.md`
- `docs/TECH_RESEARCH/P2_08_STANDALONE_TO_LINGJI_MAPPING.md`
- `docs/TECH_RESEARCH/SRC_SECOND_BRAIN_CAPABILITY_AUDIT.md`
- `docs/VECTOR_DATABASE.md`
- `docs/WINDOWS_DB_LIFECYCLE_REPORT.md`

## 4. Reference audit

Maintained authority files were checked for references to the removed paths. The only current-tree references found were two historical mentions in `docs/CHANGELOG.md`; they were rewritten to point readers to Git history/current authorities rather than deleted files.

`docs/DEVELOPMENT_RULES.md` now explicitly defines retention rules so superseded implementation documents do not accumulate again.

## 5. Branch / PR audit

Remote state before cleanup:

- remote branches: **156**
- open PRs: **5**
- branch heads associated with merged PRs: **73** (including one historical PR whose head name was master; master is excluded from deletion)
- branch heads associated with closed-unmerged PRs: **10**
- branches with no directly associated PR in current API results: **68**
- duplicate-SHA branch groups: **5**

Open PR policy:

- keep: `#106 feat/sb0-work-fact-contract` (current Phase 1 implementation)
- retire as stale/superseded: `#54`, `#60`, `#88`, `#91`

### High-confidence remote branch prune set

The following branch names are merged-PR heads and are candidates for physical ref deletion after excluding any branch explicitly referenced by current acceptance authority:

- `closeout/pr88-m5-owner-workbench-v4-bd1e7a17`
- `codex/local-final-closeout-discovery-9eace85`
- `codex/pr60-autonomous-memory-release`
- `codex/pr60-cleanup-readonly-dir-623d3c9d`
- `codex/pr60-empty-vector-state-6214ac48`
- `codex/pr60-final-closeout-6214ac48-docs`
- `codex/pr60-final-closeout-f0956f67-docs`
- `codex/pr60-memory-quality-24f35704-task`
- `codex/pr60-memory-quality-05376996-task`
- `codex/pr60-memory-quality-trial-3739c42f-task`
- `codex/pr60-qdrant-owner-recovery`
- `codex/pr60-qdrant-second-owner`
- `codex/pr60-validation-git-identity-05376996`
- `codex/pr60-vector-snapshot-truth-05376996`
- `docs/acceptance-governance`
- `docs/final-local-closeout-handoff`
- `docs/fix-recovery-parent-cleanup-contract`
- `docs/local-execution-handoff-validation`
- `docs/memory-quality-trial-acceptance`
- `docs/pr60-acceptance-sync`
- `docs/pr88-acceptance-cleanup`
- `docs/pr88-close-work-feed-v3-fail`
- `docs/pr88-owner-home-v2-fail-closeout`
- `fix/cleanup-code-validation-workspace`
- `fix/pr60-autonomous-runtime-binding`
- `fix/pr60-d69874af-acceptance-gates`
- `fix/pr60-import-state-cleanup-recovery`
- `fix/pr60-launchable-codex-resolution`
- `fix/pr88-final-head-relock`
- `fix/pr88-final-same-sha`
- `fix/pr88-macos-real-exit-gate`
- `fix/pr88-owner-fact-chain-v5`
- `fix/pr88-owner-home-v2`
- `fix/pr88-owner-work-feed-v3`
- `fix/pr88-owner-workbench-v4`
- `fix/windows-db-lifecycle`
- `handoff/pr88-m5-owner-home-v2-f3cba413`
- `handoff/pr88-m5-owner-work-feed-v3-1d99d10c`
- `handoff/pr88-m5-owner-workbench-v4-bd1e7a17`
- `handoff/pr88-m5-reacceptance-2c96b3ec`
- `work/context-routing-validation`
- `work/master-ci-validation-finalization`
- `work/master-mainline-convergence`
- `work/p0-a-start-center`
- `work/p0-engineering-hygiene`
- `work/p2-05-integrated-validation`
- `work/p2-05a-capture-control-api`
- `work/p2-05b-manual-import-wiring`
- `work/p2-05c-capture-center-ui`
- `work/p2-06-obsidian-cli-migration`
- `work/p2-07-integrated-validation`
- `work/p2-07a-codex-session-project`
- `work/p2-07b-context-memory-review`
- `work/p2-07c-local-ui-loop`
- `work/p2-08-p2-09-doc-sync`
- `work/p2-08-p2-09-integration-verification`
- `work/p2-08-p2-09-local-acceptance-closeout`
- `work/p2-08a-auto-review-core`
- `work/p2-08b-auto-review-ai-api`
- `work/p2-09a-runtime-truth`
- `work/p2-09b-idempotency-mcp`
- `work/p2-09c-desktop-data`
- `work/p2-09d-desktop-ux-auto-review`
- `work/p2-10a-settings-governance-core`
- `work/p2-10a-settings-governance-doc-sync`
- `work/p2-10b-native-desktop-ui`
- `work/p2-10c-memory-workspace-ui`
- `work/p2-11a-windows-release-baseline`
- `work/p2-11b-runtime-sidecar-manager`
- `work/p2-12a-observation-first-ui`
- `work/repository-governance-cleanup`
- `work/windows-gui-low-token-validation`

Duplicate refs that clearly do not carry unique content include the extraction-hardening copy chain at `f7872aaf...`, hardware PR copies at `b85c1ff4...`, the PR60 backup/validation pair at `a90a18a6...`, and duplicate PR88 artifact/workbench refs.

### Physical branch deletion boundary

The connected GitHub action surface available in this execution supports branch creation/movement but does **not** expose Git ref deletion. Therefore this cleanup does not pretend that remote refs were deleted. Stale PRs are closed here; physical branch deletion remains a separate Git-ref operation. This limitation is recorded explicitly rather than silently claiming success.

Never delete:

- `master`
- `feat/sb0-work-fact-contract` while PR #106 is active
- any branch referenced by an ACTIVE acceptance task
- the currently authoritative acceptance report branch until its evidence has been superseded and preserved

## 6. Active PR interaction

PR #106 is based on an older master and may still contain documents removed by this cleanup. Before #106 is eventually merged, it must merge/rebase the cleaned master and resolve documentation conflicts so stale files are not resurrected.

## 7. Validation

Initial documentation commit `77740d8ee725fb2ff7e51cfd9cb9f8587d7f095f` changed only `docs/**` (57 files total: 54 deletions + 3 documentation updates).

CI results on that exact commit:

- `local-execution-handoff`: PASS
- `acceptance-doc-sync`: PASS
- MCP smoke: PASS
- browser capture smoke: PASS
- Obsidian plugin smoke: PASS
- Python 3.11 / 3.12 and Desktop smoke exposed two pre-existing stale UI-test contracts in unchanged files:
  - integration test still required `pending_review_count` / SHADOW copy in Attention even though the canonical page now reads `/api/work/pending-actions`;
  - observation-first smoke still required the old literal “每 4 秒自动更新” while Activity now uses the shared polling hook at 5000 ms.

The cleanup therefore updates those tests without weakening coverage: assertions now bind to the canonical Work Fact API, `PendingAction` DTO, explicit empty/error states, and actual polling intervals.

The next CI pass also exposed a stale TypeScript call-site contract: `AppPages` still passed removed `overview/onNavigate` props to `AttentionPage`, whose current contract is only `{ api, active }`. PR #107 removes only those obsolete props. This is a compile-contract repair; it does not change Attention runtime behavior or data authority.

A further Desktop smoke rerun exposed more presentation-coupled assertions in the same historical smoke: it required the source literal `5_000` and the obsolete copy “系统当前空闲 / 处理进度”. `CurrentWorkPanel` now uses `5000`, the empty state “当前没有进行中的工作”, and the canonical Work Fact projection fields “任务 / 事件 / 结果 / 下一步”. The smoke now validates those current contracts and the exact 5000 ms interval instead of obsolete presentation strings.

The next sequential smoke failure was also stale ownership: `codex-workspace-smoke.mjs` still expected project/session copy inside `CurrentWorkPanel`. The test now validates project/session ownership in `CodexWorkspacePage` and validates canonical Work Fact ownership in `CurrentWorkPanel`.

No Runtime, Vault, database, Qdrant, Memory authority, or owner-data code is changed.

Final validation must be read from CI on the updated cleanup head; no unexecuted result may be reported as PASS.

## 8. Rollback

Revert the cleanup commit on `chore/repository-deep-cleanup-20260919` or the eventual merge commit. All removed files remain recoverable from `ced1128e50d3b3758585573042ea6bcc6f315384` and earlier Git history.
