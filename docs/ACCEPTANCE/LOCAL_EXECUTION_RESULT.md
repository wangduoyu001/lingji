# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> Codex 必须在任务单指定的报告分支更新本文件。聊天中的“完成了”不构成结果，只有远程报告、公开证据、结果回执、报告 Commit 和 PR 评论都能够重新读取，任务才算提交成功。
>
> 用户不负责填写、上传、推送、核对或解释本文件。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-D69874AF
status: PENDING
verdict: PENDING
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
task_instruction_commit: a9dc01d3bf8672b7bdf63c88ce1bd62b85a0f7bb
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_branch: acceptance/pr60-memory-quality-trial-d69874af
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_d69874af.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_d69874af.txt
day0_result: NOT_RUN
stage1_result: NOT_RUN
stage2_result: NOT_RUN
real_data_authorized: false
quality_questions_total: 0
owner_sample_questions: 0
quality_score_percent: NOT_RUN
source_accuracy_percent: NOT_RUN
false_positive_percent: NOT_RUN
codex_mcp_success_percent: NOT_RUN
duplicate_formal_content_count: NOT_RUN
production_pollution_count: NOT_RUN
owner_config_preserved: PENDING
cleanup_before: NOT_RUN
cleanup_after: NOT_RUN
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: PENDING
started_at: PENDING
finished_at: PENDING
```

## 2. 阶段规则

允许的 `status`：

```text
PENDING
RUNNING
COMPLETED
BLOCKED_SUBMISSION
```

允许的 `verdict`：

```text
PENDING
PASS
FAIL
BLOCKED
```

允许的阶段结果：

```text
PASS
FAIL
BLOCKED
NOT_RUN
```

- Day 0 不是 PASS 时，Stage 1 和 Stage 2 必须为 NOT_RUN；
- Day 0 未 PASS 时不得把 `real_data_authorized` 写为 true；
- 进入 Stage 1 前必须获得主人明确授权；
- Day 0 FAIL 或 BLOCKED 时最终 verdict 不得为 PASS。

## 3. PASS 硬门槛

PASS 至少要求：

```text
day0_result: PASS
stage1_result: PASS
real_data_authorized: true
quality_questions_total >= 20
owner_sample_questions >= 10
quality_score_percent >= 90
source_accuracy_percent >= 95
false_positive_percent <= 5
codex_mcp_success_percent >= 95
duplicate_formal_content_count = 0
production_pollution_count = 0
owner_config_preserved: PASS
```

还必须确认：

- 上次 `D0-UX-001` 回归通过；
- 上次 `D0-CODEX-002` 回归通过；
- Embedding / Qdrant 状态和下一步可理解；
- 主人五个检查点完成；
- 开始前和结束后清理通过；
- 远程报告、公开证据、回执和 PR 评论复读成功。

## 4. 完成规则

当 `status: COMPLETED` 时必须同时满足：

- `verdict` 为 PASS、FAIL 或 BLOCKED；
- `task_instruction_commit` 为远程可读取的 40 位 SHA；
- `report_commit` 为第一次成功推送且远程可读取的报告正文与公开证据 Commit；
- `cleanup_before: PASS`；
- `cleanup_after: PASS`；
- `remote_branch_verified`、`remote_commit_verified`、`remote_report_verified`、`remote_result_verified`、`pr_comment_verified` 和 `local_temp_root_absent` 全部为 true；
- `owner_observation` 为 PASS、FAIL 或 NOT_REQUIRED；
- `started_at` 和 `finished_at` 为带时区的 ISO 8601 时间；
- 报告分支最终 HEAD 包含报告 Commit 和当前回执最终版本。

远程读取失败时：

```yaml
status: BLOCKED_SUBMISSION
verdict: BLOCKED
```

结束清理失败时不得写 `COMPLETED`，必须记录 `BLOCKED_POST_CLEANUP` 和剩余相对路径。

## 5. 主人检查点

Codex 回填：

```text
Checkpoint A 安装、首页、唯一下一步与状态理解：PENDING
Checkpoint B Codex 命令、工具、真实连接与返回内容：PENDING
Checkpoint C 候选批准与拒绝：PENDING
Checkpoint D Windows 重启后：PENDING
Checkpoint E 质量题抽查：PENDING
```

Codex不得替主人填写肉眼、理解程度或真实资料正确性结论。

## 6. 最终结果摘要

```text
自动测试：PENDING
D0-UX-001 回归：NOT_RUN
D0-CODEX-002 回归：NOT_RUN
Embedding / Qdrant 诊断：NOT_RUN
Day 0：NOT_RUN
Stage 1：NOT_RUN
Stage 2：NOT_RUN
质量题：0
主人抽查：0
quality_score：NOT_RUN
source_accuracy：NOT_RUN
false_positive_rate：NOT_RUN
Codex MCP 成功率：NOT_RUN
阻塞缺陷：PENDING
Production 是否被污染：PENDING
主人配置是否保持：PENDING
临时垃圾是否清理：PENDING
远程报告是否复读成功：PENDING
```

## 7. 证据索引

只填写脱敏信息：

```text
最终报告：PENDING
公开摘要：PENDING
公开哈希：PENDING
PR 评论 URL：PENDING
远程分支最终 HEAD：PENDING
报告内容 Commit：PENDING
问题集摘要 SHA256：PENDING / NOT_RUN
私有证据归档 SHA256：PENDING / NOT_RETAINED
```

禁止写入真实剧本正文、私人聊天、Vault 正文、数据库内容、Token、Authorization、API Key、完整本机路径、用户配置正文或未脱敏截图。