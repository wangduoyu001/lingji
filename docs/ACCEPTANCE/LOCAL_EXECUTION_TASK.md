# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务。不得从旧聊天、旧报告、本机残留目录或旧 Artifact 推断额外要求。

## 1. 当前任务元数据

```yaml
task_id: PR60-MASTER-SYNC-A90A18A6
status: ACTIVE
execution_mode: BRANCH_SYNC_AND_ARTIFACT_PREPARATION
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: a90a18a66ffba157c01367ba70bfec98f58798e2
artifact_name: PENDING_EXACT_HEAD_CI
artifact_id: PENDING
report_branch: acceptance/pr60-master-sync-a90a18a6
report_path: docs/TEST_REPORTS/PR60_MASTER_SYNC_a90a18a6.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MASTER_SYNC_SUMMARY_a90a18a6.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MASTER_SYNC_HASHES_a90a18a6.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
sync_source_branch: sync-base/pr60-master-4eb3a107
sync_source_commit: 4eb3a1078ef85ef2691d85e13026ad66b2a4f390
validated_release_report_head: 6dc079c552628998e997f613c51c2c05d9202053
previous_blocked_report_head: 34770d942351d07cca51974c12ccc47a3dea34d3
```

## 2. 为什么改用固定同步源

上一版任务要求：

```text
origin/master = c349131d1aa22d2630b57df4d01d43a1088a1529
```

但任务单和回执本身提交到 `master` 后，`master` 已前进到 `4eb3a107...`，因此 Codex 正确返回 `BLOCKED_WRONG_IDENTITY`。

若继续把任务单里的 SHA 改成当前 `master` 后再提交回 `master`，提交动作又会生成新的 SHA，形成自引用循环。

本任务因此使用不可移动的固定同步源：

```text
origin/sync-base/pr60-master-4eb3a107
4eb3a1078ef85ef2691d85e13026ad66b2a4f390
```

后续任务文档可以继续推动 `master`，但不会改变需要合入产品分支的固定治理快照。

## 3. 已确认基线

产品提交 `a90a18a6` 已完成代码发布链验证：

```text
完整 release：PASS（15 suites）
Python 全量：PASS
Desktop smoke/build：PASS
Rust/Tauri：PASS
本地 release 身份与哈希：PASS
清理与远程复读：PASS
```

本任务不是 Day 0，不安装灵机，不启动 UI，不读取真实数据。

## 4. 开始前门禁

拉取远程引用并确认：

```text
origin/feature/unified-ai-memory-connectors = a90a18a66ffba157c01367ba70bfec98f58798e2
origin/sync-base/pr60-master-4eb3a107 = 4eb3a1078ef85ef2691d85e13026ad66b2a4f390
```

还必须确认：

```text
git merge-base --is-ancestor 4eb3a1078ef85ef2691d85e13026ad66b2a4f390 origin/master
```

结果必须为成功。

注意：**不得要求 `origin/master` 当前 HEAD 等于 `4eb3a107...`。** 当前 `master` 会包含本任务单和回执的后续提交，这是预期行为，不构成身份错误。

若产品分支或固定同步源分支身份变化，立即 `BLOCKED_WRONG_IDENTITY`。

## 5. 隔离与备份

使用唯一临时根：

```text
D:\codex\LingJiSync\PR60-a90a18a6
```

创建并远程确认备份分支：

```text
backup/pr60-pre-master-sync-a90a18a6
→ a90a18a66ffba157c01367ba70bfec98f58798e2
```

不得 force-push，不得覆盖已有不同身份的备份分支。

## 6. 合并规则

从产品分支执行：

```text
git merge --no-ff origin/sync-base/pr60-master-4eb3a107
```

不得执行：

```text
git merge origin/master
rebase
squash 107 个产品提交
force-push
```

### 预期冲突

根据远程比较，双方已知同时修改的治理文件为：

```text
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
```

解决原则：

- 保留固定同步源中的全部治理、清理和任务历史；
- 保留产品分支中的 PR #60 UI、连接器、Embedding/Qdrant 和 bundle gate 记录；
- 不删除或改写历史结论；
- 不把旧 `d69874af / Artifact 8762312712` 恢复为可执行身份。

固定同步源还包含旧版任务单和回执。合并冲突时以历史完整为原则，不得把旧任务重新激活。当前真正可执行任务始终以远程最新 `master` 中本文件为准。

若出现其他产品代码冲突，停止并报告，不得猜测处理。

## 7. 合并后验证

先确认：

```text
git diff --check = PASS
git status = clean
无冲突标记
新 Head 同时包含 a90a18a6 与 4eb3a107
产品代码文件相对 a90a18a6 无意外删除
固定同步源治理文件全部存在
```

运行：

```powershell
python -m pytest -q tests/test_acceptance_sync.py tests/test_local_execution_handoff.py tests/test_cleanup_acceptance_workspace.py tests/test_brain_status_e2e.py tests/test_validate_frontend_dist.py
python scripts/check_acceptance_sync.py

Set-Location desktop\lingji-control
npm ci --no-audit --no-fund
npm run test:smoke
npm run build
Set-Location ..\..
```

`python scripts/check_local_execution_handoff.py` 必须在远程最新 `master` 的任务文档副本上运行，不能使用固定同步源中已经冻结的旧任务文本来判断当前任务。

不得删除、skip、弱化或改写测试。本机不重跑完整15套 release；新 Head 由远程 CI 和 Windows 打包重新验证。

## 8. 推送与远程确认

将 merge commit 推送到：

```text
feature/unified-ai-memory-connectors
```

远程确认：

- PR #60 Head 变为新40位 SHA；
- 新 Head 包含父提交 `a90a18a6` 和固定同步源 `4eb3a107`；
- PR 不再显示 conflict；
- PR 保持 Draft；
- GitHub Actions 已针对新 Head 启动；
- 不复用旧 Artifact `8762312712`。

`master` 在 `4eb3a107` 之后的变化只允许是任务交接和结果回执文件；这些提交不属于本次产品同步源，也不要求进入产品 Head。

## 9. 报告与回执

更新现有报告分支：

```text
acceptance/pr60-master-sync-a90a18a6
```

提交并远程复读：

```text
docs/TEST_REPORTS/PR60_MASTER_SYNC_a90a18a6.md
docs/TEST_REPORTS/evidence/PR60_MASTER_SYNC_SUMMARY_a90a18a6.json
docs/TEST_REPORTS/evidence/PR60_MASTER_SYNC_HASHES_a90a18a6.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

报告必须保留首次 `BLOCKED_WRONG_IDENTITY` 历史，并追加本次固定同步源重试结果，不得覆盖旧证据。

## 10. 清理

远程报告复读成功后：

- 删除本任务 worktree、临时依赖和任务目录；
- 解除 worktree 登记；
- 确认没有 LingJi 进程、8766/8767 监听或孤儿 MCP；
- `D:\codex\LingJiSync` 共享父目录允许保留。

## 11. PASS条件

```text
固定同步源身份 PASS
产品备份分支 PASS
标准非快进 merge PASS
仅预期治理冲突或零冲突
聚焦测试 PASS
Desktop smoke/build PASS
新 Head 推送 PASS
PR conflict 消失
远程 Actions 已启动
报告与回执远程可读
任务目录清理 PASS
```

CI和正式 Windows Artifact 的最终结论由 ChatGPT 在新 Head 推送后继续核验。

## 12. 最终回复

```text
PR60 固定源同步完成
task_id: PR60-MASTER-SYNC-A90A18A6
结论: PASS / FAIL / BLOCKED
源产品 Commit: a90a18a66ffba157c01367ba70bfec98f58798e2
固定同步源: sync-base/pr60-master-4eb3a107
固定同步源 Commit: 4eb3a1078ef85ef2691d85e13026ad66b2a4f390
新产品 Head: <40位 SHA>
合并父提交: <a90a18a6>, <4eb3a107>
PR conflict: 已消失 / 仍存在
远程 Actions: 已启动 / 未启动
报告分支: acceptance/pr60-master-sync-a90a18a6
报告 Commit: <40位 SHA>
本地清理: PASS
```
