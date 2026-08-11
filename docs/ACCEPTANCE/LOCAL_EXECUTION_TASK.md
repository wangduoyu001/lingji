# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达当前开发任务的唯一权威入口。
>
> 当前任务不是再次验收。`171091fe...` / Artifact `9102748834` 已在真实 M5 上 FAIL，禁止重复安装或重复验收同一包。

## 1. 当前任务身份

```yaml
task_id: PR88-M5-PHASE4-FAILURE-REPAIR-171091FE
status: ACTIVE
execution_mode: FAILURE_REPORT_FIRST_THEN_ROOT_CAUSE_REPAIR
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
failed_product_commit: 171091fe764c6653cdc7325b4a1a71e0b7800822
failed_artifact_name: lingji-macos-arm64
failed_artifact_id: 9102748834
failed_workflow_run_id: 31495013820
failed_dmg_sha256: 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
failed_m5_task: MACOS-M5-AUTOPILOT-PHASE4-171091FE
product_status: FAIL_DO_NOT_MERGE
retry_same_artifact: false
physical_reacceptance_before_new_artifact: false
source_report_expected_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
source_report_expected_branch: acceptance/macos-m5-autopilot-phase4-171091fe
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
implementation_report_path: docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
```

## 2. 已知现场结论

主人已确认本轮 M5 复验结束，结论为 **FAIL，不是 BLOCKED**。

已知三类阻断：

```text
M5-IDENTITY-002
安装包 / 已安装 App 的真实身份未满足精确产品 Commit 合同。

M5-UX-003
首次使用体验仍不清晰，不能让普通主人无需理解技术概念直接进入可用状态。

M5-ISOLATION-002
本轮错误写入了任务根之外的 ~/Documents/acceptance。
```

现场已经完成：

```text
新版本停止
8766/8767及相关后台进程关闭
本轮测试数据清理到废纸篓
旧的有效签名 /Applications/灵机.app 已恢复
```

不得要求主人重新执行以上步骤。

## 3. 第一步硬门禁：先恢复并读取真实失败报告

Codex 在修改任何产品代码前必须先读取本机刚生成的 Phase 4 M5 失败报告、相关最小证据和本机 Git 状态。

预期报告：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
```

预期报告分支：

```text
acceptance/macos-m5-autopilot-phase4-171091fe
```

### 当前远程事实

ChatGPT 已在 2026-08-11 对 GitHub 远程做了重新读取：

```text
预期 Phase 4 acceptance 分支：未发现
预期 MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md：master / 产品分支均未发现
GitHub acceptance refs 中只有旧 c10d255 / bf9da9ff 等历史分支
远程最新 M5 相关 docs commit 仍为 f0fde9c1（Phase 4任务单）
```

因此 Codex 不得继续宣称“已推送”而不复读远程。

### Codex 必须执行

1. 找到本机刚生成的失败报告，确认文件内容、mtime、Git status、当前分支、HEAD、reflog、未推送提交；
2. 读取报告全文，提取三个阻断的**实际 observed / expected / evidence / exact path / exact SHA**；
3. 若报告确实还没有到远程：只提交报告、必要脱敏证据和失败结果回执到正确 acceptance 分支；
4. `git push` 后必须用 `git ls-remote` + GitHub API/`gh api` 重新读取远程分支、Commit 和报告原文；
5. 在 PR #88 留一条与该报告 Commit 对应的 FAIL 评论；
6. 只有 `remote_report_verified=true` 后才能修改产品代码。

如果本机报告不存在或已经被误删，不得凭记忆编造证据。使用当前仍存在的最小日志、终端历史、Git reflog 和已知现场事实重建一份**明确标注 reconstructed** 的报告，再远程提交。

## 4. 修复原则

固定流程：

```text
真实失败报告
→ 根因定位
→ 最小修复
→ 针对真实失败路径的自动回归测试
→ 焦点测试
→ 全量 Python / Desktop / Rust
→ Windows P0 + Windows Release
→ macOS Release Gate
→ 新精确产品 Head
→ 新 Artifact / 新哈希
→ 更新 M5 任务单
→ 才允许重新真机验收
```

禁止：

- 只改文案或预期值让测试变绿；
- 把观察到的错误 Commit 改成“正确预期”；
- 在测试里豁免 `~/Documents/acceptance`；
- 用旧 Artifact 重新验收；
- 只换 Artifact 不增加覆盖本次真实失败的回归测试；
- 破坏 Windows 已通过的共享主线；
- 新增第二套 Runtime、队列、状态库或 Mac 特供业务逻辑。

## 5. 阻断 A：安装包精确身份

先以失败报告中的真实值为准确认：

```text
expected product SHA
artifact workflow source SHA
.app embedded/release metadata SHA
安装后 UI / diagnostics SHA
实际运行 Sidecar / App 来源
codesign identity / bundle path
```

必须定位“CI 为什么认为 exact-head PASS，而真实安装后仍显示/运行错误身份”的根因。

重点检查但不要预设结论：

```text
.github/workflows/macos-desktop.yml
release metadata 的 Rust build-time 注入来源
Tauri .app / DMG 生成与二次构建路径
安装 whole-bundle replace 后实际启动的 bundle
Desktop release_metadata command
packaged Sidecar 与主程序各自身份来源
缓存 / target / 旧 bundle 是否可能进入最终 DMG
```

### 必须增加的回归

新的 macOS Gate 不能只对二进制做 `strings | grep`。

至少要从**最终 DMG 挂载后的 App**验证：

```text
1. 主程序真实 release_metadata.commit == workflow expected head SHA
2. 主程序架构 arm64
3. Sidecar 来自同一 bundle
4. DMG 内 App 与构建前 verified App 身份一致
5. 安装/复制后的 App 仍能返回同一精确 SHA（可自动验证的部分）
```

任何 identity 字段为 merge commit、master docs commit、旧产品 SHA、unknown 或彼此不一致：Release Gate 必须 FAIL。

## 6. 阻断 B：首次使用体验

首先把失败报告中的主人实际观察逐条转成 UI 回归断言，不得由开发者自己猜“这样应该够清晰”。

目标体验固定为：

```text
打开灵机
→ 灵机自动准备
→ 能自动解决的自己解决
→ 直接进入首页
→ 首页只告诉主人现在是否需要做决定
```

正常首次启动不得要求主人理解或选择：

```text
DataRoot
Workspace / production / acceptance
Qdrant
Embedding
SQLite
8766 / MCP
路径策略
bootstrap
```

只有自动准备真实失败时才出现一个清晰兜底动作；技术详情默认折叠。

重点检查：

```text
desktop/lingji-control/src/components/RuntimeBoundary.tsx
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/pages/OverviewPage.tsx
DesktopShell / 状态栏 / 首次启动可见文案
```

### 必须增加的回归

- fresh bootstrap 时不出现手选目录主流程；
- 正常路径不出现 acceptance/workspace/DataRoot 等术语；
- 自动准备失败时只有一个主要恢复动作，高级路径选择折叠；
- 自动准备 → healthy → Overview 的状态切换无矛盾提示；
- 首页无主人事项时明确“无需操作”；
- 错误状态不得同时显示“正常/已准备好”。

## 7. 阻断 C：`~/Documents/acceptance` 越界写入

失败报告必须给出实际生成路径、生成时间和尽可能精确的写入来源。

重点沿以下链路追踪，但以真实证据为准：

```text
LINGJI_ACCEPTANCE_DATA_ROOT
runtime_bootstrap.rs
RuntimeManager 启动环境
run_packaged_control_api.py
WorkspaceResolver / Settings 默认值
所有 acceptance 默认目录 / fallback
测试脚本与验收脚本
```

当前产品代码已经有 task-scoped `LINGJI_ACCEPTANCE_DATA_ROOT` 合同，因此这次的目标不是再写一条“不要污染”的文档，而是找到**谁绕过了这个合同**。

### 必须增加的回归

建立 macOS 隔离集成测试：

```text
给定：HOME=<isolated-home>
     LINGJI_ACCEPTANCE_DATA_ROOT=<task-root>/runtime-data
启动：与正式打包 Runtime 等价的 bootstrap / sidecar 链
验证：SQLite/Qdrant/log/raw/vault/backup/runtime/token 全在 task root
验证：<isolated-home>/Documents/acceptance 不存在
验证：任务根外新增 LingJi acceptance 路径数量 = 0
```

测试必须覆盖首次启动和再次启动，不能只测纯函数。

## 8. 双平台与安全边界

这三项修复不得破坏：

```text
Windows NSIS / RuntimeManager
Windows 自动/手动 DataRoot 既有合同
8766 loopback + token
MCP 8767 / stdio合同
Autopilot Doctor-Repair-Verify
永久记忆人工确认
Qdrant destructive action人工确认
真实 AI 正文读取授权
Production DataRoot / Vault
```

Mac 与 Windows 必须继续共享同一业务核心，不创建 Mac 专用产品分叉。

## 9. 自动验收顺序

先跑焦点测试，失败就修，不要把红测试带进全量 CI。

至少：

```text
身份专项测试
bootstrap / acceptance isolation Rust tests
Desktop 首次体验 smoke
Autopilot tests
packaged runtime tests
```

焦点通过后执行：

```text
Python 3.11 / 3.12 full tests
Windows Python tests
Desktop full smoke + React production build
Rust/Tauri tests
MCP / Obsidian / browser smoke
acceptance-doc-sync
local-execution-handoff
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
```

所有门禁必须针对同一个**最终产品 Head**。

## 10. 新 Artifact 门禁

只有三项修复和全部自动门禁 PASS 后才能发新 M5 包。

必须产生全新的：

```text
product_commit
macOS workflow_run_id
artifact_id
artifact ZIP sha256
DMG sha256
DMG size
Windows artifact identity
```

Codex 必须下载自己刚生成的 macOS Artifact，再独立核对 ZIP/DMG 哈希和最终 DMG 内 App release metadata。

旧身份全部作废：

```text
171091fe764c6653cdc7325b4a1a71e0b7800822
Artifact 9102748834
DMG sha256 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
```

## 11. 文档要求

开发完成前必须新增/更新：

```text
docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/MODULES/CODE_MAP.md（若入口/所有权变化）
docs/CHANGELOG.md
PR #88 body/comment
```

实施报告必须分别写清：

```text
失败报告来源 Commit
三个根因
修改文件
新增回归测试
焦点测试结果
完整 CI run IDs
新 Artifact 身份与哈希
Windows 回归结果
剩余风险
```

## 12. 完成条件

本开发任务只有以下全部成立才可标记 `COMPLETED`：

```text
source_failure_report_read = true
remote_failure_report_verified = true
identity_root_cause_fixed = true
first_run_ux_root_cause_fixed = true
acceptance_isolation_root_cause_fixed = true
three_real_failure_regressions = PASS
full_ci = PASS
windows_release = PASS
macos_release = PASS
new_exact_product_head = recorded
new_artifact_id = recorded
new_artifact_hashes_verified = true
old_artifact_retry = false
PR88 = Draft / DO_NOT_MERGE
```

完成开发后，Codex只更新 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 为**新的精确 Artifact**并把状态切回 ACTIVE；不得自行把真实 M5 验收写成 PASS。
