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
source_master_commit: c349131d1aa22d2630b57df4d01d43a1088a1529
validated_release_report_head: 6dc079c552628998e997f613c51c2c05d9202053
```

## 2. 已确认基线

产品 Commit `a90a18a6` 已完成代码发布链验证：

```text
完整 release：PASS（15 suites）
Python 全量：PASS
Desktop smoke/build：PASS
Rust/Tauri：PASS
本地 release 身份与哈希：PASS
清理与远程复读：PASS
```

该结果证明源产品代码可发布，但不是正式 GitHub Artifact，也不能直接进入 Day 0。

PR #60 当前状态：

```text
Head：a90a18a66ffba157c01367ba70bfec98f58798e2
Base：master
相对 master：ahead 107 / behind 11
Merge base：715c8fe73126227beb9a5378e5fd8e63d742941c
状态：diverged / conflict
```

`master` 落后的11个提交只涉及验收治理、任务回执和安全清理工具。已知双方同时修改的文件只有：

```text
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
```

## 3. 任务目标

在隔离 worktree 中，把远程最新 `master` 合入 `feature/unified-ai-memory-connectors`，保留产品分支全部功能和 `master` 全部治理修复，生成新的精确产品 Head，并触发 GitHub CI与Windows Artifact流程。

本任务不是 Day 0，不安装灵机，不启动 UI，不读取真实数据。

## 4. 开始前门禁

1. 拉取远程最新 `master`、产品分支和本任务单。
2. 确认远程身份：

```text
origin/master = c349131d1aa22d2630b57df4d01d43a1088a1529
origin/feature/unified-ai-memory-connectors = a90a18a66ffba157c01367ba70bfec98f58798e2
```

若任一身份变化，立即 `BLOCKED_WRONG_IDENTITY`，不得自行套用旧方案。

3. 使用唯一临时根：

```text
D:\codex\LingJiSync\PR60-a90a18a6
```

4. 创建远程备份分支：

```text
backup/pr60-pre-master-sync-a90a18a6
```

该分支必须精确指向 `a90a18a6`，并远程复读确认。

## 5. 合并规则

从产品分支执行标准 merge：

```text
git merge --no-ff origin/master
```

不得 rebase、不得 squash 107个产品提交、不得 force-push覆盖历史。

### 唯一预期冲突

```text
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
```

解决原则：

- 保留 `master` 中全部治理、清理和任务交接历史；
- 保留产品分支中 PR #60 UI、连接器、Embedding/Qdrant、bundle gate 修复相关记录；
- 历史条目不得删除；
- 可按时间重新排序，但不得改写既有结论；
- 不把旧 `d69874af / Artifact 8762312712` 恢复为可执行身份。

若出现其他代码冲突，停止并报告，不得猜测解决。

## 6. 合并后必跑验证

先确认：

```text
git diff --check = PASS
git status = clean
无冲突标记
产品代码文件相对 a90a18a6 无意外删除
master新增治理文件全部存在
```

然后运行：

```powershell
python -m pytest -q tests/test_acceptance_sync.py tests/test_local_execution_handoff.py tests/test_cleanup_acceptance_workspace.py tests/test_brain_status_e2e.py tests/test_validate_frontend_dist.py
python scripts/check_acceptance_sync.py
python scripts/check_local_execution_handoff.py

Set-Location desktop\lingji-control
npm ci --no-audit --no-fund
npm run test:smoke
npm run build
Set-Location ..\..
```

预期：全部 PASS。不得删除、skip、弱化或改写测试。

本机不需要重跑完整15套 release；新的精确 Head 必须由远程 CI和Windows打包流程重新验证。

## 7. 推送与远程确认

1. 将 merge commit 推送到：

```text
feature/unified-ai-memory-connectors
```

2. 远程复读确认：

- PR #60 Head 已变为新的40位 SHA；
- 新 Head 同时包含父提交 `a90a18a6` 与 `c349131d...`；
- PR 不再显示 conflict；
- PR保持 Draft；
- GitHub Actions已针对新 Head启动；
- 不复用旧 Artifact 8762312712。

3. 更新 PR #60 评论，写明：

```text
代码发布链源基线 a90a18a6 已 PASS。
最新 master 已通过非快进 merge 合入。
新精确 Head 等待远程 CI 和正式 Windows Artifact。
Day 0 尚未开始。
```

## 8. 报告与回执

在报告分支提交：

```text
docs/TEST_REPORTS/PR60_MASTER_SYNC_a90a18a6.md
docs/TEST_REPORTS/evidence/PR60_MASTER_SYNC_SUMMARY_a90a18a6.json
docs/TEST_REPORTS/evidence/PR60_MASTER_SYNC_HASHES_a90a18a6.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

报告必须包含：

- 开始与结束身份；
- 备份分支远程确认；
- 实际冲突文件；
- 冲突解决原则；
- 合并 Commit 和两个父提交；
- 每条本机验证命令与结果；
- PR远程状态；
- Actions启动状态；
- 数据安全声明；
- 清理结果。

不得提交 node_modules、dist、日志、Token、安装包或任何私人资料。

## 9. 结束清理

远程报告第一次复读成功后：

- 删除本任务 worktree和临时依赖；
- 删除 `D:\codex\LingJiSync\PR60-a90a18a6`；
- 解除 worktree登记；
- 确认没有LingJi进程、8766/8767监听或孤儿MCP；
- 共享父目录 `D:\codex\LingJiSync` 允许保留。

## 10. 判定

`PASS` 要求：

```text
备份分支 PASS
标准 merge PASS
仅预期日志冲突或零冲突
聚焦测试 PASS
Desktop smoke/build PASS
新 Head 推送 PASS
PR conflict 消失
远程 Actions 已启动
报告与回执远程可读
任务目录清理 PASS
```

CI或Artifact最终结论不属于本机任务的PASS条件，由ChatGPT在新Head推送后继续核验。

## 11. 最终回复

```text
PR60 master同步完成
task_id: PR60-MASTER-SYNC-A90A18A6
结论: PASS / FAIL / BLOCKED
源产品 Commit: a90a18a66ffba157c01367ba70bfec98f58798e2
源 master Commit: c349131d1aa22d2630b57df4d01d43a1088a1529
新产品 Head: <40位 SHA>
合并父提交: <a90a18a6>, <c349131d>
PR conflict: 已消失 / 仍存在
远程 Actions: 已启动 / 未启动
报告分支: acceptance/pr60-master-sync-a90a18a6
报告 Commit: <40位 SHA>
本地清理: PASS
```
