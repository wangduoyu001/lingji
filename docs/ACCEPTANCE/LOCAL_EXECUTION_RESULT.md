# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> Codex 必须在任务单指定的报告分支更新本文件。聊天中的“完成了”不构成结果，只有远程报告、公开证据、结果回执、报告 Commit 和 PR 评论能够被重新读取，任务才算提交成功。
>
> 用户不负责填写、上传、推送、核对或解释本文件。

## 1. 当前回执

```yaml
task_id: PR60-GUIDED-MEMORY-TRIAL-D69874AF
status: PENDING
verdict: PENDING
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
task_instruction_commit: PENDING
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_branch: acceptance/pr60-guided-memory-trial-d69874af
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR60_GUIDED_MEMORY_TRIAL_d69874af.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_GUIDED_MEMORY_TRIAL_SUMMARY_d69874af.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_GUIDED_MEMORY_TRIAL_HASHES_d69874af.txt
day0_result: NOT_RUN
stage1_result: NOT_RUN
stage2_result: NOT_RUN
semantic_retrieval_result: NOT_RUN
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
legacy_cleanup: NOT_RUN
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

## 2. 阶段和判定规则

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

规则：

- Day 0 不是 PASS 时，Stage 1 和 Stage 2 必须为 NOT_RUN；
- Day 0 未 PASS 时不得授权或读取真实数据；
- 进入 Stage 1 前必须 `real_data_authorized: true`；
- 最终 PASS 要求 `semantic_retrieval_result: PASS`；
- UI 能解释向量问题但本机尚未激活时，写 `semantic_retrieval_result: BLOCKED`，最终 verdict 不得为 PASS；
- PASS 至少执行 20 道题，主人至少抽查 10 题；
- PASS 要求 quality score ≥ 90、source accuracy ≥ 95、false positive ≤ 5；
- PASS 要求 Codex MCP 成功率 ≥ 95；
- PASS 要求重复正式内容和 Production 污染均为 0；
- PASS 要求主人配置保持不变。

## 3. 主人检查点

Codex只能记录主人给出的真实结论：

```text
Checkpoint A 主动引导与首次理解：PENDING
Checkpoint B 当前 Codex 主机真实 MCP 调用：PENDING
Checkpoint C 候选批准与拒绝：PENDING
Checkpoint D Windows 重启后：PENDING
Checkpoint E 质量题抽查：PENDING
```

Checkpoint A 必须包含：

```text
扫描后 5 秒内是否知道唯一下一步
是否能区分发现目录 / 配置写入 / 命令可用 / 真实测试通过
是否能看懂导入范围和未读取边界
是否能一眼看到 Embedding / Qdrant 的具体问题
```

Codex不得替主人填写肉眼、理解程度或真实资料正确性。

## 4. 完成规则

当 `status: COMPLETED` 时必须同时满足：

- `task_instruction_commit` 为远程可读取的 40 位 SHA；
- `report_commit` 为远程可读取的报告正文和公开证据 Commit；
- `cleanup_before: PASS`；
- `cleanup_after: PASS`；
- 所有 `remote_*_verified` 为 true；
- `pr_comment_verified: true`；
- `local_temp_root_absent: true`；
- `owner_observation` 为 PASS、FAIL 或 NOT_REQUIRED；
- `started_at` 和 `finished_at` 为带时区 ISO 8601；
- 报告分支最终 HEAD 包含 report_commit 和本回执最终版本；
- 远程报告、公开证据和本回执可通过 GitHub API 重新读取。

远程复读失败：

```yaml
status: BLOCKED_SUBMISSION
verdict: BLOCKED
```

结束清理失败不得写 `COMPLETED`。

## 5. 最终结果摘要

```text
自动测试：PENDING
主动引导重测：PENDING
Day 0：NOT_RUN
Stage 1：NOT_RUN
Stage 2：NOT_RUN
语义检索：NOT_RUN
质量题：0
主人抽查：0
quality_score：NOT_RUN
source_accuracy：NOT_RUN
false_positive_rate：NOT_RUN
Codex MCP 成功率：NOT_RUN
阻塞缺陷：PENDING
未覆盖数据源或客户端：PENDING
Production 是否被污染：PENDING
主人配置是否保持：PENDING
旧验收垃圾是否清理：PENDING
本轮临时垃圾是否清理：PENDING
远程报告是否复读成功：PENDING
```

## 6. 证据索引

只填写脱敏信息：

```text
最终报告：PENDING
公开摘要：PENDING
公开哈希：PENDING
PR 评论 URL：PENDING
远程分支最终 HEAD：PENDING
报告内容 Commit：PENDING
问题集摘要 SHA256：PENDING / NOT_RUN
清理预览摘要 SHA256：PENDING
私有证据归档 SHA256：PENDING / NOT_RETAINED
```

禁止写入真实剧本正文、私人聊天、Vault 正文、数据库内容、Token、Authorization、API Key、完整本机路径、用户配置正文或未脱敏截图。