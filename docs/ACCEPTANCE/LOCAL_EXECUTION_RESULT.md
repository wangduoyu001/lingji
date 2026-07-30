# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> Codex 必须在任务单指定的报告分支更新本文件。聊天中的“完成了”不构成结果，只有远程报告分支中的本文件、最终报告、报告内容 Commit 和 PR 评论能够被重新读取，任务才算提交成功。
>
> 用户不负责填写、上传、推送、核对或解释本文件。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-1C514877
status: BLOCKED_SUBMISSION
verdict: BLOCKED
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
task_instruction_commit: 715c8fe73126227beb9a5378e5fd8e63d742941c
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_branch: acceptance/pr60-memory-quality-trial-1c514877
report_commit: cb24c542306bf06bd3918a1dae18afed6e0712f8
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_1c514877.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_1c514877.txt
day0_result: FAIL
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
owner_config_preserved: PASS
cleanup_before: PASS
cleanup_after: BLOCKED_POST_CLEANUP
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: false
owner_observation: FAIL
started_at: 2026-07-30T21:02:59+08:00
finished_at: 2026-07-30T21:05:37+08:00
```

## 2. Codex 回填规则

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

阶段字段允许：

```text
PASS
FAIL
BLOCKED
NOT_RUN
```

### Day 0 规则

- `day0_result` 不是 PASS 时，`stage1_result` 和 `stage2_result` 必须为 NOT_RUN；
- Day 0 未 PASS 时不得把 `real_data_authorized` 写为 true；
- Day 0 FAIL 或 BLOCKED 时，最终 verdict 不得为 PASS。

### 真实数据规则

- 进入 Stage 1 前必须 `real_data_authorized: true`；
- PASS 报告至少执行 20 道质量题；
- 主人至少抽查 10 题；
- PASS 要求 `quality_score_percent >= 90`；
- PASS 要求 `source_accuracy_percent >= 95`；
- PASS 要求 `false_positive_percent <= 5`；
- PASS 要求 `codex_mcp_success_percent >= 95`；
- PASS 要求 `duplicate_formal_content_count = 0`；
- PASS 要求 `production_pollution_count = 0`；
- PASS 要求 `owner_config_preserved: PASS`。

### 完成规则

当 `status: COMPLETED` 时必须同时满足：

- `verdict` 为 PASS、FAIL 或 BLOCKED；
- `task_instruction_commit` 为远程可读取的 40 位 Git SHA；
- `report_commit` 为第一次成功推送且远程可读取的“报告正文 + 公开证据”Commit；
- 最终回执 Commit 可以晚于 `report_commit`；
- `cleanup_before: PASS`；
- `cleanup_after: PASS`；
- 所有 `remote_*_verified` 为 `true`；
- `pr_comment_verified: true`；
- `local_temp_root_absent: true`；
- `owner_observation` 为 PASS、FAIL 或 NOT_REQUIRED；
- `started_at` 和 `finished_at` 为带时区的 ISO 8601 时间；
- 报告分支最终 HEAD 包含 `report_commit` 和当前回执最终版本；
- 远程报告、公开证据和本回执能够通过 GitHub API 重新读取。

任何远程读取失败时：

```yaml
status: BLOCKED_SUBMISSION
verdict: BLOCKED
```

任何结束清理失败时不得写 `COMPLETED`。

## 3. 主人检查点

Codex 回填：

```text
Checkpoint A 安装与首次打开：PENDING
Checkpoint B Codex 真实连接：PENDING
Checkpoint C 候选批准与拒绝：PENDING
Checkpoint D Windows 重启后：PENDING
Checkpoint E 质量题抽查：PENDING
```

Codex不得替主人填写肉眼、理解程度或真实资料正确性结论。

## 4. 最终结果摘要

```text
自动测试：PASS
Day 0：FAIL
Stage 1：NOT_RUN
Stage 2：NOT_RUN
质量题：0
主人抽查：0
quality_score：NOT_RUN
source_accuracy：NOT_RUN
false_positive_rate：NOT_RUN
Codex MCP 成功率：NOT_RUN
阻塞缺陷：D0-UX-001, D0-CODEX-002
未覆盖数据源或客户端：真实 Codex、Claude Code、WorkBuddy / CodeBuddy；Stage 1/2 未运行
Production 是否被污染：0 (executed scope)
主人配置是否保持：PASS
临时垃圾是否清理：BLOCKED_POST_CLEANUP（宿主策略拒绝对验收临时目录执行递归删除）
远程报告是否复读成功：PASS（首次报告 Commit 已复读；本次最终回执待推送后复读）
```

## 5. 证据索引

只填写脱敏信息：

```text
最终报告：docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md
公开摘要：docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_1c514877.json
公开哈希：docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_1c514877.txt
PR 评论 URL：https://github.com/wangduoyu001/lingji/pull/60#issuecomment-5131166762
远程分支最终 HEAD：待本次最终回执推送
报告内容 Commit：cb24c542306bf06bd3918a1dae18afed6e0712f8
问题集摘要 SHA256：PENDING / NOT_RUN
私有证据归档 SHA256：PENDING / NOT_RETAINED
```

禁止写入真实剧本正文、私人聊天、Vault 正文、数据库内容、Token、Authorization、API Key、完整本机路径、用户配置正文或未脱敏截图。
