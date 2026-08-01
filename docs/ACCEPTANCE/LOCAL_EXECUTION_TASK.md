# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务。不得从旧聊天、旧报告、本机残留目录或旧 Artifact 推断额外要求。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-3E24E65C
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: 3e24e65ce12bfa22b5c9193d65500648ebf45729
artifact_name: lingji-windows-0.1.0-3e24e65c
artifact_id: 8820695386
artifact_zip_sha256: 649de2e03bde0ec491f8c828fdfac73d1a9539877c72ecd5199c7be407ee0e98
installer_name: LingJi_0.1.0_windows_x64_setup.exe
installer_sha256: 21d87149844b8fd7ccf4d8e8b05923bbccf1338573aa6e189202571ef769caa1
portable_name: LingJi_0.1.0_windows_x64.exe
portable_exe_sha256: bcb1af32c1dbcd9d0d25147c0f3bc11e5835ef9025d121a7cc5e7dfd0b3b9fc0
sidecar_exe_sha256: 866c80420b99ff7935814755957e4bbf7b8df2c7492063db0af3ae0fffd7a489
manifest_sha256: 518a0ec991b064704e8d55a3999451f32c22a6225021370cd0917c699b58466c
artifact_workflow_run_id: 30707017562
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_branch: acceptance/pr60-memory-quality-trial-3e24e65c
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_3e24e65c.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_3e24e65c.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_3e24e65c.txt
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

## 2. 已确认远程基线

精确产品 Head：

```text
3e24e65ce12bfa22b5c9193d65500648ebf45729
```

远程门禁全部通过：

```text
local-execution-handoff #75：PASS
acceptance-doc-sync #82：PASS
tests #1167：PASS
P0 Windows Gate #261：PASS
Windows Desktop Release Baseline #143：PASS
```

正式 GitHub Artifact：

```text
名称：lingji-windows-0.1.0-3e24e65c
ID：8820695386
ZIP SHA256：649de2e03bde0ec491f8c828fdfac73d1a9539877c72ecd5199c7be407ee0e98
未过期；对应 Head 精确为 3e24e65c。
```

旧 Artifact `8723868744`、`8762312712` 及产品提交 `1c514877`、`d69874af` 均为历史失败身份，禁止下载、安装或复验。

PR #60 必须保持 Draft，不得在本任务结束前合并。

## 3. 本轮阶段边界

本任务分两段：

```text
Day 0：只使用合成测试资料、隔离配置和元数据发现；必须先完成。
Stage 1：只有 Day 0 PASS 且主人明确授权后才能读取指定真实资料。
```

Codex完成 Day 0 自动部分后必须停止，等待主人完成肉眼检查点并明确授权。不得因为页面看起来正常就自动进入 Stage 1。

未经主人授权，禁止读取真实剧本、真实聊天内容、真实 Obsidian 文档内容、真实 Codex Session/JSONL 内容或任何其他私人正文。

允许产品在 Day 0 扫描已安装 AI 软件和已知历史目录的元数据，但只允许读取存在性、路径类型、支持状态和必要的近似数量；不得打开正文。

## 4. 开始前清理与身份门禁

### 4.1 远程身份

必须确认：

```text
origin/feature/unified-ai-memory-connectors
= 3e24e65ce12bfa22b5c9193d65500648ebf45729

Artifact 8820695386
= lingji-windows-0.1.0-3e24e65c
= head_sha 3e24e65ce12bfa22b5c9193d65500648ebf45729
```

任何身份变化立即 `BLOCKED_WRONG_IDENTITY`。

### 4.2 临时目录

当前任务唯一临时根：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-3e24e65c
```

若存在，先执行：

```powershell
python scripts/cleanup_acceptance_workspace.py `
  --task-id PR60-MEMORY-QUALITY-TRIAL-3E24E65C `
  --target D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-3e24e65c
```

确认 dry-run 只包含当前任务目录后，再追加 `--execute`。

还必须确认旧目录不存在：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877
D:\codex\LingJiAcceptance\PR60-1c514877
```

若旧 `d69874af` 目录仍存在，只能使用旧任务 ID `PR60-MEMORY-QUALITY-TRIAL-D69874AF` 的安全清理策略，先 dry-run 后执行。不得手工强删或扩大白名单。

### 4.3 环境保护

开始前：

- 确认 8766、8767 空闲；
- 确认没有遗留 LingJi、Sidecar 或孤儿 MCP 进程；
- 备份 `%LOCALAPPDATA%\LingJi\desktop-bootstrap.json`，若不存在则记录不存在；
- 记录现有 LingJi 安装版本，不卸载；
- 不修改 Production DataRoot、Production Vault、正式 SQLite 或 Qdrant；
- 不读取主人真实 `CODEX_HOME` 内容。

## 5. Artifact 下载与核验

只下载 Artifact `8820695386`。

必须依次验证：

```text
Artifact ZIP SHA256：649de2e03bde0ec491f8c828fdfac73d1a9539877c72ecd5199c7be407ee0e98
Installer SHA256：21d87149844b8fd7ccf4d8e8b05923bbccf1338573aa6e189202571ef769caa1
Portable SHA256：bcb1af32c1dbcd9d0d25147c0f3bc11e5835ef9025d121a7cc5e7dfd0b3b9fc0
Sidecar SHA256：866c80420b99ff7935814755957e4bbf7b8df2c7492063db0af3ae0fffd7a489
Manifest SHA256：518a0ec991b064704e8d55a3999451f32c22a6225021370cd0917c699b58466c
```

`build-metadata.json` 必须显示：

```text
commit = 3e24e65ce12bfa22b5c9193d65500648ebf45729
version = 0.1.0
channel = pr
installer_format = nsis
signed = false
```

任一不符立即停止。

## 6. Day 0 安装与隔离启动

1. 使用固定 Installer 覆盖安装，不卸载旧版本。
2. 首次启动选择非 C 盘验收根：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-3e24e65c\product
workspace = acceptance
```

3. 不允许使用 Production Workspace。
4. UI、Runtime、Sidecar 和 MCP 均只连接当前验收 DataRoot。
5. 不自动下载模型，不自动重建 Production Qdrant。
6. 若出现黑色控制台窗口、错误指向 Production、数据根落到 C 盘或旧版本身份，立即 FAIL。

## 7. Day 0 必验项目

### 7.1 首屏与唯一下一步

主人打开页面后，必须能在不阅读日志的情况下回答：

```text
现在系统处于什么状态？
当前唯一下一步是什么？
哪个问题阻塞了继续？
点击后会读取或修改什么？
```

同一页面不得同时展示多个互相竞争的主要动作。

### 7.2 主动发现与授权提示

扫描完成后必须主动展示：

- 发现了哪些 AI 软件或历史目录；
- 路径或来源类型；
- 近似数量或可用范围；
- 当前仅扫描元数据，尚未读取正文；
- 支持导入什么、不支持导入什么；
- `预览/授权继续` 与 `暂不处理` 两个明确选择。

不得只显示一个模糊“导入”按钮，让主人猜它会吞进去什么。

### 7.3 Codex 三层状态

页面必须分别显示：

```text
配置目录：已发现 / 未发现
codex 命令：可用 / 未找到
真实 MCP 调用：已验证 / 尚未验证 / 失败
```

禁止出现以下矛盾：

```text
“已设置，等待测试”
同时又显示“未找到 codex 命令”
```

缺少命令时状态必须是 `blocked`，不得显示 ready。只有真实 CLI/MCP 调用成功才可显示 ready。

### 7.4 真实 Codex MCP 调用

使用隔离的临时 `CODEX_HOME` 或等效配置副本，不读取或修改主人真实 Codex 配置正文。

必须完成至少一次真实 MCP 调用：

- Codex能看到 LingJi 工具；
- 调用命中当前验收 Runtime；
- 返回合成测试资料中的确定答案；
- 鉴权失败、错误端口或错误 DataRoot 不得算 PASS；
- 调用结束后恢复主人原配置或删除临时副本。

### 7.5 Embedding 与 Qdrant 状态

页面必须分别展示：

- 配置的 Embedding 模型；
- 当前实际激活模型；
- 缺失或不可用模型；
- 最近一次错误；
- Qdrant 模式与服务状态；
- collection/index 是否存在；
- 是否需要重建；
- 当前影响：全文检索是否仍可用、语义检索是否不可用；
- 可执行的下一步入口。

不得再用“配置存在但尚未激活，后续从向量中心处理”一句话把所有问题塞进同一个抽屉。

### 7.6 候选审核边界

只使用合成测试资料：

- 生成至少两个候选；
- 主人亲自批准一个；
- 主人亲自拒绝一个；
- 批准前 Core Memory 不增加；
- 拒绝项不进入永久记忆；
- UI必须明确显示来源、内容、目标层级和后果。

### 7.7 生命周期

必须验证：

- Core/Sidecar 连续重启3次；
- Desktop关闭并重新打开；
- Windows重启一次；
- 重启后无黑窗；
- Runtime、8766/8767、Workspace、DataRoot、Vault和候选状态恢复正确；
- 不得污染 Production。

## 8. 主人检查点

Codex必须在以下位置暂停并等待主人实际观察：

```text
Checkpoint A：覆盖安装、首次打开、无黑窗、唯一下一步清楚。
Checkpoint B：扫描结果主动解释来源、范围和授权边界。
Checkpoint C：Codex 三层状态一致，真实 MCP 调用成功。
Checkpoint D：Embedding/Qdrant 问题与下一步能一眼看懂。
Checkpoint E：批准一个候选、拒绝一个候选，后果正确。
Checkpoint F：Windows重启后恢复正常。
```

主人未明确给出每个检查点 PASS 前：

```text
day0_result 不得写 PASS
real_data_authorized 必须为 false
stage1_result / stage2_result 必须为 NOT_RUN
```

## 9. Stage 1 授权规则

只有同时满足以下条件才允许进入 Stage 1：

```text
Day 0 自动检查 PASS
Checkpoint A-F 主人确认 PASS
主人明确写出允许读取的真实资料清单
主人明确授权进入 Stage 1
```

首次真实资料范围最多：

- 1部明确授权剧本；
- 1份明确授权 Codex 报告；
- 少量明确授权 ChatGPT 历史；
- 1个明确授权 Obsidian 目录。

不得自动扩展到其他目录。Stage 1 无 P0/P1 后，才允许另行授权 Stage 2，最多扩展到10部剧本和其他明确授权资料。

## 10. 质量门禁

Stage 1 至少20道质量题：

```text
精确事实 >= 8
跨文档比较 >= 4
来源核验 >= 4
负面边界 >= 4
主人抽查 >= 10
```

阈值：

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP真实调用成功率 >= 95%
重复正式内容 = 0
Production污染 = 0
人工审核链成功率 = 100%
```

剧本人物、剧情、台词和世界观不得进入主人个人事实。不存在的信息必须回答未知，不能拿相似资料冒充。

## 11. 报告、回执与清理

报告分支：

```text
acceptance/pr60-memory-quality-trial-3e24e65c
```

必须提交并远程复读：

```text
docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_3e24e65c.md
docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_3e24e65c.json
docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_3e24e65c.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
PR #60 评论
```

不得上传安装包、数据库、Token、私人正文、真实路径清单、node_modules、dist或未脱敏日志。

任务结束后：

- 恢复或删除临时 Codex 配置；
- 恢复原 `desktop-bootstrap.json`；
- 清理当前任务临时根，先 dry-run 再 `--execute`；
- 解除 worktree登记；
- 确认无 LingJi/Sidecar/MCP进程和8766/8767监听；
- `D:\codex\LingJiAcceptance` 共享父目录允许保留；
- 不删除主人明确选择保留的授权资料副本，除非主人明确要求。

## 12. 本轮首次回复格式

完成自动准备并到达第一个主人检查点后，回复：

```text
PR60 Day 0 已到主人检查点
task_id: PR60-MEMORY-QUALITY-TRIAL-3E24E65C
产品 Commit: 3e24e65ce12bfa22b5c9193d65500648ebf45729
Artifact: 8820695386 / lingji-windows-0.1.0-3e24e65c
当前阶段: Day 0
当前检查点: A / B / C / D / E / F
自动检查: PASS / FAIL / BLOCKED
需要主人观察: <具体页面和动作>
真实资料读取: 0
Stage 1: NOT_RUN
```
