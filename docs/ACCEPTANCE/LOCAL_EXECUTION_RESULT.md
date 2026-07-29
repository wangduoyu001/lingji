# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> Codex 必须在任务单指定的报告分支更新本文件。聊天中的“完成了”不构成结果，只有远程报告分支中的本文件、最终报告、报告 Commit 和 PR 评论能够被重新读取，任务才算提交成功。
>
> 用户不负责填写、上传、推送、核对或解释本文件。

## 1. 当前回执

```yaml
task_id: PR60-OWNER-REACCEPTANCE-1C514877
status: PENDING
verdict: PENDING
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
task_instruction_commit: 9249dce0abe1fdd5b3274fe318c946c3c793d962
report_branch: acceptance/pr60-owner-1c514877
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_REACCEPTANCE_1c514877.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_PUBLIC_REACCEPTANCE_SUMMARY_1c514877.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_PUBLIC_REACCEPTANCE_HASHES_1c514877.txt
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

## 2. Codex 回填规则

最终回执必须把上面字段更新为真实值。

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

当 `status: COMPLETED` 时必须同时满足：

- `verdict` 为 PASS、FAIL 或 BLOCKED；
- `report_commit` 为远程可读取的 40 位 Git SHA；
- `cleanup_before: PASS`；
- `cleanup_after: PASS`；
- 所有 `remote_*_verified` 为 `true`；
- `pr_comment_verified: true`；
- `local_temp_root_absent: true`；
- `owner_observation` 为 PASS、FAIL 或 NOT_REQUIRED；
- `started_at` 和 `finished_at` 为带时区的 ISO 8601 时间；
- 报告分支 HEAD 必须等于 `report_commit`；
- 远程报告、公开证据和本回执必须能够通过 GitHub API 重新读取。

任何远程读取失败时：

```yaml
status: BLOCKED_SUBMISSION
verdict: BLOCKED
```

任何结束清理失败时不得写 `COMPLETED`。

## 3. 最终结果摘要

Codex 在报告分支提交时填写：

```text
自动测试：PENDING
真机测试：PENDING
主人观察：PENDING
阻塞缺陷：PENDING
未覆盖客户端：PENDING
Production 是否被污染：PENDING
主人配置是否保持：PENDING
临时垃圾是否清理：PENDING
远程报告是否复读成功：PENDING
```

## 4. 证据索引

只填写脱敏信息：

```text
最终报告：PENDING
公开摘要：PENDING
公开哈希：PENDING
PR 评论 URL：PENDING
远程分支 HEAD：PENDING
私有证据归档 SHA256：PENDING / NOT_RETAINED
```

禁止写入 Token、Authorization、API Key、私人聊天、真实数据库、完整本机路径、用户配置正文或未脱敏截图。