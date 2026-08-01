# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务，不得从聊天、旧报告、本机残留目录或旧 Artifact 推断任务。

## 1. 当前任务元数据

```yaml
task_id: PR60-CODE-RELEASE-VALIDATION-A90A18A6
status: ACTIVE
execution_mode: CODE_RELEASE_VALIDATION
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: a90a18a66ffba157c01367ba70bfec98f58798e2
artifact_name: NOT_APPLICABLE_PENDING_NEW_ARTIFACT
artifact_id: NOT_APPLICABLE
report_base: master
report_branch: acceptance/pr60-code-release-validation-a90a18a6
report_path: docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_SUMMARY_a90a18a6.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_HASHES_a90a18a6.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
recovery_only: true
release_rerun_forbidden: true
validated_release_suites: 15
blocked_report_head: e654b283c53b986aa64c2974c37d8c0cb231b366
cleanup_fix_commit: 0f9bb6421bceea815bfe8c5d26b59728c0f49fb6
```

## 2. 当前任务性质

这不是新的代码发布验证。产品 Commit `a90a18a6` 的完整发布链已经通过：

```text
精确修复测试：PASS（11 passed）
Python 全量：PASS（583 passed，10 skipped，3 subtests）
Desktop smoke：PASS（22 scripts）
干净 build：PASS
重复 build：PASS
frontend dist validator：PASS
Rust/Tauri：PASS（9 passed）
validate.ps1 -Mode release：PASS（15 suites）
本地 release 身份与哈希：PASS
真实数据读取：0
安装或 UI 启动：0
```

远程报告分支和阻塞回执已经可读。唯一剩余问题是旧清理工具不认识：

```text
D:\codex\LingJiValidation\PR60-CODE-a90a18a6
```

清理策略已在 PR #69 修复并合并到 `master`：

```text
0f9bb6421bceea815bfe8c5d26b59728c0f49fb6
```

## 3. 绝对禁止

Codex 不得重新执行：

```text
Python 全量测试
Desktop smoke 或 build
Rust/Tauri 测试
validate.ps1 -Mode release
重新生成本地安装包
安装或启动 LingJi
读取或导入真实资料
```

不得修改产品分支、产品 Commit、原测试结果或原产物哈希。不得把本次恢复称为新的产品验证。

## 4. 恢复工作区

原任务目录内包含 product 和 report worktree，Windows 无法在当前工作目录内部删除其父目录。因此必须从目标目录之外执行恢复。

1. 拉取远程最新 `master`，确认包含清理修复 Commit `0f9bb642...`。
2. 在目标目录之外创建一次性恢复 worktree，例如：

```text
D:\codex\LingJiRecovery\PR60-CODE-a90a18a6-report
```

3. 在该 worktree 检出远程现有报告分支：

```text
acceptance/pr60-code-release-validation-a90a18a6
```

4. 复读并记录：

```text
报告分支当前 HEAD: e654b283c53b986aa64c2974c37d8c0cb231b366
首次报告内容 Commit: 3aecaa06ec3a2a504a170fae28996b37854beb4c
Release validation: PASS
Cleanup after: BLOCKED_POST_CLEANUP
```

5. 不得覆盖或删除原报告证据。

## 5. 安全清理

必须从最新 `master` 的仓库副本、且当前目录位于目标根之外执行。

### A. 运行清理工具测试

只运行本次工具的聚焦测试：

```powershell
python -m pytest -q tests/test_cleanup_acceptance_workspace.py
```

预期：PASS。不得运行产品 release 套件。

### B. Dry-run

```powershell
python scripts/cleanup_acceptance_workspace.py `
  --task-id PR60-CODE-RELEASE-VALIDATION-A90A18A6 `
  --root D:\codex\LingJiValidation `
  --target D:\codex\LingJiValidation\PR60-CODE-a90a18a6
```

必须确认：

- 状态不是 `BLOCKED`；
- 目标只有一个直接子目录；
- 清单仅包含本任务创建的 product、report、release、依赖缓存、日志和证据；
- 不含 Vault、Production DataRoot、正式 Acceptance 数据、用户 AI 配置或相邻任务目录。

### C. 解除 worktree 占用

在执行删除前：

- 确认 product/report 分支所需提交均已远程存在；
- 从外部仓库执行 `git worktree remove` 或 `git worktree prune`，解除原目标内两个 worktree 的 Git 登记；
- 当前 shell、编辑器、Python、Node、Cargo 和日志进程不得占用目标目录；
- 不得结束无关进程。

### D. 显式执行

```powershell
python scripts/cleanup_acceptance_workspace.py `
  --task-id PR60-CODE-RELEASE-VALIDATION-A90A18A6 `
  --root D:\codex\LingJiValidation `
  --target D:\codex\LingJiValidation\PR60-CODE-a90a18a6 `
  --execute
```

执行后必须确认：

```text
cleanup_after: PASS
local_temp_root_absent: true
D:\codex\LingJiValidation\PR60-CODE-a90a18a6 不存在
相邻目录和主人数据未变化
```

工具若仍拒绝或操作系统返回占用/权限错误，继续 `BLOCKED_POST_CLEANUP`，不得强删或放宽安全规则。

## 6. 更新原报告，不创建新报告

清理成功后，在外部恢复 worktree中更新原分支：

```text
docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md
docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_SUMMARY_a90a18a6.json
docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_HASHES_a90a18a6.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

最终回执必须写为：

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

`report_commit` 保留首次成功推送的报告内容 Commit：

```text
3aecaa06ec3a2a504a170fae28996b37854beb4c
```

另在证据索引记录最终报告分支 HEAD。

## 7. PR #60 评论和远程复读

在 PR #60 添加或更新评论，明确：

```text
产品 Commit a90a18a6 的 15 套 release 验证此前已 PASS。
BLOCKED 仅由清理工具策略缺口造成。
PR #69 / master 0f9bb642 修复清理策略后，目标目录已安全删除。
最终代码发布链验证结论：PASS。
这不是正式 GitHub Artifact，也尚未进入 Day 0 或 UI 验收。
```

随后远程复读：

- 报告分支最终 HEAD；
- 首次报告内容 Commit；
- 最终报告正文；
- 公开摘要和哈希；
- 最终结果回执；
- PR #60 评论。

## 8. 恢复 worktree 清理

最终 push 和远程复读成功后：

- 删除外部恢复 worktree；
- 删除其空父目录；
- 确认没有孤儿 worktree、LingJi进程、8766/8767监听或 MCP；
- 不删除任何远程报告分支或历史证据。

## 9. 最终回复

```text
代码发布链验证恢复完成
task_id: PR60-CODE-RELEASE-VALIDATION-A90A18A6
最终结论: PASS / BLOCKED
产品 Commit: a90a18a66ffba157c01367ba70bfec98f58798e2
完整 release: PASS（沿用已验证的15 suites，不重跑）
清理修复 Commit: 0f9bb6421bceea815bfe8c5d26b59728c0f49fb6
报告分支: acceptance/pr60-code-release-validation-a90a18a6
首次报告内容 Commit: 3aecaa06ec3a2a504a170fae28996b37854beb4c
报告分支最终 HEAD: <40位 SHA>
远程确认: PASS
本地清理: PASS
```
