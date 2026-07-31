# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> 用户只负责告诉 Codex“去看任务单干活”，或告诉 ChatGPT“Codex 已经完成”。用户不负责复制命令、理解 Git、选择分支、上传报告或清理本机垃圾。
>
> Codex 不得从聊天记录、旧报告、本机残留目录或自己的猜测推断任务。只执行本文件中 `status: ACTIVE` 的任务。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-D69874AF
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
artifact_name: lingji-windows-0.1.0-d69874af
artifact_id: 8762312712
artifact_zip_sha256: 6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4
installer_name: LingJi_0.1.0_windows_x64_setup.exe
installer_sha256: d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262
portable_exe_sha256: a852079b43b2f4020cb66942f44f1a5035633b65d3ff4122c2613c5ea7440a69
sidecar_exe_sha256: 20fe548e1be5cff5d1a34852f4fc0e223abb218eef1e51418724a6723e180599
manifest_sha256: d78a91153b62bcf641bcbbdbc41819283fe0dbc5deff2cdab64cdffcea3e6c87
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_base: master
report_branch: acceptance/pr60-memory-quality-trial-d69874af
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_d69874af.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_d69874af.txt
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

## 2. 旧任务作废

以下身份已经完成历史失败记录，禁止再次执行：

```text
product commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
artifact id: 8723868744
report branch: acceptance/pr60-memory-quality-trial-1c514877
```

旧报告中的 `D0-UX-001`、`D0-CODEX-002` 和 `BLOCKED_POST_CLEANUP` 只作为本轮回归来源，不代表新版本结论。

## 3. 任务目标

本轮验证修复后的完整路径：

```text
开始前清理
→ 固定新 Artifact 覆盖安装
→ Day 0 安全与首次使用回归
→ 主人五个检查点
→ Stage 1 小批量真实数据
→ Stage 2 逐步扩展
→ 记忆质量问题集与评分
→ 远程报告确认
→ 结束清理
```

Day 0 未 PASS 时禁止进入真实数据阶段。

完整标准以以下文件为准：

```text
docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前 PR #60 条目
docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

## 4. 开始前强制清理

Codex 开始前必须：

1. 拉取远程最新 `master`，读取 `AGENTS.md`、验收 README、本任务单、结果回执、专项协议、变更记录和报告模板。
2. 记录最后修改本任务单的远程 Commit：

```powershell
git log -1 --format=%H -- docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

3. 验证 task_id、产品 Commit、Artifact ID、全部哈希、报告分支和路径完全一致。
4. 使用两个隔离 worktree：产品测试 worktree 精确检出 `product_commit`；报告 worktree 从最新 `master` 创建报告分支。
5. 使用唯一临时根目录：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af
```

6. 清理旧任务的验收专用临时目录，包括：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877
D:\codex\LingJiAcceptance\PR60-1c514877
```

7. 删除上一轮重复 Artifact、解压目录、普通成功日志、普通成功截图、fixture、checkpoint、临时配置副本和临时 worktree。
8. 正常退出 LingJi；只结束确认属于 LingJi 的进程；确认 8766、8767 已释放且没有孤儿 MCP。
9. 删除时必须逐项确认目标位于 `D:\codex\LingJiAcceptance` 内，不得使用模糊通配符，不得跟随符号链接，不得触碰 Production DataRoot、正式 Acceptance 数据、Obsidian Vault、正式记忆或用户 AI 客户端配置。
10. 删除被操作系统或宿主策略拒绝时不得绕过安全策略，结果写 `BLOCKED_PRE_CLEANUP` 并列出剩余相对路径。

## 5. 上次问题的强制回归

### D0-UX-001：页面缺少统一引导

主人必须从新安装版确认：

- 页面始终只有一个明确的主要下一步；
- 扫描结束后主动说明发现了哪些 AI 软件和哪些历史目录元数据；
- 发现历史目录后主动询问是否查看或导入，不让主人自己猜文件格式和目录；
- 扫描、连接、导入、审核和向量状态组成连续流程；
- 状态卡能一眼区分“已检测”“配置存在”“命令可用”“真实连接通过”“历史已导入”；
- 不支持的 Codex 原始 Session / JSONL 自动导入必须明确说明，不能伪装为已自动导入。

### D0-CODEX-002：Codex 状态自相矛盾

必须验证：

- 配置文件存在、`codex` 命令可用和真实 MCP 调用是三个独立状态；
- 找不到 `codex` 命令时状态为 blocked，不得出现绿色 ready；
- 页面不得出现旧文案“已设置，等待测试”；
- 只有新 Codex 会话真实调用 LingJi MCP 成功后才显示 ready；
- 操作系统拒绝访问时显示具体阻塞和下一步，而不是笼统失败。

### Embedding / Qdrant 可执行诊断

必须验证页面显示：

- 配置模型；
- 实际激活模型；
- 缺失或不可用模型；
- 最近错误；
- Qdrant 当前模式和状态；
- 是否需要重建；
- 全文检索仍可用时明确说明；
- 当前能执行的处理入口或明确受限边界。

本版本不宣称自动下载 Embedding 模型或自动重建 Production Qdrant，不得把未实现能力写成 PASS。

## 6. Day 0 其余强制项目

- 固定安装器直接覆盖安装，不卸载、不删除主人数据、不迁回 C 盘；
- 完整自动测试和 Artifact 哈希验证；
- Runtime、进程树、8766、8767 和 MCP 鉴权；
- 新 Codex 会话真实调用 `get_core_memory`、`search_memory`、`build_context_pack`、`memory_health`、`propose_memory`；
- `propose_memory` 只生成候选；
- 主人亲自批准一个测试候选、拒绝一个测试候选；
- A-01 `CODEX_HOME` 隔离；
- 连接器备份、回滚和恢复；
- Production / Acceptance 物理隔离；
- 三轮 Core 重启；
- 一次 Windows 重启和重启后一轮 Core 重启；
- 主人确认无黑窗、页面可理解、客户端工具可见、调用正确和重启恢复。

Day 0 只有 `PASS / FAIL / BLOCKED`。FAIL 或 BLOCKED 时停止，不进入真实数据阶段。

## 7. 真实数据授权与试运行

Stage 1 前必须获得主人明确授权。初始范围最多为：

```text
1 部短剧剧本
1 份 Codex 开发报告
少量 ChatGPT 历史
Obsidian 中 1 个明确目录
```

Stage 1 必须验证原文追溯、来源、adapter version、input hash、idempotency、失败路径、重复导入、候选边界和新 Codex 会话检索。

Stage 1 无 P0/P1 后，Stage 2 才可逐步扩展到最多 10 部授权剧本及其他授权资料，不得一次性全量导入。

至少执行 20 道质量题，主人至少抽查 10 道。阈值：

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP 真实调用成功率 >= 95%
重复正式内容 = 0
Production 污染 = 0
人工审核链成功率 = 100%
Windows 重启后恢复 = 100%
```

## 8. 主人检查点

Codex只在以下节点暂停：

```text
A：安装、黑窗、首页、唯一下一步和状态是否看懂
B：Codex 工具可见、真实调用和返回内容
C：主人批准一个候选、拒绝一个候选
D：Windows 重启后的黑窗、恢复和页面操作
E：主人抽查至少 10 道质量题的答案与来源
```

Codex不得替主人填写肉眼、理解程度或真实资料正确性结论。

## 9. 报告提交与远程复读

顺序固定：

```text
完成执行
→ 生成最终报告和脱敏公开证据
→ 从最新 master 创建报告分支
→ 提交报告正文和公开证据并记录 report_commit
→ push
→ 远程复读分支、Commit、报告和公开证据
→ 在 PR #60 添加报告评论
→ 远程复读 PR 评论
→ 执行结束清理
→ 更新结果回执
→ 再次提交、push 和远程复读
→ 删除 worktree 和临时根目录
→ 最后回复主人
```

远程必须能够读取：

```powershell
git ls-remote --heads origin acceptance/pr60-memory-quality-trial-d69874af

gh api repos/wangduoyu001/lingji/commits/<REPORT_COMMIT>

gh api "repos/wangduoyu001/lingji/contents/docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md?ref=acceptance/pr60-memory-quality-trial-d69874af"

gh api "repos/wangduoyu001/lingji/contents/docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md?ref=acceptance/pr60-memory-quality-trial-d69874af"

gh api repos/wangduoyu001/lingji/issues/60/comments
```

任一远程复读失败：`BLOCKED_REPORT_NOT_VISIBLE_ON_GITHUB`。

## 10. 结束清理

- 删除本轮 Artifact 副本、重复安装包、解压目录、普通成功日志、普通成功截图、fixture、checkpoint、临时配置副本和产品测试 worktree；
- 删除带本轮前缀的 Acceptance 测试候选和测试资料；
- 主人授权的真实资料是否保留由主人决定，Codex不得擅自删除；
- 更新结果回执并远程复读后，删除报告 worktree和 `D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af`；
- 确认没有孤儿 MCP、临时配置副本和剩余临时目录；
- 删除被安全策略拒绝时不得强制绕过，结果写 `BLOCKED_POST_CLEANUP` 并列出剩余相对路径。

## 11. 最终回复主人

只有报告、公开证据、结果回执和 PR 评论都能远程读取，且结束清理通过后，才回复：

```text
本机任务已完成
task_id: PR60-MEMORY-QUALITY-TRIAL-D69874AF
最终结论: PASS / FAIL / BLOCKED
Day 0: PASS / FAIL / BLOCKED
Stage 1: PASS / FAIL / BLOCKED / NOT_RUN
Stage 2: PASS / FAIL / BLOCKED / NOT_RUN
quality_score: <百分比或 NOT_RUN>
source_accuracy: <百分比或 NOT_RUN>
false_positive_rate: <百分比或 NOT_RUN>
报告分支: acceptance/pr60-memory-quality-trial-d69874af
报告 Commit: <40位SHA>
远程确认: PASS
本地清理: PASS
```

禁止让主人理解或操作 Git、分支、上传、报告路径和清理命令。