# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> 当前任务先执行 Day 0。只有 Day 0 与主人检查点全部 PASS，并获得明确授权后，才允许进入真实资料 Stage 1。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-3E24E65C
status: PENDING
verdict: PENDING
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 3e24e65ce12bfa22b5c9193d65500648ebf45729
task_instruction_commit: PENDING
report_branch: acceptance/pr60-memory-quality-trial-3e24e65c
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_3e24e65c.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_3e24e65c.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_3e24e65c.txt
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
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
day0_result: NOT_RUN
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
owner_config_preserved: NOT_RUN
artifact_name: lingji-windows-0.1.0-3e24e65c
artifact_id: 8820695386
artifact_zip_sha256: 649de2e03bde0ec491f8c828fdfac73d1a9539877c72ecd5199c7be407ee0e98
installer_sha256: 21d87149844b8fd7ccf4d8e8b05923bbccf1338573aa6e189202571ef769caa1
portable_exe_sha256: bcb1af32c1dbcd9d0d25147c0f3bc11e5835ef9025d121a7cc5e7dfd0b3b9fc0
sidecar_exe_sha256: 866c80420b99ff7935814755957e4bbf7b8df2c7492063db0af3ae0fffd7a489
manifest_sha256: 518a0ec991b064704e8d55a3999451f32c22a6225021370cd0917c699b58466c
```

## 2. 当前阶段

```text
Day 0：NOT_RUN
主人检查点 A-F：NOT_RUN
真实资料授权：false
Stage 1：NOT_RUN
Stage 2：NOT_RUN
```

在主人明确授权前，真实资料读取数必须保持0。

PR #60 在验收控制文档继续更新后可能显示落后或文档冲突。这不改变固定产品 Head、Artifact和本次Day 0身份，也不允许在验收过程中再次同步产品分支。最终验收完成后再做一次合并前文档同步。

## 3. 已固定身份

```text
产品 Head：3e24e65ce12bfa22b5c9193d65500648ebf45729
Artifact：lingji-windows-0.1.0-3e24e65c
Artifact ID：8820695386
Artifact ZIP SHA256：649de2e03bde0ec491f8c828fdfac73d1a9539877c72ecd5199c7be407ee0e98
Installer SHA256：21d87149844b8fd7ccf4d8e8b05923bbccf1338573aa6e189202571ef769caa1
Portable SHA256：bcb1af32c1dbcd9d0d25147c0f3bc11e5835ef9025d121a7cc5e7dfd0b3b9fc0
Sidecar SHA256：866c80420b99ff7935814755957e4bbf7b8df2c7492063db0af3ae0fffd7a489
Manifest SHA256：518a0ec991b064704e8d55a3999451f32c22a6225021370cd0917c699b58466c
```

旧 Artifact `8723868744`、`8762312712` 禁止使用。

## 4. Day 0 待验证

```text
前置清理：NOT_RUN
Artifact 下载与哈希：NOT_RUN
覆盖安装：NOT_RUN
首次启动与非C盘 acceptance DataRoot：NOT_RUN
无黑窗：NOT_RUN
唯一下一步：NOT_RUN
主动发现与授权边界：NOT_RUN
Codex配置/命令/真实连接三层状态：NOT_RUN
真实 Codex MCP 调用：NOT_RUN
Embedding/Qdrant详细诊断：NOT_RUN
候选批准/拒绝边界：NOT_RUN
Core/Sidecar三轮重启：NOT_RUN
Desktop重启：NOT_RUN
Windows重启恢复：NOT_RUN
Production污染：0
真实资料读取：0
```

## 5. 主人检查点

```text
Checkpoint A：NOT_RUN
Checkpoint B：NOT_RUN
Checkpoint C：NOT_RUN
Checkpoint D：NOT_RUN
Checkpoint E：NOT_RUN
Checkpoint F：NOT_RUN
```

Codex到达检查点后应把状态写为 `RUNNING / PENDING`，保持 `real_data_authorized: false`，并等待主人反馈。不得提前将整个任务写为 PASS。

## 6. Stage 1 质量指标

只有获得主人明确授权后才填写：

```text
质量题总数：0 / >=20
主人抽查：0 / >=10
质量分：0 / >=90%
来源准确率：0 / >=95%
误报率：0 / <=5%
Codex MCP成功率：0 / >=95%
重复正式内容：0
Production污染：0
主人配置保留：NOT_RUN
```

## 7. 最终状态规则

允许：

```text
status: PENDING / RUNNING / COMPLETED / BLOCKED_SUBMISSION
verdict: PENDING / PASS / FAIL / BLOCKED
```

整个任务最终 PASS 必须同时满足：

- Day 0 PASS；
- 主人检查点 A-F PASS；
- 主人明确授权真实资料；
- Stage 1 PASS；
- 质量阈值全部满足；
- Production污染为0；
- 清理与远程复读全部PASS。

Day 0 PASS 但尚未授权 Stage 1 时，状态只能保持 `RUNNING / PENDING`。

## 8. 证据索引

```text
最终报告：PENDING
公开摘要：PENDING
公开哈希：PENDING
PR #60 评论：PENDING
报告分支最终 HEAD：PENDING
```

禁止提交安装包、数据库、Token、私人正文、完整真实路径清单、node_modules、dist或未脱敏日志。
