# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> 用户只负责：告诉 Codex“去看任务单干活”、在固定检查点给出观察结论，以及告诉 ChatGPT“Codex 已经完成”。用户不负责 Git、命令、上传、报告路径或本地清理。
>
> Codex 只执行本文件中 `status: ACTIVE` 的任务。聊天旧指令和旧 Artifact 全部失效。

## 1. 当前任务元数据

```yaml
task_id: PR60-GUIDED-MEMORY-TRIAL-D69874AF
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
artifact_name: lingji-windows-0.1.0-d69874af
artifact_id: 8762312712
artifact_zip_sha256: 6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4
installer_sha256: d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262
portable_exe_sha256: a852079b43b2f4020cb66942f44f1a5035633b65d3ff4122c2613c5ea7440a69
sidecar_exe_sha256: 20fe548e1be5cff5d1a34852f4fc0e223abb218eef1e51418724a6723e180599
manifest_sha256: d78a91153b62bcf641bcbbdbc41819283fe0dbc5deff2cdab64cdffcea3e6c87
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
cleanup_tool_path: scripts/cleanup_acceptance_workspace.py
report_base: master
report_branch: acceptance/pr60-guided-memory-trial-d69874af
report_path: docs/TEST_REPORTS/PR60_GUIDED_MEMORY_TRIAL_d69874af.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_GUIDED_MEMORY_TRIAL_SUMMARY_d69874af.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_GUIDED_MEMORY_TRIAL_HASHES_d69874af.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
day0_required: true
real_data_requires_day0_pass: true
real_data_authorization_required: true
minimum_quality_questions: 20
minimum_owner_sample_questions: 10
minimum_quality_score_percent: 90
minimum_source_accuracy_percent: 95
maximum_false_positive_percent: 5
semantic_retrieval_required_for_final_pass: true
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 被取代的旧任务

以下身份已失败并废弃，禁止再次下载、安装或继续填写旧报告：

```text
product_commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
artifact_id: 8723868744
report_branch: acceptance/pr60-memory-quality-trial-1c514877
```

旧报告只作为失败证据保留。

## 3. 固定读取顺序

```text
AGENTS.md
docs/ACCEPTANCE/README.md
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 顶部 PR #60 主动引导修复条目
docs/ACCEPTANCE/REPORT_TEMPLATE.md
docs/TEST_REPORTS/PR60_ASSISTANT_HUB_GUIDED_FLOW_PLAN.md
```

记录最后修改本任务单的远程 Commit：

```powershell
git log -1 --format=%H -- docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

## 4. 开始前安全清理

允许根目录：

```text
D:\codex\LingJiAcceptance
```

### 4.1 清理上轮被阻塞的旧目录

先预览：

```powershell
python scripts/cleanup_acceptance_workspace.py --allowed-root "D:\codex\LingJiAcceptance" cleanup --target "D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877" --task-id "PR60-MEMORY-QUALITY-TRIAL-1C514877" --allow-unmarked-legacy
```

只有预览列出的内容全部属于旧验收目录时，才执行：

```powershell
python scripts/cleanup_acceptance_workspace.py --allowed-root "D:\codex\LingJiAcceptance" cleanup --target "D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877" --task-id "PR60-MEMORY-QUALITY-TRIAL-1C514877" --allow-unmarked-legacy --execute
```

若旧目录不存在，记录 `ALREADY_ABSENT`。若包含未知目录或链接，停止并报告 `BLOCKED_LEGACY_CLEANUP_REVIEW`，不得强删。

### 4.2 初始化本轮目录

```text
D:\codex\LingJiAcceptance\PR60-GUIDED-TRIAL-d69874af
```

执行：

```powershell
python scripts/cleanup_acceptance_workspace.py --allowed-root "D:\codex\LingJiAcceptance" initialize --target "D:\codex\LingJiAcceptance\PR60-GUIDED-TRIAL-d69874af" --task-id "PR60-GUIDED-MEMORY-TRIAL-D69874AF"
```

只在该目录内创建产品测试 worktree、报告 worktree、Artifact、日志、fixture、checkpoint 和临时配置副本。

随后：

- 正常退出 LingJi；
- 只结束确认属于 LingJi 的残留进程；
- 释放 8766 / 8767；
- 确认没有孤儿 MCP；
- 不碰 Production DataRoot、正式 Acceptance 数据、Vault、正式记忆和主人 AI 配置。

开始前清理未通过：

```text
BLOCKED_PRE_CLEANUP
```

## 5. Day 0 第一目标：验证新主动引导

覆盖安装固定新 Artifact，不卸载，不删除主人数据。

主人 Checkpoint A 必须直接观察真实安装版：

```text
黑窗：有 / 无
首页：正常 / 异常
扫描后 5 秒内是否知道唯一下一步：知道 / 不知道
是否能区分“发现目录、配置写入、命令可用、真实测试通过”：能 / 不能
是否能看懂准备导入什么、尚未读取什么：能 / 不能
是否能一眼看到 Embedding / Qdrant 的具体阻塞原因：能 / 不能
```

强制 UI 行为：

- 页面顶部只给一个当前阻塞或下一步；
- 扫描到 Codex 历史目录后主动提示，但不读取正文；
- 明确当前只支持 ChatGPT Export 和结构化 Codex Report；
- 不把原始 Session / JSONL / Markdown 伪装成已支持自动导入；
- “配置文件已写入”不能显示成绿色连接成功；
- 找不到 `codex` 命令时必须显示 `blocked` 和明确原因；
- 只有真实客户端验证通过才显示 `ready`；
- Embedding / Qdrant 显示配置模型、实际模型、错误、模式和重建要求；
- 全文检索可用时必须明确说明，不能把降级伪装成系统崩溃。

Checkpoint A 任一核心项失败，Day 0 为 FAIL，停止真实数据导入。

## 6. Day 0 基础安全与客户端验证

继续执行：

- 产品 Commit、Artifact ID 和全部 SHA256；
- Runtime、进程树、8766、8767、认证；
- Production / Acceptance 物理隔离；
- A-01 空环境隔离；
- 连接器预览、备份、冲突拒绝、回滚和恢复；
- `propose_memory` 只生成候选；
- 主人批准一个测试候选、拒绝一个测试候选；
- 三轮 Core 重启；
- Windows 重启及重启后一轮 Core 重启；
- 主人确认无黑窗和界面恢复。

### 6.1 真实 Codex 调用方法

优先使用当前执行本任务的 Codex 主机直接调用 LingJi MCP：

```text
get_core_memory
search_memory
build_context_pack
memory_health
propose_memory
```

不得把“从 Codex 内部再次启动嵌套 codex.exe 被宿主拒绝”单独判为产品失败。

判定规则：

- 当前 Codex 会话能看到并真实调用 LingJi 工具：PASS；
- 当前会话需要重启才能加载新配置：写 checkpoint，主人重开 Codex 后继续；
- UI 报告命令缺失且当前 Codex 也无法调用 LingJi：BLOCKED_CODEX_CLIENT;
- 只用 HTTP 脚本列出工具，不能替代真实 Codex 调用。

## 7. Embedding / Qdrant 边界

本轮必须记录：

```text
configured_model
active_model
embedding_state
embedding_available
embedding_last_error
qdrant_state
qdrant_mode
collection
collection_exists
rebuild_required
lexical_available
```

不得自动下载模型，不得自动删除或重建 Production Collection。

允许在主人明确同意的 Acceptance Workspace 中执行已有安全配置或重建流程。

最终 PASS 要求语义检索真实可用。若 UI 已正确解释问题但本机模型或 Qdrant 尚未激活：

```text
BLOCKED_VECTOR_ACTIVATION
```

可以在不写 Production 的前提下继续 Stage 1 lexical 试运行并收集问题，但最终不得写 PASS。

## 8. 真实数据试运行

只有 Day 0 安全项通过且主人明确授权资料范围后，才能进入 Stage 1。

初始授权范围由主人在检查点确认，建议：

```text
1 部短剧剧本
1 份 Codex 开发报告
少量 ChatGPT 历史
Obsidian 中 1 个明确目录
```

Codex不得自行扩大范围。

按照 `MEMORY_QUALITY_TRIAL.md` 完成：

- raw、provenance、adapter version、input hash、idempotency key；
- 重复导入和无效文件；
- 候选审核边界；
- 剧本内容不得进入主人个人事实；
- 至少 20 道质量题；
- 主人抽查至少 10 题；
- quality score ≥ 90%；
- source accuracy ≥ 95%；
- false positive rate ≤ 5%；
- Codex MCP 成功率 ≥ 95%；
- 重复正式内容和 Production 污染均为 0。

## 9. 报告与远程确认

报告分支从最新 `master` 创建，产品 worktree固定在 `d69874af`。

严格顺序：

```text
完成测试
→ 生成报告和脱敏公开证据
→ 提交报告正文与证据，记录 report_commit
→ push
→ 远程复读分支、Commit、报告和证据
→ 评论 PR #60
→ 远程复读 PR 评论
→ 执行结束清理
→ 更新结果回执
→ 再次提交、push、远程复读
→ 删除报告 worktree
→ 最后回复主人
```

必须远程读取：

```powershell
git ls-remote --heads origin acceptance/pr60-guided-memory-trial-d69874af

gh api repos/wangduoyu001/lingji/commits/<REPORT_COMMIT>

gh api "repos/wangduoyu001/lingji/contents/docs/TEST_REPORTS/PR60_GUIDED_MEMORY_TRIAL_d69874af.md?ref=acceptance/pr60-guided-memory-trial-d69874af"

gh api "repos/wangduoyu001/lingji/contents/docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md?ref=acceptance/pr60-guided-memory-trial-d69874af"

gh api repos/wangduoyu001/lingji/issues/60/comments
```

## 10. 结束清理

先预览本轮目录：

```powershell
python scripts/cleanup_acceptance_workspace.py --allowed-root "D:\codex\LingJiAcceptance" cleanup --target "D:\codex\LingJiAcceptance\PR60-GUIDED-TRIAL-d69874af" --task-id "PR60-GUIDED-MEMORY-TRIAL-D69874AF"
```

确认仅包含本轮临时内容后执行：

```powershell
python scripts/cleanup_acceptance_workspace.py --allowed-root "D:\codex\LingJiAcceptance" cleanup --target "D:\codex\LingJiAcceptance\PR60-GUIDED-TRIAL-d69874af" --task-id "PR60-GUIDED-MEMORY-TRIAL-D69874AF" --execute
```

工具逐文件删除、空目录后序删除，不使用递归强删；遇到链接、junction、未知路径或 task_id 不一致立即拒绝。

完成条件：

```text
cleanup_before: PASS
cleanup_after: PASS
local_temp_root_absent: true
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
```

## 11. 最终回复主人

只有远程结果回执可读且结束清理通过后才回复：

```text
本机任务已完成
task_id: PR60-GUIDED-MEMORY-TRIAL-D69874AF
最终结论: PASS / FAIL / BLOCKED
Day 0: PASS / FAIL / BLOCKED
Stage 1: PASS / FAIL / BLOCKED / NOT_RUN
Stage 2: PASS / FAIL / BLOCKED / NOT_RUN
语义检索: PASS / BLOCKED / NOT_RUN
quality_score: <百分比或 NOT_RUN>
source_accuracy: <百分比或 NOT_RUN>
false_positive_rate: <百分比或 NOT_RUN>
报告分支: acceptance/pr60-guided-memory-trial-d69874af
报告 Commit: <40位SHA>
远程确认: PASS
本地清理: PASS
```

不得让主人处理 Git、上传、命令或清理。