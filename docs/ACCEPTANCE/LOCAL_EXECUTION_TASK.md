# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> 用户只负责两句话之一：`去看任务单干活`，或 `Codex 已经完成`。用户不负责复制命令、解释 Git、寻找分支、上传文件或核对报告路径。
>
> Codex 不得从聊天记录、旧报告、自己的猜测或本机残留文件推断任务。只执行本文件中 `status: ACTIVE` 的任务。

## 1. 当前任务元数据

```yaml
task_id: PR60-OWNER-REACCEPTANCE-1C514877
status: ACTIVE
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
artifact_name: lingji-windows-0.1.0-1c514877
artifact_id: 8723868744
report_base: master
report_branch: acceptance/pr60-owner-1c514877
report_path: docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_ACCEPTANCE_1c514877.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_PUBLIC_ACCEPTANCE_SUMMARY_1c514877.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_PUBLIC_ACCEPTANCE_HASHES_1c514877.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 开始条件

Codex 开始前必须：

1. 拉取远程最新状态，读取根目录 `AGENTS.md`、`docs/ACCEPTANCE/README.md`、本文件、`CODEX_ACCEPTANCE_INSTRUCTIONS.md`、`CHANGE_ACCEPTANCE_LOG.md` 当前任务条目和 `LOCAL_EXECUTION_RESULT.md`。
2. 记录最后修改本任务单的远程 Commit：

```powershell
git log -1 --format=%H -- docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

3. 验证当前任务 `status: ACTIVE`；不是 ACTIVE 时立即停止。
4. 验证产品 PR、产品 Commit、Artifact 名称、Artifact ID、报告分支和报告路径完全一致。
5. 使用两个隔离工作区：

```text
产品测试 worktree：精确检出 product_commit
报告 worktree：从最新 report_base 创建 report_branch
```

报告分支从最新 `master` 治理主线创建，以确保包含当前任务单、结果回执和 CI 门禁。报告中固定记录被测 `product_commit`；不得修改或移动产品分支。

6. 在非系统盘使用唯一临时根目录：

```text
D:\codex\LingJiAcceptance\PR60-1c514877
```

7. 如果该临时根目录存在，先确认不含主人正式数据，然后整体删除重建。
8. 清理上一轮留下的安装包副本、解压目录、普通成功日志、普通成功截图、fixture、checkpoint、临时配置副本和临时 worktree。
9. 正常退出 LingJi；只结束确认属于 LingJi 的残留进程；确认 8766、8767 已释放且没有孤儿 MCP。
10. 不得删除 Production DataRoot、主人正式 Acceptance 数据、Obsidian Vault、正式记忆或用户自己的 AI 客户端配置。
11. 把清理前后的目录、进程和端口结果写入私有证据，但不得提交隐私内容。

任一开始条件不满足，结果为：

```text
BLOCKED_PRE_CLEANUP
```

## 3. 本轮必须执行

以 `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md` 为基础，以 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 中 PR #60 / `1c514877` 条目为增量，完成：

- 精确产品 Commit、Artifact、安装器和 SHA256 核验；
- 固定安装器直接覆盖安装，不卸载主人数据；
- 完整自动测试与当前增量回归；
- P0-A 首页和首次使用理解；
- Runtime、进程树、8766、8767、MCP 鉴权；
- 新 Codex 会话真实调用 LingJi MCP；
- `propose_memory` 只生成候选；
- ChatGPT Export 或 Codex Report 至少一种真实导入；
- 人工审核边界；
- 三轮 Core 重启；
- 一次 Windows 重启和重启后一轮 Core 重启；
- 无 PowerShell、CMD、黑窗；
- A-01 `CODEX_HOME` 隔离回归；
- Codex 配置备份、回滚、恢复；
- Production / Acceptance 隔离；
- 当前验收权威要求的全部安全和回归项。

主人肉眼项必须等待主人明确结论，Codex不得自行代填。

## 4. 报告提交顺序

必须严格按顺序执行：

```text
完成测试
→ 生成报告与脱敏公开证据
→ 从最新 master 创建报告分支
→ 提交报告正文和公开证据，记录 report_commit
→ push
→ 远程重新读取分支、report_commit 和报告
→ 在产品 PR 添加报告评论
→ 远程重新读取 PR 评论
→ 清理本地临时垃圾
→ 更新结果回执为最终状态
→ 再次提交、push、远程读取结果回执
→ 删除临时 worktree 和临时根目录
→ 最后回复主人
```

报告分支相对 `master` 只能新增或修改：

- 最终 Markdown 报告；
- 脱敏公开证据 JSON；
- 公开哈希清单；
- `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`。

不得修改产品代码或移动产品 Head。

## 5. 远程确认硬门禁

Codex 执行 `git push` 不等于提交成功。必须重新从远程读取并确认：

```powershell
git ls-remote --heads origin acceptance/pr60-owner-1c514877

gh api repos/wangduoyu001/lingji/commits/<REPORT_COMMIT>

gh api "repos/wangduoyu001/lingji/contents/docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_ACCEPTANCE_1c514877.md?ref=acceptance/pr60-owner-1c514877"

gh api "repos/wangduoyu001/lingji/contents/docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md?ref=acceptance/pr60-owner-1c514877"

gh api repos/wangduoyu001/lingji/issues/60/comments
```

只有以下事实全部成立，才允许写“已提交”：

- 远程分支存在；
- `report_commit` 存在且属于远程报告分支历史；
- 远程报告可读取；
- 远程结果回执可读取；
- 产品 PR 评论中包含 task_id、产品 Commit、报告分支、report_commit、报告路径和结论。

否则结果必须是：

```text
BLOCKED_REPORT_NOT_VISIBLE_ON_GITHUB
```

## 6. 结束清理硬门禁

远程确认完成后必须：

1. 删除本轮 Artifact、重复安装包、解压目录、fixture、checkpoint、临时配置副本、普通成功日志和普通成功截图。
2. 删除带本轮测试前缀的 Acceptance 测试候选和测试资料，不碰其他主人数据。
3. 删除产品测试 worktree。
4. 更新并提交最终结果回执，push 后从 GitHub API 重新读取。
5. 删除报告 worktree。
6. 删除 `D:\codex\LingJiAcceptance\PR60-1c514877`。
7. 重新检查临时根目录不存在、8766/8767 状态符合任务结束预期、没有孤儿 MCP、没有临时配置副本。
8. 只保留远程报告、脱敏公开证据、哈希、报告 Commit，以及主人明确要求保留的失败证据。

清理未完成不得回复“完成”，结果必须是：

```text
BLOCKED_POST_CLEANUP
```

## 7. 最终回复主人

只有 `LOCAL_EXECUTION_RESULT.md` 已在远程报告分支可读取、远程报告可读取、PR 评论可读取且结束清理通过后，才回复：

```text
本机任务已完成
task_id: PR60-OWNER-REACCEPTANCE-1C514877
最终结论: PASS / FAIL / BLOCKED
报告分支: acceptance/pr60-owner-1c514877
报告 Commit: <40位SHA>
远程确认: PASS
本地清理: PASS
```

禁止让主人理解或操作 Git、分支、上传、报告路径和清理命令。