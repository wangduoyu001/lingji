# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务。不得从旧聊天、旧报告、本机残留目录或旧 Artifact 推断额外要求。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-24F35704
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: 24f3570440437f57b6a62e54d409577ed40b6c14
artifact_name: lingji-windows-0.1.0-24f35704
artifact_id: 8832010437
artifact_zip_sha256: ac3c329e85e35b17fa35c92f68f415a58905e544b8325de42e557171f35fcd45
installer_name: LingJi_0.1.0_windows_x64_setup.exe
installer_sha256: e89a10c12d08d0ddb910233d6c7d366f50e509a975ce6506f0cf3b80772368ce
portable_name: LingJi_0.1.0_windows_x64.exe
portable_exe_sha256: 5139cef2771124c6609c85acc154a10d9db1c77b06e0ed4deefd5fac16d8341f
sidecar_exe_sha256: 4cbf0a62a1f5667ec22e36c2e347f4a113c05eb4217eaa48801c960450061b03
manifest_sha256: 077e07851431d4eeece773a1734a98c0816fe62067dbe78487d1276e6b46e182
build_metadata_sha256: fd32179b943ed88fe6d3ebb09f345846913b2f7b956cb55fc9dedb26248fb6c0
artifact_workflow_run_id: 30743102197
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_branch: acceptance/pr60-memory-quality-trial-24f35704
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_24f35704.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_24f35704.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_24f35704.txt
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

## 2. 当前唯一产品身份

只允许使用：

```text
Product Head：24f3570440437f57b6a62e54d409577ed40b6c14
Artifact：lingji-windows-0.1.0-24f35704
Artifact ID：8832010437
Workflow：Windows Desktop Release Baseline / run 30743102197
```

精确 Head 已通过：

```text
local-execution-handoff / run 30743102211
acceptance-doc-sync / run 30743102181
tests / run 30743102183
P0 Windows Gate / run 30743102202
Windows Desktop Release Baseline / run 30743102197
```

旧提交和 Artifact，包括 `3739c42f / 8831573426`、`1860fa17 / 8830371064`、`4161807c / 8821878623`、`b68711fd / 8830090726` 以及更早版本，均为失败或被替代身份，禁止下载、安装、复验或从其报告推断行为。

PR #60 必须保持 Draft，不得合并到 master。

## 3. 产品工作方式

本轮不是让主人逐项点击菜单。验收目标是：

```text
灵机主动发现
→ 主动检查
→ 自动执行低风险可逆动作
→ 自动入队、去重、刷新、重试和恢复
→ UI 展示状态、证据、进度、阻塞与授权边界
→ 只在读取真实正文、修改外部客户端、永久记忆或不可逆操作时请求主人决定
```

Codex负责安装、启动、窗口操作、API调用、截图、日志、重启、报告、Git提交、远程复读和清理。主人只负责：

1. 观察 UI 是否一眼可懂；
2. 明确授权读取任务生成的合成导出包；
3. 指定一个合成候选批准、一个合成候选拒绝；
4. 明确允许 Windows 重启；
5. Day 0 全部 PASS 后，另行授权具体真实资料范围。

主人不得被要求手工填写路径、手工刷新状态、手工执行命令、手工上传报告或手工清理目录。

## 4. 开始前清理

### 4.1 使用修复后的清理工具

先建立精确产品 Commit 的只读/隔离 worktree，并从该 worktree调用：

```text
scripts/cleanup_acceptance_workspace.py
```

禁止使用旧 master 中可能尚未包含 `DRY_RUN_READY` 修复的脚本。

### 4.2 清理上一轮失败根

目标：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-3739c42f
```

任务身份：

```text
PR60-MEMORY-QUALITY-TRIAL-3739C42F
```

先 dry-run。合法结果必须是：

```text
status = DRY_RUN_READY
authorized = true
next_action = rerun_with_execute
```

确认清单只在该唯一任务根下后，自动追加 `--execute`。最终必须：

```text
status = PASS
next_action = cleanup_complete 或 nothing_to_remove
目标目录不存在
相邻目录与主人数据未变化
```

不得因为 dry-run列出待删除项就标记 `BLOCKED`，也不得绕过脚本手工强删。

### 4.3 环境保护

开始前必须：

- 关闭旧 LingJi Desktop；
- 清空遗留 LingJi、Sidecar、MCP进程；
- 确认 8766、8767 空闲；
- 记录现有安装版本；
- 备份全局 bootstrap并记录哈希或“不存在”；
- 不读取主人真实 `CODEX_HOME`、ChatGPT、剧本、Vault或其他私人正文；
- 不修改 Production DataRoot、Production Vault、SQLite或 Qdrant。

## 5. 当前任务隔离环境

唯一任务根：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-24f35704
```

产品 DataRoot：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-24f35704\product
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

使用任务专属启动绑定契约，必须锁定：

- 精确 DataRoot；
- `acceptance` workspace；
- 唯一 binding id；
- 非 C盘；
- 不允许 UI覆盖；
- 不允许回退全局 bootstrap；
- 不允许接管外部 Runtime。

## 6. Artifact核验与覆盖安装

只下载 Artifact `8832010437`，依次验证任务 YAML 中全部哈希。

`build-metadata.json` 必须显示：

```text
schema_version = 5
version = 0.1.0
commit = 24f3570440437f57b6a62e54d409577ed40b6c14
channel = pr
target = x86_64-pc-windows-msvc
installer_format = nsis
signed = false
first_run_configuration_required = false
automatic_safe_non_system_drive_selection = true
startup_binding_contract_supported = true
runtime_binding_identity_required = true
external_runtime_adoption_allowed = false
owner_authorization_required_for_real_content = true
c_drive_runtime_data_allowed = false
```

覆盖安装，不卸载主人数据。身份不符立即 `BLOCKED_WRONG_IDENTITY`。

## 7. Day 0 自动执行与门禁

### 7.1 首次恢复

Codex启动 Desktop并计时。必须在 45 秒内同时满足：

- 8766鉴权健康；
- 8767 MCP可用；
- Desktop显示 Runtime ready；
- Runtime ping反向证明精确 DataRoot和 workspace；
- 无黑色控制台窗口；
- 无 Production路径；
- 无第二个 MCP/Qdrant拥有者。

超过45秒、第一轮失败后依赖第二轮人工重试，均记 Day 0 FAIL。

### 7.2 合成导出包和自动发现

只在隔离 `USERPROFILE\Downloads` 创建：

1. 一个格式有效、内容明确的合成 ChatGPT Export；
2. 一个格式有效、内容明确的合成 Codex Work Report；
3. 一个无关 JSON 和一个无关 ZIP作为负面样本。

合成内容不得复制主人真实资料，只能包含虚构项目、虚构偏好和确定性答案。

灵机必须自动扫描元数据：

- 只识别两个受支持导出包；
- 不把无关 JSON/ZIP列为候选；
- 不向前端暴露绝对路径；
- 不跟随符号链接；
- 未授权前正文读取数为0。

### 7.3 一步导入

发现候选后 UI必须只提供一个主要动作：

```text
授权最近导出包并开始导入
```

主人在聊天中明确授权合成包后，Codex代为触发 UI或受控 API。必须：

- 一次授权后立即进入正式采集队列；
- 不再出现路径输入；
- 不再出现第二个“提交导入”；
- 自动展示处理、去重、完成或失败重试；
- 不自动写 Core Memory。

另用一个受支持但未被自动发现的合成文件验证：选择文件后立即入队，不得二次提交。

Claude Code和 WorkBuddy等无正式历史适配器的来源只显示边界说明，不得展示无效导入按钮。

### 7.4 Codex命令与真实 MCP

必须在隔离环境下验证：

1. 枚举确定性 PATH/PATHEXT/npm候选；
2. 若 `WindowsApps\codex.exe` 返回 Access Denied，自动跳过；
3. 继续选择可启动的 `codex.cmd`、`codex.exe`或其他合法 PATH候选；
4. UI分别显示：
   - 配置状态；
   - 候选存在；
   - 实际命令可启动；
   - 最终选中命令；
   - 真实客户端注册状态；
5. 真实执行 `codex mcp list`，必须列出 `lingji-memory`；
6. 完成至少一次真实 Codex MCP调用，命中当前验收 Runtime并返回合成资料中的确定答案。

没有可启动候选、真实命令被拒绝、未列出 `lingji-memory`、错误端口、错误 DataRoot或鉴权失败，均为 Day 0 FAIL。不得用配置文件存在代替真实成功。

### 7.5 Qdrant与检索真相

必须验证 MCP是 SQLite/Qdrant唯一实时拥有者：

```text
runtime/memory-owner.lock = OS互斥
runtime/memory-owner.json = 可读诊断
```

Control API只能读取 MCP发布的 `memory_status.json`，不得再次打开同一嵌入式 Qdrant目录。

状态必须一致：

- 尚无向量：`empty / collection_empty`；
- `semantic_search_available = false`；
- `lexical_search_available = true`；
- 不得显示 healthy；
- 导入和索引完成后，向量数量、Collection、覆盖率、Embedding和语义检索可用性必须相互一致；
- 不得出现 `ready + 0 vectors`；
- 不得出现 Control显示正常、MCP显示目录被锁；
- 快照过期不得宣称语义检索可用。

### 7.6 合成候选审核

从合成资料生成至少两个候选：

- 主人明确指定一个批准；
- 主人明确指定一个拒绝；
- Codex代为执行 UI动作；
- 批准前 Core Memory不增加；
- 拒绝项不得进入永久记忆；
- UI显示来源、候选内容、目标层级和后果。

### 7.7 生命周期

自动验证：

- Core/Sidecar/MCP连续重启3次；
- Desktop关闭再打开；
- 每轮在预算内恢复；
- 8766/8767、DataRoot、workspace、binding、owner lock和候选状态正确；
- 无孤儿进程；
- 无 Production污染。

在 Windows重启前只向主人请求一次许可。重启后自动继续并验证同一状态。

## 8. 主人检查点

Codex只在以下位置暂停：

```text
A：首启在45秒内恢复，UI状态、DataRoot和当前动作清楚。
B：合成导出包已自动发现；请求主人授权读取并导入。
C：一键导入、Codex真实MCP和Qdrant状态一致；展示证据。
D：请求主人指定一个候选批准、一个拒绝。
E：请求主人允许 Windows重启。
F：重启恢复、清理和远程报告完成；展示最终证据。
```

主人未明确确认 A-F 前：

```text
day0_result 不得为 PASS
real_data_authorized 必须为 false
stage1_result = NOT_RUN
stage2_result = NOT_RUN
```

## 9. Stage 1边界

Day 0与主人检查点全部 PASS 后，Codex必须停止。只有主人另行给出**明确命名的真实资料范围**，才可进入 Stage 1。

未经授权，禁止读取真实剧本、ChatGPT内容、Codex Session/JSONL、Obsidian正文或其他私人正文。

质量阈值仍按 YAML执行：至少20道质量题、主人抽查至少10道、质量分不低于90%、来源准确率不低于95%、误报率不高于5%、Codex MCP成功率不低于95%、重复正式内容0、Production污染0。

## 10. 结束清理

报告第一次远程确认后，使用精确产品 Commit中的修复脚本清理：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-24f35704
```

先 dry-run，必须为 `DRY_RUN_READY`；随后自动 `--execute`，最终目标不存在。不得让主人手工删除。

同时删除本轮 Artifact副本、安装包、日志、截图、fixture、checkpoint、临时配置、worktree和合成导出包；恢复原 bootstrap哈希或原不存在状态。不得删除主人正式数据或其他任务目录。

## 11. 提交与远程复读

Codex必须：

1. 创建 `acceptance/pr60-memory-quality-trial-24f35704`；
2. 写入报告、公开摘要、公开哈希和结果回执；
3. push；
4. 使用远程 API重新读取分支、Commit、报告、回执和 PR #60评论；
5. 完成清理；
6. 更新回执并再次 push；
7. 再次远程复读；
8. PR #60保持 Draft。

报告不得包含 Token、私人正文、完整主人路径清单、数据库、安装包、node_modules、dist或未脱敏日志。

## 12. 最终判定

Day 0 PASS至少要求：

- 新 Artifact身份和全部哈希一致；
- 首次恢复不超过45秒；
- DataRoot绑定正确；
- 自动发现和一步导入成立；
- Codex选到可启动命令并完成真实 MCP调用；
- Qdrant单一所有权和状态一致；
- 合成候选批准/拒绝边界正确；
- Windows重启恢复；
- Production污染0；
- 真实资料读取0；
- 清理前后PASS；
- 主人检查点A-F明确PASS；
- 远程报告、回执和评论全部复读确认。

任一P0失败立即停止。不得进入 Stage 1，不得把“最终恢复了”替代首轮时限失败，也不得把“状态解释得更清楚”替代功能真正可用。
