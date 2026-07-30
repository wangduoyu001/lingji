# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> 用户只负责两句话之一：`去看任务单干活`，或 `Codex 已经完成`。用户不负责复制命令、解释 Git、寻找分支、上传文件或核对报告路径。
>
> Codex 不得从聊天记录、旧报告、自己的猜测或本机残留文件推断任务。只执行本文件中 `status: ACTIVE` 的任务。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-1C514877
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
artifact_name: lingji-windows-0.1.0-1c514877
artifact_id: 8723868744
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_base: master
report_branch: acceptance/pr60-memory-quality-trial-1c514877
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_1c514877.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_1c514877.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
day0_required: true
real_data_requires_day0_pass: true
real_data_authorization_required: true
minimum_quality_questions: 20
minimum_owner_sample_questions: 10
minimum_quality_score_percent: 90
minimum_source_accuracy_percent: 95
maximum_false_positive_percent: 5
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 任务性质

本任务把 PR #60 的本机安全验收与真实数据试运行合并执行：

```text
Day 0 安全门槛
→ Stage 1 小批量真实数据
→ Stage 2 扩展数据试运行
→ 记忆质量问题集与评分
→ 主人检查点
→ 报告、远程复读和本地清理
```

Day 0 不是可选步骤。Day 0 未 PASS 时，禁止导入主人真实资料，只能提交 FAIL 或 BLOCKED 报告。

完整标准以 `docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md` 为准，并叠加：

- `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`；
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 当前 PR #60 条目；
- `docs/ACCEPTANCE/REPORT_TEMPLATE.md`。

## 3. 开始条件和清理

Codex 开始前必须：

1. 拉取远程最新 `master`。
2. 固定读取：

```text
AGENTS.md
docs/ACCEPTANCE/README.md
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前条目
docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

3. 记录最后修改任务单的远程 Commit：

```powershell
git log -1 --format=%H -- docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

4. 确认任务为 `ACTIVE`，产品 PR、产品 Commit、Artifact、报告分支和报告路径完全一致。
5. 使用两个隔离 worktree：

```text
产品测试 worktree：精确检出 product_commit
报告 worktree：从最新 master 创建 report_branch
```

6. 使用唯一非系统盘临时根目录：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877
```

7. 若目录存在，确认不含主人正式数据后整体删除重建。
8. 清理上一轮重复安装包、Artifact、解压目录、普通成功日志、普通成功截图、fixture、checkpoint、临时配置副本和临时 worktree。
9. 正常退出 LingJi，只结束确认属于 LingJi 的残留进程，确认 8766、8767 已释放且没有孤儿 MCP。
10. 不得删除 Production DataRoot、主人正式 Acceptance 数据、Obsidian Vault、正式记忆或用户自己的 AI 客户端配置。

开始前清理失败：

```text
BLOCKED_PRE_CLEANUP
```

## 4. Day 0 安全门槛

在任何真实数据导入前，Codex必须完成：

- 精确产品 Commit、Artifact 和全部哈希核验；
- 固定安装器直接覆盖安装；
- 强制自动测试；
- P0-A 首页和首次使用理解；
- Runtime、进程树、8766、8767 和 MCP 鉴权；
- 新 Codex 会话真实调用全部规定的 LingJi MCP 工具；
- `propose_memory` 只生成候选；
- 主人亲自批准一个测试候选、拒绝一个测试候选；
- A-01 `CODEX_HOME` 隔离回归；
- 连接器备份、回滚和恢复；
- Production / Acceptance 物理隔离；
- 三轮 Core 重启；
- 一次 Windows 重启和重启后一轮 Core 重启；
- 主人确认无黑窗、页面可理解、客户端工具可见和重启后恢复。

Day 0 只有 `PASS / FAIL / BLOCKED`。FAIL 或 BLOCKED 时停止，不进入真实数据阶段。

## 5. 真实数据授权

Codex不得自行决定读取或导入哪些真实资料。

开始 Stage 1 前，主人必须明确授权数据范围。允许使用的初始范围建议为：

```text
1 部短剧剧本
1 份 Codex 开发报告
少量 ChatGPT 历史
Obsidian 中 1 个明确目录
```

授权只说明资料类别或明确目录，不需要主人复制文件到聊天中。

未得到明确授权：

```text
BLOCKED_REAL_DATA_AUTHORIZATION
```

## 6. Stage 1 小批量试运行

按照 `MEMORY_QUALITY_TRIAL.md` 执行并验证：

- 原文可追溯；
- provenance、adapter version、input hash 和 idempotency key 完整；
- 重复导入不重复生成正式内容；
- 无效文件失败且不产生脏正式记忆；
- 导入只生成候选；
- 剧本内容不进入主人个人事实；
- Codex 新会话能检索并引用正确来源；
- 测试候选可清理且不影响其他主人数据。

出现 P0/P1 问题立即停止扩容。

## 7. Stage 2 扩展试运行

只有 Stage 1 PASS 后才能逐步扩展，最多使用：

```text
10 部主人授权的短剧剧本
1 个真实短剧项目资料集
更多主人授权的 ChatGPT 历史
Codex 开发报告
Obsidian 授权目录
```

不得一次性全量导入。每批记录导入前后数量、磁盘占用、重复、失败、候选和正式记忆变化。

## 8. 质量问题集和主人验证

Codex 至少生成并执行 20 题：

```text
精确事实 ≥ 8
跨文档比较 ≥ 4
来源核验 ≥ 4
负面和边界问题 ≥ 4
```

每题：

```text
2 分：答案、来源和边界正确
1 分：主体正确，细节或来源定位有问题
0 分：错误、找不到、张冠李戴、来源错误或越权
```

主人至少抽查 10 题，判断答案和来源是否符合真实资料。Codex不得替主人完成全部主观正确性判定。

通过阈值：

```text
quality_score ≥ 90%
source_accuracy ≥ 95%
false_positive_rate ≤ 5%
Codex MCP 真实调用成功率 ≥ 95%
重复导入产生重复正式内容 = 0
人工审核链成功率 = 100%
Windows 重启后恢复 = 100%
```

## 9. 主人检查点

Codex只在以下节点暂停并请求主人给出简短结论：

```text
A：安装、黑窗、首页和下一步
B：Codex 工具可见、真实调用和返回内容
C：亲自批准一个候选、拒绝一个候选
D：Windows 重启后黑窗、恢复和页面操作
E：至少 10 道质量题的答案与来源抽查
```

主人不参与命令、Git、日志、配置和清理操作。

## 10. 报告与远程提交

严格执行：

```text
完成测试和试运行
→ 生成报告与脱敏公开证据
→ 从最新 master 创建报告分支
→ 提交报告正文和公开证据，记录 report_commit
→ push
→ 远程重新读取分支、Commit 和报告
→ 在产品 PR #60 添加报告评论
→ 远程重新读取 PR 评论
→ 清理本地临时垃圾
→ 更新结果回执
→ 再次提交、push 和远程复读
→ 删除全部临时 worktree 和临时根目录
→ 最后回复主人
```

报告分支相对 `master` 只能新增或修改：

- 最终 Markdown 报告；
- 脱敏公开证据 JSON；
- 公开哈希清单；
- `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`。

远程必须重新读取：

```powershell
git ls-remote --heads origin acceptance/pr60-memory-quality-trial-1c514877

gh api repos/wangduoyu001/lingji/commits/<REPORT_COMMIT>

gh api "repos/wangduoyu001/lingji/contents/docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md?ref=acceptance/pr60-memory-quality-trial-1c514877"

gh api "repos/wangduoyu001/lingji/contents/docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md?ref=acceptance/pr60-memory-quality-trial-1c514877"

gh api repos/wangduoyu001/lingji/issues/60/comments
```

任何远程复读失败：

```text
BLOCKED_REPORT_NOT_VISIBLE_ON_GITHUB
```

## 11. 结束清理

远程报告第一次确认后：

1. 删除本轮 Artifact、重复安装包、解压目录、普通成功日志和普通成功截图。
2. 删除 fixture、checkpoint、临时配置副本和产品测试 worktree。
3. 删除带本轮前缀的 Acceptance 测试候选和测试资料。
4. 主人授权导入的真实资料是否保留，以主人选择为准，不得自行删除。
5. 更新结果回执，提交、push 并远程复读。
6. 删除报告 worktree。
7. 删除 `D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877`。
8. 确认没有孤儿 MCP、没有临时配置副本、临时根目录不存在。

结束清理失败：

```text
BLOCKED_POST_CLEANUP
```

## 12. 最终回复主人

只有结果回执、报告、公开证据和 PR 评论都可远程读取，且结束清理通过后，才回复：

```text
本机任务已完成
task_id: PR60-MEMORY-QUALITY-TRIAL-1C514877
最终结论: PASS / FAIL / BLOCKED
Day 0: PASS / FAIL / BLOCKED
Stage 1: PASS / FAIL / BLOCKED / NOT_RUN
Stage 2: PASS / FAIL / BLOCKED / NOT_RUN
quality_score: <百分比或 NOT_RUN>
source_accuracy: <百分比或 NOT_RUN>
false_positive_rate: <百分比或 NOT_RUN>
报告分支: acceptance/pr60-memory-quality-trial-1c514877
报告 Commit: <40位SHA>
远程确认: PASS
本地清理: PASS
```

禁止让主人理解或操作 Git、分支、上传、报告路径和清理命令。