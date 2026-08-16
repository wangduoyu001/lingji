# LingJi 本机执行任务单

> **当前状态：ACTIVE / READY FOR M5 REACCEPTANCE。**
>
> 本文件是本机 Codex 的唯一当前任务入口。只允许执行下方精确产品 Commit 与 Artifact；任何历史 Artifact、历史报告或聊天指令都不能替代本任务。

## 1. 当前任务身份

```yaml
task_id: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
status: ACTIVE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
artifact_name: lingji-macos-arm64
artifact_id: 9258682849
artifact_workflow_run_id: 31928631105
artifact_zip_sha256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_sha256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
windows_artifact_name: lingji-windows-0.1.0-bd1e7a17
windows_artifact_id: 9258675881
windows_artifact_workflow_run_id: 31928631101
windows_artifact_zip_sha256: 0696ae6615d8afc44f46efc264fd7852e7d971866efc1285f2397d87a36ce4b1
windows_nsis_sha256: b9341ae7982375cac1a771ad7082b8ba76014b60c4a1c300de5791ce77a84339
windows_portable_sha256: 2435fcbfbc0e211c76c64ec5556c9f36fef84c12cd603c421ef0607c8da5f3b3
report_branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_SUMMARY_bd1e7a17.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_HASHES_bd1e7a17.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
task_root: $HOME/LingJiAcceptance/PR88-M5-OWNER-WORKBENCH-V4-bd1e7a17
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
same_sha_artifacts_required: true
secret_export_count_required: 0
production_pollution_count_required: 0
retry_rejected_artifact: false
```

## 2. 自动产品门禁已锁定

以下六道门均在精确产品 SHA `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9` 上 PASS：

```text
tests: 31928631115
P0 Windows Gate: 31928631099
macOS Desktop Gate: 31928631105
Windows Desktop Release Baseline: 31928631101
acceptance-doc-sync: 31928631103
local-execution-handoff: 31928631118
```

macOS Gate 已自动验证：精确源码身份、原生 arm64、Rust 单测、App Bundle、内嵌产品身份、packaged Sidecar、认证 Control API、DMG 生成与挂载、安装 App 的 Acceptance 隔离。

Windows Release 已自动验证：同 SHA 构建元数据、Desktop smoke、Rust Runtime manager、packaged Python Runtime、认证 health + managed stop、NSIS、checksum 与 Artifact contract。

自动门禁不能替代主人真机体验结论。

## 3. 开始前

严格按以下顺序读取：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/ACCEPTANCE/README.md
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前 V4 条目
docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

执行开始前完成只读盘点、Apple Silicon 门禁、Gatekeeper、已有灵机 App、LingJi 进程、8766/8767、任务根和 Production/Acceptance 隔离检查。

只清理**确认属于本任务**的旧临时材料与进程。不得删除 Production DataRoot、Vault、正式记忆、AI 客户端配置或归属不明文件。

## 4. Artifact 硬门禁

本轮 macOS 只能下载：

```text
Artifact 9258682849
lingji-macos-arm64
ZIP SHA256 c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
DMG SHA256 a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
Product bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
```

必须再次验证 ZIP、DMG、DMG 内 App release metadata、arm64、strict codesign 与安装后身份。

以下历史 macOS Artifact 永久禁止重跑：

```text
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

发现身份或哈希不一致立即 `BLOCKED_WRONG_IDENTITY`，不得换旧包继续。

## 5. 安装与数据隔离

使用 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md` 的 whole-bundle replace 流程，不允许 overlay copy。

所有本轮 Acceptance 数据只能进入：

```text
$HOME/LingJiAcceptance/PR88-M5-OWNER-WORKBENCH-V4-bd1e7a17
```

以及该任务根下明确创建的 runtime-data / fixture / logs / evidence / backup 等子目录。Production 只允许只读检查，除非主人明确批准写入。

若 FAIL，停止本任务精确 Runtime、释放本任务端口、删除失败 App、整体恢复旧 App 备份并复核签名。若 PASS，按协议保留新 App，远程报告确认后再清理临时备份。

## 6. V4 主人体验核心验收

本轮不是验证“页面有没有新颜色”，而是验证 Owner Workbench 是否真的解决上轮四个 P1。

### M5-V4-001 · 第一眼主人简报

首次进入日常首页后，主人应在几秒内无需理解 Runtime、Qdrant、PID、端口或技术状态，就能回答：

```text
现在有没有事情必须由我决定？
灵机刚刚真正替我做了什么？
灵机现在正在做什么？
接下来灵机会做什么？
记忆最近发生了什么变化？
```

首页必须是主人简报，不能退化成监控仪表盘、七阶段大卡或技术指标墙。

### M5-V4-002 · 一级导航与日常路径

日常一级导航必须清晰可理解：

```text
首页 / 记忆 / 工作 / 需要我 / 高级
```

技术诊断、模型、向量、任务队列、日志、存储等不得重新占据主人日常一级路径。

### M5-V4-003 · 第二永久记忆大脑可直接检查

“记忆”一级页面必须让主人看到真实记忆对象，而不是只显示“有 N 份资料”。至少验证：

- 可以浏览真实记忆列表；
- 搜索/筛选会真实改变结果；
- 选中对象后可以读懂记忆内容/摘要与状态；
- 可以看到来源/证据链；
- 没有证据时明确说未知，不使用通用模板猜来源；
- 记忆为空时说明为什么空、系统是否会继续、主人是否需要操作；
- `下一页` 只能在后端明确证明存在下一页时可用。

### M5-V4-004 · “需要我”只有真实对象

“需要我”不得把计数、普通故障、技术告警或空页面伪装成主人待办。

必须实际验证：

- 每个可点击待办都有真实对象 ID；
- 候选永久记忆必须绑定真实 `memory_id`；
- 正文读取授权必须绑定真实 `candidate_id`；
- 不可逆维护必须有明确原因和边界；
- 没有真实对象时不得显示“去处理/审核”按钮；
- 页面未知时显示未知，不伪装成“0 待办”。

### M5-V4-005 · 候选记忆精确直达

从首页或“需要我”点击某一条候选永久记忆：

```text
真实 memory_id
→ 进入人工记忆审核
→ 自动打开同一个 memory_id 的详情
```

不得只跳到审核列表让主人二次寻找，更不得打开空页面。

### M5-V4-006 · 工作履历

“工作”必须用主人能理解的方式回答：

```text
发生了什么
灵机做了什么
结果是什么
下一步是什么
下一执行者是谁
```

技术 trace 可以展开查看，但不能代替主人语言。

### M5-V4-007 · 全局记录入口

验证 `Cmd/Ctrl + K`：

- 可以打开全局入口；
- `记住：<真实测试文本>` 必须进入正式 Capture 流程并可追踪；
- 导航意图必须真实跳页；
- 尚未实现的开放式 Agent 指令必须明确说“不支持/未执行”，不得假装成功；
- 测试内容只能进入 Acceptance。

### M5-V4-008 · 分页终点

逐个验证受影响页面：

```text
记忆
人工记忆审核
Memory Inspector
Capture Center
```

当后端 `has_more=false` 时，“下一页”必须不可用；当后端没有 `has_more` 且没有可证明 total 时，也必须保守停止，不得用“本页刚好满了”猜下一页存在。

### M5-V4-009 · 主动发现与自动化可见但不打扰

验证支持来源的主动发现：

- 系统可以自动识别支持的 AI 工具/资料元数据；
- 未授权正文不得读取；
- 需要正文权限时只产生对象级授权待办；
- 已授权后的排队、去重、整理、索引由灵机继续自动处理；
- 没有真实动作时首页不得制造“系统很忙”的假动态。

### M5-V4-010 · 高级信息下沉

PID、端口、Commit、DataRoot、模型、向量、日志等技术信息应放在“高级”或显式展开区。主人日常页面不得要求理解这些信息才能操作。

## 7. Window Recovery 必测

上轮为 `NOT_TESTED`，本轮不得遗漏。主人必须肉眼确认三条路径均能把主窗口带回当前屏幕/前台：

```text
菜单：窗口 → 将灵机带到当前屏幕
快捷键：Cmd/Ctrl + Shift + L
macOS Dock Reopen
```

任何一条未执行写 `NOT_TESTED`，最终不得 PASS。

## 8. 技术安全回归

在 V4 UX 验收之外，必须保持：

```text
identity_result: PASS
arm64_result: PASS
strict_codesign_result: PASS
acceptance_isolation_result: PASS
auth_status_boundary_result: PASS
secret_export_count: 0
production_pollution_count: 0
```

认证状态可以显示脱敏 AuthStatus，但 Secret、Token、Cookie、Authorization、Secret 路径/长度和私人绝对路径不能进入公开证据。

Production 不得被测试污染。

## 9. Runtime 两轮生命周期

至少完成两轮：

```text
启动 → authenticated health → 保存当前 Sidecar PID → 精确 stop → state 消失 → PID 消失 → 8766 释放
```

第一轮 stop **必须在停止前保存 Sidecar PID**，并在 stop 后同时证明：

```text
state gone
saved PID gone
127.0.0.1:8766 free
```

第二轮重复启动/精确停止，确认没有重复 Core、孤儿 MCP 或残留监听。

禁止全局 kill Python/Node/Codex。

## 10. 主人结论优先级

主人必须肉眼判断：

- 第一眼是否知道自己要不要做事；
- 首页是否终于能看懂；
- “记忆”是否像一个可检查的第二永久记忆大脑；
- “工作”是否能解释真实结果和下一步；
- “需要我”是否只出现真的需要主人决定的对象；
- UI 是否与上一版有明显、可感知的产品级差异；
- 是否仍存在空按钮、无限分页、空待办、假动态或看不懂的技术信息。

任一 P0/P1 主人体验失败：

```text
status: COMPLETED
verdict: FAIL
merge: DO NOT MERGE
Artifact 9258682849: DO NOT RETRY
PR #88: KEEP DRAFT
```

自动测试不得覆盖主人明确的 FAIL。

## 11. 报告、远程回执与清理

验收报告分支固定：

```text
acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
```

只允许添加/更新验收报告与脱敏证据，不得修改产品代码。

必须提交：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_SUMMARY_bd1e7a17.json
docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_HASHES_bd1e7a17.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

报告必须使用 `REPORT_TEMPLATE.md` 结构，明确自动检查、主人观察、技术安全、生命周期、Window Recovery、回滚/保留新 App 和未测试项。

第一次 push 后必须从远端重新确认：报告分支、报告 Commit、报告、summary、hashes、结果回执与 PR #88 评论均可读取。

最后完成安全清理，再更新/提交 cleanup receipt，并再次远程复读。

PASS 只允许在：

```text
V4 主人体验全部 PASS
+ Window Recovery 全部 PASS
+ 技术安全全部 PASS
+ 两轮生命周期 PASS
+ secret_export_count=0
+ production_pollution_count=0
+ 报告/PR 回执/清理全部闭环
```

时成立。
