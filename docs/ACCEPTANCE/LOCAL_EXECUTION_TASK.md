# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> 本轮起，本机 Codex 不再只是执行一次验收，而是负责 PR #60 剩余开发、测试、发包、真机复验、主线收敛、文档、报告和清理。具体总控见 `docs/ACCEPTANCE/LOCAL_FINAL_CLOSEOUT_PLAN.md`。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-F0956F67
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: f0956f6793b9417a7621bf0088ec2ee72de67e84
artifact_name: lingji-windows-0.1.0-f0956f67
artifact_id: 8834916611
artifact_zip_sha256: 0273b97eba5332b5f876cc0147313126e4c049b32e0da2596a05a8ba2d51c504
installer_name: LingJi_0.1.0_windows_x64_setup.exe
installer_sha256: c1209ba968508bb5b684776f350f7daa4a447b6123df2b04ed32b798240ec1f4
portable_name: LingJi_0.1.0_windows_x64.exe
portable_exe_sha256: 28b637e7781642f123b9e4b1ccf473ac45905a6881f1bfe36efa5568a8ad3e1d
sidecar_exe_sha256: e26b9271371de8ac381448ed4533b4024a33ca16d63f9abd08a43cfd9c2b98c4
manifest_sha256: 8e2614c346482781ae560eca4fd62b6428816ce30da0d0c5bdb1ddc4842a0a73
build_metadata_sha256: dfc3607978f89e4b968390d22f8706c499b6a09ac3d64bbf086f167a86669e94
artifact_workflow_run_id: 30752394032
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
closeout_plan_path: docs/ACCEPTANCE/LOCAL_FINAL_CLOSEOUT_PLAN.md
report_branch: acceptance/pr60-memory-quality-trial-f0956f67
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_f0956f67.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_f0956f67.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_f0956f67.txt
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
local_discovery_required: true
local_closeout_owner: true
continue_after_actionable_failure: true
pr60_draft_required: true
```

## 2. 当前远程基线

```text
master = d831af9dcb992533252e2f298b6f965835bb849e
product Head = f0956f6793b9417a7621bf0088ec2ee72de67e84
product branch ahead of master = 200 commits
product branch behind master = 33 commits
PR #60 = Draft / Do not merge
```

当前产品提交在既有 fresh DataRoot 计数修复和 MCP 单一所有权基础上，进一步修复了空 Collection 被未验证 Embedding 状态错误覆盖的问题。新 Artifact 必须在任何导入前显示 0 文档、0 分块、0 Core Memory、0 向量和 `empty / collection_empty`。

旧 `6214ac48 / 8834478298`、`623d3c9d / 8834121370`、`05376996 / 8832376546` 及更早身份均禁止使用。

## 3. 第一步：读取本机最新提交并保护现场

在任何安装、清理或代码修改前，严格执行 `LOCAL_FINAL_CLOSEOUT_PLAN.md` 的 Phase 0。

必须记录：

```text
本机仓库根
当前分支
本机 HEAD
origin/master
origin/feature/unified-ai-memory-connectors
未推送提交
未提交修改
worktree
reflog
本机与远程的领先/落后关系
```

必须生成：

```text
docs/TEST_REPORTS/LOCAL_FINAL_CLOSEOUT_DISCOVERY_<local-short-sha>.md
```

禁止 `reset --hard`、`clean -fdx`、force push、删除未知 worktree或覆盖未提交修改。

若存在未推送提交，先创建并推送：

```text
backup/local-closeout-<timestamp>-<shortsha>
```

Phase 0未完成，不得进入 Day 0。

## 4. 当前立即任务：f0956f67 Day 0

只下载和使用：

```text
Artifact: lingji-windows-0.1.0-f0956f67
Artifact ID: 8834916611
Release run: 30752394032
```

任务根：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-f0956f67
```

产品 DataRoot：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-f0956f67\product
workspace = acceptance
```

任务专属环境：

```text
LOCALAPPDATA = <任务根>\profile\LocalAppData
APPDATA      = <任务根>\profile\AppData
USERPROFILE  = <任务根>\profile\User
HOME         = <任务根>\profile\User
CODEX_HOME   = <任务根>\profile\CodexHome
```

开始前从当前产品提交的隔离 worktree调用 `scripts/cleanup_acceptance_workspace.py`，使用旧任务身份 `PR60-MEMORY-QUALITY-TRIAL-6214AC48` 精确清理上一轮 `D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-6214ac48`。合法 dry-run必须返回：

```text
status = DRY_RUN_READY
authorized = true
next_action = rerun_with_execute
```

随后由 Codex自动执行 `--execute`。不得要求主人手工删除。

## 5. Day 0 必须证明

```text
首次恢复 <= 45 秒
8766鉴权健康，8767 MCP可用
精确 DataRoot / workspace / binding一致
真实资料正文读取数 = 0
合成 ChatGPT/Codex 导出包自动发现
一次授权后立即入队，无路径输入、无二次提交
队列任务完成或给出真实可解释错误
只有 MCP Runtime 持有 SQLite/Qdrant
Control API 不打开第二个 Qdrant
向量状态 empty/locked/stale/rebuilding/healthy一致
全文检索与语义检索分别真实显示
Codex跳过不可启动WindowsApps别名
真实 codex mcp list 列出 lingji-memory
真实 Codex MCP调用命中 acceptance Runtime
合成候选批准一个、拒绝一个
Core/MCP/Desktop多轮重启恢复
Windows重启恢复
Production污染 = 0
清理 dry-run = DRY_RUN_READY
execute后任务根不存在
报告、回执、PR评论远程复读通过
```

## 6. 主人边界

主人只参与：

```text
A：观察首启、DataRoot和UI
B：授权读取任务生成的合成导出包
C：确认一键导入、Codex MCP和Qdrant证据
D：指定一个合成候选批准、一个拒绝
E：允许Windows重启
F：确认重启、清理和远程报告结果
```

不得要求主人填写路径、刷新状态、执行命令、启停服务、上传报告或删除目录。

## 7. Day 0失败后的本地修复责任

Day 0失败时：

1. 立即保持 `stage1_result = NOT_RUN`、`stage2_result = NOT_RUN`、`real_data_authorized = false`；
2. 完成失败报告和远程复读；
3. 不等待云端零散修改；
4. 按 `LOCAL_FINAL_CLOSEOUT_PLAN.md` Phase 2建立最小修复分支；
5. 添加能够覆盖真实失败路径的回归测试；
6. 完成焦点测试、完整 Python、Desktop smoke/build、Rust/Tauri、release验证；
7. 每个功能或大段代码新增 Markdown报告并更新 Code Map、Project Status、Changelog；
8. PR只合入产品分支，PR #60继续保持Draft；
9. 精确新Head五套门禁通过后生成新Artifact并核验全部哈希；
10. 通过docs PR更新本任务和回执；
11. 清理旧任务根并重新执行Day 0。

同一缺陷重复出现时，必须先补足缺失的真实回归测试或修复验收合同，禁止只换Artifact。

## 8. Day 0通过后的后续阶段

严格按 `LOCAL_FINAL_CLOSEOUT_PLAN.md` 执行：

```text
Phase 3：主人具名授权后的Stage 1小范围真实资料质量试运行
Phase 4：Stage 1通过后的Stage 2扩展验证
Phase 5：产品分支与master收敛
Phase 6：最终精确Head发布候选全量验证
Phase 7：文档、回滚、清理、PR #60收尾
```

Stage 1至少20道质量题、主人抽查至少10道，并满足任务YAML中的质量阈值。

## 9. 架构与开发硬边界

```text
src/ = 唯一长期正式主线
second_brain/ = 迁移、兼容、只读、诊断来源
Tauri + React = 唯一正式UI
Obsidian Vault + Git = 永久记忆权威
lingji_state.db = 运行状态
lingji_memory.db = 可重建全文/元数据索引
Qdrant = 可重建语义索引
MCP Runtime = 嵌入式Qdrant唯一实时拥有者
Control API = 只读MCP状态快照，不实时打开Qdrant
```

禁止新增平行系统、第二事实源、第二正式UI或第二Qdrant拥有者。

## 10. 最终门禁

PR #60只有在以下全部完成后才可转Ready：

```text
最终精确Head CI全绿
最终Artifact哈希核验
最终合成Day 0 PASS
Stage 1 PASS
主人质量抽查PASS
Production污染0
重复正式内容0
主人配置保留PASS
安全清理PASS
远程报告复读PASS
master收敛完成
回滚验证完成
```

合并PR #60、创建版本标签或公开Release前，仍需主人明确批准。
