# LingJi 本机执行任务单

> **当前状态：ACTIVE / Task8E Mac Experience Candidate / NOT_FINAL_RELEASE。**
>
> 本任务经主人明确授权，用于尽快进入真实 macOS 发布候选与主人实际体验；它不绕过
> Task7 质量测量阻塞，不构成 Phase 1、100k、release gate 或最终发布结论。

## 1. 当前任务

```yaml
task_id: TASK8E-MAC-EXPERIENCE-FFC2D885
status: ACTIVE
verdict: IN_PROGRESS
execution_mode: MACOS_ARM64_RELEASE_CANDIDATE_OWNER_EXPERIENCE
repository: wangduoyu001/lingji
product_pr: none
product_branch: codex/phase1-automatic-memory
product_commit: ffc2d8851dc91b5f09b14d31a34c1e6988358933
base_commit: ffc2d8851dc91b5f09b14d31a34c1e6988358933
artifact_name: lingji-macos-arm64-local-task8e
artifact_id: LOCAL-TASK8E-FFC2D885
artifact_path: /tmp/LingJiAcceptance/TASK8E-ffc2d8851/artifact
app_path: /Applications/灵机.app
installer_path: /tmp/LingJiAcceptance/TASK8E-ffc2d8851/artifact/dmg
acceptance_root: /tmp/LingJiAcceptance/TASK8E-ffc2d8851
acceptance_data_root: /tmp/LingJiAcceptance/TASK8E-ffc2d8851/data
report_branch: acceptance/task8e-mac-experience-ffc2d885
report_path: docs/TEST_REPORTS/MACOS_TASK8E_EXPERIENCE_CANDIDATE_ffc2d885.md
public_summary_path: docs/TEST_REPORTS/evidence/TASK8E_MAC_EXPERIENCE_SUMMARY_ffc2d885.json
public_hashes_path: docs/TEST_REPORTS/evidence/TASK8E_MAC_EXPERIENCE_HASHES_ffc2d885.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
required_ci: desktop frontend/build and macOS sidecar/Tauri local release candidate checks
quality_blocker: TASK7 BLOCKED_AT_MEASUREMENT_CAP; no memory-quality/100k/release-gate claim permitted
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
production_data_access: forbidden
production_vault_write: forbidden
same_sha_artifacts_required: false
artifact_is_final_release: false
```

## 2. Scope and exact commands

Only the exact product commit above may be built. Do not run the Task7-blocked `release` gate,
100k benchmark, or quality trial. Allowed candidate checks are:

```text
cd desktop/lingji-control && npm run test:macos-release
cd desktop/lingji-control && npm run build
cd desktop/lingji-control && npm run test:work-fact
cd desktop/lingji-control && npm run test:memory-sources
cd desktop/lingji-control && npm run test:e2e:memory
cd desktop/lingji-control && npm run build:sidecar:macos
cd desktop/lingji-control && npx tauri build --config src-tauri/tauri.sidecar.conf.json --bundles app --target aarch64-apple-darwin
cd desktop/lingji-control && npx tauri bundle --config src-tauri/tauri.sidecar.conf.json --bundles dmg --target aarch64-apple-darwin
```

The candidate must use `/tmp/LingJiAcceptance/TASK8E-ffc2d8851/data/acceptance` as its
configured workspace/data root through the Desktop bootstrap UI or equivalent documented
bootstrap path. It must never connect to Production, the owner's Vault, or existing owner
credentials/data.

## 3. Start/end cleanup and rollback

- Before start, remove only the prior clearly task-scoped `/tmp/LingJiAcceptance/TASK8E-ffc2d8851`
  root if present; stop only identified LingJi PIDs and release 8766/8767. Do not use global
  process kills. Do not touch Production/Vault or unknown Acceptance roots.
- Record the old `/Applications/灵机.app` bundle and whole-bundle move it to the task root
  backup before installing. Do not overlay-copy into the app bundle.
- Keep the candidate UI open after Codex self-check; do not close it before owner confirmation.
- If candidate installation/runtime fails, stop only its identified runtime, release the ports,
  remove only the failed candidate bundle, restore the old whole bundle, and preserve minimal
  failure evidence.
- After owner confirmation and remote report verification, delete only candidate artifact,
  fixture, checkpoint, ordinary successful logs/screenshots, temporary config backup, and task
  root. Keep the report, redacted public evidence, hashes, and owner-requested failure evidence.

## 4. Codex self-check and owner observation

Codex must verify PID/instance identity, authenticated `127.0.0.1:8766` health, runtime state,
arm64 binaries, strict codesign, DataRoot/workspace isolation, and the visible navigation and
buttons it actually clicks. Unclicked controls remain `NOT_TESTED`.

Owner must judge only the machine-dependent experience: first-open next step, what LingJi did
or took over, Work/Attention/Memory provenance, loading/error/unknown honesty, narrow window,
absence of black console windows, and window recovery. Owner confirmation is required before
any final PASS, merge, or release claim.

## 5. Known blocker and rollback boundary

Task7 remains `BLOCKED_AT_MEASUREMENT_CAP`; this candidate may expose existing UI/runtime behavior
for observation but must not claim memory quality, measured RAG, scale, final release, or Phase1
completion. No product-code change is authorized in this task. A failure is evidence, not a reason
to weaken assertions or alter the acceptance standard.
