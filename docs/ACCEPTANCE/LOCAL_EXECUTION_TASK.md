# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务。不得从旧聊天、旧报告、本机残留目录或旧 Artifact 推断额外要求。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-4161807C
status: ACTIVE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: 4161807ce4598cc1696093da4a703de101648280
artifact_name: lingji-windows-0.1.0-4161807c
artifact_id: 8821878623
artifact_zip_sha256: c1019006509033a45debf24fd5530133cda2a804d051424a66a0c3d122c680ab
installer_name: LingJi_0.1.0_windows_x64_setup.exe
installer_sha256: 219c5866ad22b5a1b6e6ea0d78c02fb2b4a392548d3cb9b360a236d9d6bdf931
portable_name: LingJi_0.1.0_windows_x64.exe
portable_exe_sha256: c49c46f32d9b4e52c0e32754c16b4bf8f67cfb9a7d61d90ea782a2a524508210
sidecar_exe_sha256: 76c36cd02735afd556ebdfd9a0af4ebf0a8879eaccb56dc1252f1ea8466b9d20
manifest_sha256: 50168354b918f318a71677892c4d5fd6e6dc85cbdf18ae0599d31bf12d61f368
build_metadata_sha256: 73726765d1293d0a4ef7b3e72150208da98919abfaf53c7a681b35181c1a75a2
artifact_workflow_run_id: 30710872683
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_branch: acceptance/pr60-memory-quality-trial-4161807c
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_4161807c.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_4161807c.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_4161807c.txt
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

## 2. 产品原则

本轮不是让主人按按钮驱动工作流。目标是验证：

```text
灵机主动发现
→ 主动检查
→ 主动执行可逆低风险动作
→ 自动重试与恢复
→ UI持续展示状态、进度、DataRoot、阻塞和证据
→ 只有读取真实正文、修改外部客户端配置、永久记忆或不可逆操作时请求主人决定
```

菜单必须保留，作为查看、授权、诊断和手动干预入口；不得把菜单存在误解成主人必须逐项操作。

## 3. 固定远程身份

必须精确确认：

```text
origin/feature/unified-ai-memory-connectors
= 4161807ce4598cc1696093da4a703de101648280

Artifact 8821878623
= lingji-windows-0.1.0-4161807c
= head_sha 4161807ce4598cc1696093da4a703de101648280
```

精确 Head 已通过：

```text
local-execution-handoff #101
acceptance-doc-sync #135
tests #1189
P0 Windows Gate #262
Windows Desktop Release Baseline #144
```

旧产品提交 `1c514877`、`d69874af`、`3e24e65c` 与 Artifact `8723868744`、`8762312712`、`8820695386` 均为历史失败身份，禁止下载、安装或复验。

PR #60 必须保持 Draft，整个 Day 0 与 Stage 1 完成前不得合并。

## 4. 阶段边界

```text
Day 0：合成资料、隔离配置、元数据扫描、自动运行与恢复验证。
Stage 1：仅在 Day 0 PASS 且主人明确授权一个具名真实资料范围后执行。
Stage 2：Stage 1 PASS 后才允许扩大授权范围。
```

Day 0 前和过程中：

- 真实资料正文读取数必须为 0；
- 不得读取真实剧本、ChatGPT正文、Obsidian正文或 Codex Session/JSONL；
- 允许只读安装状态、已知目录存在性、类型、支持状态和近似数量；
- 不得自动修改主人真实 Codex/Claude/WorkBuddy 配置；
- 不得自动下载模型或重建 Production Qdrant；
- 不得自动批准永久记忆。

## 5. 唯一临时根与安全清理

唯一任务目录：

```text
D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-4161807c
```

若存在，先执行 dry-run：

```powershell
python scripts/cleanup_acceptance_workspace.py `
  --task-id PR60-MEMORY-QUALITY-TRIAL-4161807C `
  --target D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-4161807c
```

清单只能包含该任务目录。确认后追加 `--execute`。不得手工强删、不得删除共享父目录、不得扩大白名单。

开始前确认：

- 8766、8767 空闲；
- 无 LingJi、Sidecar、MCP 遗留进程；
- 旧任务专属目录均不存在；
- 主工作区原有未跟踪文件不得修改；
- Production DataRoot、Vault、SQLite、Qdrant 不得读取或修改。

## 6. Artifact 下载与复核

只下载 Artifact `8821878623`，逐项验证：

```text
ZIP：c1019006509033a45debf24fd5530133cda2a804d051424a66a0c3d122c680ab
Installer：219c5866ad22b5a1b6e6ea0d78c02fb2b4a392548d3cb9b360a236d9d6bdf931
Portable：c49c46f32d9b4e52c0e32754c16b4bf8f67cfb9a7d61d90ea782a2a524508210
Sidecar：76c36cd02735afd556ebdfd9a0af4ebf0a8879eaccb56dc1252f1ea8466b9d20
Manifest：50168354b918f318a71677892c4d5fd6e6dc85cbdf18ae0599d31bf12d61f368
build-metadata.json：73726765d1293d0a4ef7b3e72150208da98919abfaf53c7a681b35181c1a75a2
```

`build-metadata.json` 必须包含：

```text
schema_version = 5
commit = 4161807ce4598cc1696093da4a703de101648280
version = 0.1.0
channel = pr
installer_format = nsis
signed = false
automatic_safe_non_system_drive_selection = true
startup_binding_contract_supported = true
runtime_binding_identity_required = true
external_runtime_adoption_allowed = false
owner_authorization_required_for_real_content = true
```

任一不符立即停止。

## 7. 启动契约与物理隔离

### 7.1 创建任务启动契约

在任务目录创建：

```text
startup-binding.json
```

内容必须为：

```json
{
  "schema_version": 1,
  "binding_id": "PR60-MEMORY-QUALITY-TRIAL-4161807C",
  "data_root": "D:\\codex\\LingJiAcceptance\\PR60-MEMORY-TRIAL-4161807c\\product",
  "workspace": "acceptance"
}
```

### 7.2 隔离 Desktop 小配置

记录主人原始文件是否存在及 SHA256，但不得打开其内容：

```text
%LOCALAPPDATA%\LingJi\desktop-bootstrap.json
```

启动安装版 Desktop 时，使用任务专属进程环境：

```text
LOCALAPPDATA=D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-4161807c\localappdata
APPDATA=D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-4161807c\appdata
LINGJI_BOOTSTRAP_CONTRACT_FILE=D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-4161807c\startup-binding.json
```

不得修改主人全局 bootstrap。结束时其存在状态和 SHA256 必须与开始前一致。

### 7.3 安装与启动

- 使用固定 Installer 覆盖安装，不卸载主人数据；
- 安装过程不得自动启动无契约 Desktop；优先使用 NSIS 静默安装；
- 安装后由 Codex在上述任务专属环境中启动 Desktop；
- 不要求主人手动选择目录、启动核心、点击扫描或逐项刷新；
- 若启动契约无效、8766被占用、Runtime根不匹配或 workspace错误，必须阻断，不得退回旧 bootstrap。

## 8. Day 0 自动验收

Codex负责自动完成以下低风险动作并记录证据：

### 8.1 DataRoot 身份自证

必须同时满足：

```text
UI expected DataRoot = 任务 product 根
UI actual DataRoot = 任务 product 根
UI workspace = acceptance
UI binding source = startup_contract
UI binding id = PR60-MEMORY-QUALITY-TRIAL-4161807C
UI binding verified = true
/api/runtime/ping binding_contract_version = 1
/api/runtime/ping data_root = 任务 product 根
/api/runtime/ping workspace = acceptance
```

只验证端口、Token或HTTP 200不得算 PASS。

### 8.2 自动工作行为

不经过主人点击，连接后必须自动执行并在 UI显示进度：

- AI软件与允许历史目录元数据扫描；
- 模型状态刷新；
- 硬件与运行能力刷新；
- Runtime启动与身份核验；
- 状态轮询、失败重试和自动恢复；
- 已授权合成资料的解析、去重、排队与进度更新。

UI必须明确展示：

- 灵机当前正在做什么；
- 已完成项目；
- 失败或后台重试项目；
- 精确 DataRoot、workspace、绑定来源与验证结果；
- 哪一项正在等待主人授权或决定。

### 8.3 UI定位

必须观察到：

```text
菜单完整存在；
日常入口表达为查看状态、查看进度、查看授权或手动干预；
不存在“主人必须按1→2→3逐项操作”的流程；
不存在“扫描我的AI软件”作为启动必需按钮；
不存在“唯一推荐下一步”把主人当工作流引擎；
```

### 8.4 Codex三层状态与真实MCP

页面分别展示：

```text
配置目录状态
codex命令状态
真实MCP调用状态
```

只有真实调用成功才可显示 ready。使用隔离临时 `CODEX_HOME` 或等效副本，完成至少一次真实 MCP 调用，命中当前 acceptance Runtime并返回合成资料的确定答案。不得读取或修改主人真实 Codex配置正文。

### 8.5 Embedding与Qdrant

页面必须分别显示配置模型、实际激活模型、缺失模型、最近错误、Qdrant模式/服务、collection/index、是否需重建、全文检索影响、语义检索影响和自动修复进度。

禁止恢复模糊文案：

```text
配置存在但尚未激活；全文检索仍可用，后续从向量中心处理
```

### 8.6 合成候选与永久记忆边界

Codex自动创建至少两个合成候选并展示来源、内容、目标层级和后果，但不得自行批准或拒绝。

到达此处后暂停，只请求主人给出一次明确决定，例如：

```text
候选A批准，候选B拒绝
```

主人作出决定后，Codex代为执行并验证：

- 批准前 Core Memory不增加；
- 批准项进入正确层级；
- 拒绝项不进入永久记忆；
- UI结果清晰可观察。

### 8.7 生命周期

Codex自动完成：

- Core/Sidecar连续重启3次；
- Desktop关闭并在同一任务环境重新打开；
- 每次恢复后重新验证DataRoot身份；
- 无黑窗、无Production污染、状态和候选正确恢复。

Windows重启属于中断性操作，执行前只请求主人一次明确许可。获准后由Codex执行重启并继续验证，不要求主人手动恢复服务。

## 9. 主人观察点

主人不是操作员，只需观察和决定。Codex在自动部分完成后集中提供一份可读摘要，并等待以下确认：

```text
Checkpoint A：UI显示灵机主动运行，精确DataRoot/工作空间/绑定验证清楚；没有要求我逐项启动、扫描或刷新。
Checkpoint B：自动扫描和进度可见；读取真实正文前确实停在授权边界。
Checkpoint C：Codex三层状态一致，真实MCP调用成功。
Checkpoint D：Embedding/Qdrant原因、影响与自动处理进度一眼可懂。
Checkpoint E：主人给出候选A/B决定，Codex执行后结果正确。
Checkpoint F：主人授权Windows重启后，灵机自动恢复且绑定身份不漂移。
```

主人未明确确认 A-F 前：

```text
day0_result 不得写 PASS
real_data_authorized 必须为 false
stage1_result / stage2_result 必须为 NOT_RUN
```

## 10. Stage 1

只有 Day 0 与 A-F 全部 PASS 后，Codex才可请求一个具名、最小化真实资料授权范围。未收到主人明确授权时保持：

```text
real_data_authorized: false
stage1_result: NOT_RUN
stage2_result: NOT_RUN
```

授权后按 `docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md` 执行至少20道质量题、主人抽查至少10道，并满足既定质量阈值。不得自行扩大授权范围。

## 11. 报告、远程复读与清理

报告分支：

```text
acceptance/pr60-memory-quality-trial-4161807c
```

提交并远程复读：

```text
docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_4161807c.md
docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_4161807c.json
docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_4161807c.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
PR #60 评论
```

禁止提交安装包、数据库、Token、私人正文、真实路径全集、node_modules、dist或未脱敏日志。

第一次远程复读成功后：

- 停止任务创建的进程和监听；
- 删除任务专属 Artifact、安装包、启动契约、临时配置、fixture、日志、截图和worktree；
- 使用安全清理工具删除任务唯一临时根；
- 共享父目录允许保留；
- 不删除主人全局 bootstrap、Production数据或其他任务目录；
- 更新结果回执后再次push并远程复读。

## 12. 失败与阻塞规则

以下任一情况立即停止，不得继续到真实资料：

```text
身份或哈希不匹配
启动契约退回旧bootstrap
实际DataRoot或workspace不匹配
未托管外部Runtime被接管
主人全局bootstrap变化
自动扫描读取了真实正文
UI仍要求主人逐项驱动常规工作
真实MCP命中错误Runtime
Production污染
安全清理拒绝且无法按任务规则解决
```

最终回复格式：

```text
PR60 自治 Day 0
任务: PR60-MEMORY-QUALITY-TRIAL-4161807C
当前阶段: 自动执行 / 等待主人观察与决定 / Stage 1
Day 0: PASS / FAIL / BLOCKED / RUNNING
产品 Commit: 4161807ce4598cc1696093da4a703de101648280
Artifact: 8821878623
实际 DataRoot: <路径>
绑定验证: PASS / FAIL
自动动作: <完成摘要>
等待主人: <仅授权或决定事项>
真实资料读取: 0 / <授权后数量>
报告分支: acceptance/pr60-memory-quality-trial-4161807c
```
