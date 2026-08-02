# LingJi local execution result receipt

## Current receipt

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-1860FA17
status: COMPLETED
verdict: FAIL
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 1860fa17c5de26b0ff4d54ace48158a6e343505a
task_instruction_commit: fa395bd2b028eb763bb71cee692b7cbb5d285720
report_branch: acceptance/pr60-memory-quality-trial-1860fa17
report_commit: 6e5478be35b127dd8a056c5ed9930b2eb14bbedf
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1860fa17.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_1860fa17.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_1860fa17.txt
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: true
owner_observation: PASS
started_at: 2026-08-02T08:38:00+08:00
finished_at: 2026-08-02T09:12:00+08:00
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
day0_result: FAIL
stage1_result: NOT_RUN
stage2_result: NOT_RUN
real_data_authorized: false
quality_questions_total: 0
owner_sample_questions: 0
quality_score_percent: 0
source_accuracy_percent: 0
false_positive_percent: 0
codex_mcp_success_percent: 0
duplicate_formal_content_count: 0
production_pollution_count: 0
owner_config_preserved: PASS
artifact_name: lingji-windows-0.1.0-1860fa17
artifact_id: 8830371064
artifact_zip_sha256: 8c4d5de5ed678063f70896bede94905c941962ba744a53de6537ee2714ab9e37
installer_sha256: ea109577ad86ee6b800973fbd5ca0c48cb0d0c7d98d5a67e82379a8b795c54a2
portable_exe_sha256: 51266810195ff8ed2d1ef9dc16b7144aef1db2bf2898a420894b3d0c352d068e
sidecar_exe_sha256: e6c005210a8b7e8c84bb7e4460110033c2aa8c026a1ea0da0fb49205cb0d72ae
manifest_sha256: fd80bfa9e2acb7cb158e6e936980e974a6abad51dc2e6b510a24ba9a96f6a240
build_metadata_sha256: 62bf86b9c2b666d27730de6ebb70b6e70bfdb515d57dab380810985b2ea3dfe7
```

## Day 0 stop condition

The fixed Artifact identity, isolated startup, and metadata-only candidate scan
passed. The one authorized synthetic ChatGPT job stayed `queued` for 40 seconds
with zero attempts. This is `D0-AUTO-IMPORT-QUEUE-STALLED`; Day 0 is FAIL and
all later stages remain NOT_RUN. No real data was read.
