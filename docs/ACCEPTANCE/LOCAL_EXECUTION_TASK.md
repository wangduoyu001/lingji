# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务。不得从旧聊天、旧报告或本机残留推断额外要求。

## 1. 当前任务元数据

```yaml
task_id: PR60-CODE-RELEASE-VALIDATION-A90A18A6
status: ACTIVE
execution_mode: CODE_RELEASE_VALIDATION_FINALIZATION
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: a90a18a66ffba157c01367ba70bfec98f58798e2
report_branch: acceptance/pr60-code-release-validation-a90a18a6
report_path: docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_SUMMARY_a90a18a6.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_HASHES_a90a18a6.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
recovery_only: true
release_rerun_forbidden: true
validated_release_suites: 15
validated_product_commit: a90a18a66ffba157c01367ba70bfec98f58798e2
current_report_head: 808bcfb30aff04ac1cd05ce9fcf2fe3c48eaf59d
cleanup_fix_commit: 0f9bb6421bceea815bfe8c5d26b59728c0f49fb6
```

## 2. 已确认事实

以下结果已经远程可读，不得重跑或改写：

```text
完整 release：PASS（15 suites）
精确修复测试：PASS（11 passed）
Python 全量：PASS（583 passed，10 skipped，3 subtests）
Desktop smoke：PASS（22 scripts）
干净 build：PASS
重复 build：PASS
frontend dist validator：PASS
Rust/Tauri：PASS（9 passed）
本地 release 身份与哈希：PASS
真实数据读取：0
安装或 UI 启动：0
```

本轮恢复还已证明：

```text
清理工具聚焦测试：PASS（10 passed）
原任务临时根 D:\codex\LingJiValidation\PR60-CODE-a90a18a6：已删除
local_temp_root_absent：true
远程报告、回执、摘要、哈希和 PR #60 评论：可读
```

## 3. 纠正后的清理合同

上版任务错误要求删除：

```text
D:\codex\LingJiRecovery
```

该目录是外部共享恢复根，不是本任务临时根。安全策略拒绝删除它是正确行为，不构成任务失败。

最终清理只要求：

1. 任务专属恢复 worktree `D:\codex\LingJiRecovery\PR60-CODE-a90a18a6-report` 不存在；
2. 原任务临时根 `D:\codex\LingJiValidation\PR60-CODE-a90a18a6` 不存在；
3. 对应 Git worktree 登记已解除；
4. 没有任务创建的进程、8766/8767 监听或孤儿 MCP；
5. 相邻目录和主人数据未变化。

共享父目录 `D:\codex\LingJiRecovery` 即使为空也允许保留。不得再次尝试删除该共享根，不得放宽清理工具去删除根目录。

## 4. 本轮只允许执行

Codex 只需：

1. 拉取最新 `master` 并确认本任务单；
2. 确认任务专属目录均不存在，Git worktree登记已解除；
3. 不再执行任何删除操作；
4. 在现有报告分支更新原报告、公开摘要、公开哈希和结果回执；
5. 将最终结论改为 `PASS`，并注明共享恢复父目录保留属于正确安全边界；
6. 更新 PR #60 评论；
7. 远程复读报告分支、报告、摘要、哈希、结果回执和评论。

## 5. 绝对禁止

不得重新执行：

```text
Python 全量测试
Desktop smoke 或 build
Rust/Tauri 测试
validate.ps1 -Mode release
重新生成本地安装包
安装或启动 LingJi
读取或导入真实资料
删除 D:\codex\LingJiRecovery 共享父目录
```

不得修改产品分支、产品 Commit、原测试结果或原产物哈希。

## 6. 最终回执

最终回执应写为：

```yaml
status: COMPLETED
verdict: PASS
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: true
owner_observation: NOT_REQUIRED
```

报告必须说明：

```text
原任务根与任务专属恢复 worktree已清理。
外部共享恢复父目录允许保留，不属于任务垃圾。
产品 Commit a90a18a6 的代码发布链最终结论为 PASS。
这不是正式 GitHub Artifact，尚未进入安装、Day 0 或 UI 验收。
```

## 7. 最终回复

```text
代码发布链验证完成
task_id: PR60-CODE-RELEASE-VALIDATION-A90A18A6
最终结论: PASS
产品 Commit: a90a18a66ffba157c01367ba70bfec98f58798e2
完整 release: PASS（沿用15 suites，未重跑）
报告分支: acceptance/pr60-code-release-validation-a90a18a6
报告分支最终 HEAD: <40位 SHA>
远程确认: PASS
本地任务目录清理: PASS
共享恢复父目录: 保留（符合安全边界）
```
