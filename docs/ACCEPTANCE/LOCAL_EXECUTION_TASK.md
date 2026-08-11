# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达当前任务的唯一权威入口。
>
> 当前不是再次 M5 验收。`171091fe...` / Artifact `9102748834` 已在真实 M5 上 **FAIL**，禁止重复安装、重复验收或只换包不修根因。

## 1. 当前任务元数据

```yaml
task_id: PR88-M5-PHASE4-FAILURE-REPAIR-171091FE
status: ACTIVE
execution_mode: FAILURE_REPORT_FIRST_THEN_ROOT_CAUSE_REPAIR
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 171091fe764c6653cdc7325b4a1a71e0b7800822
artifact_name: REJECTED-lingji-macos-arm64-171091fe
artifact_id: 9102748834
report_branch: acceptance/pr88-m5-phase4-failure-repair-171091fe
report_path: docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_SUMMARY.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_HASHES.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
failed_m5_task: MACOS-M5-AUTOPILOT-PHASE4-171091FE
failed_workflow_run_id: 31495013820
failed_dmg_sha256: 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
retry_same_artifact: false
physical_reacceptance_before_new_artifact: false
source_failure_report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
source_failure_report_branch: acceptance/macos-m5-autopilot-phase4-171091fe
```

## 2. 当前结论

主人已确认 2026-08-11 本轮 M5 复验结束，结论为 **FAIL，不是 BLOCKED**。

三类阻断：

```text
M5-IDENTITY-002   安装包 / 已安装 App 身份不精确
M5-UX-003         首次使用体验仍不清晰
M5-ISOLATION-002  错误写入 ~/Documents/acceptance
```

主人已完成现场收尾：

```text
新版本停止
8766/8767及相关后台进程关闭
本轮测试数据清理到废纸篓
旧的有效签名 /Applications/灵机.app 已恢复
```

**不得要求主人重新执行这些动作。**

## 3. 第一硬门禁：先读真实失败报告

Codex 在修改任何产品代码前，必须读取本机刚生成的 Phase 4 M5 失败报告与最小证据。

预期：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
acceptance/macos-m5-autopilot-phase4-171091fe
```

ChatGPT 已重新读取 GitHub 远程，当前事实是：

```text
预期 Phase 4 acceptance 分支：远程未发现
预期 MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md：master / 产品分支未发现
GitHub acceptance refs：只有旧 c10d255 / bf9da9ff 等历史分支
```

所以 Codex 不得继续把“执行过 git push”当成“报告已经在远程”。

### 开发前必须完成

1. 只读盘点本机仓库：路径、当前分支、HEAD、origin、`git status`、`git log`、`git reflog`、未推送提交、worktree；
2. 找到本机失败报告，读取全文；
3. 从报告中提取三个阻断的 `observed / expected / evidence / exact path / exact SHA`；
4. 若报告尚未真正到远程，先把报告、必要脱敏证据和对应 FAIL 回执提交到正确 acceptance 分支；
5. push 后执行 `git ls-remote` + `gh api` / GitHub API 重新读取远程分支、Commit、报告原文；
6. 在 PR #88 留与失败报告 Commit 对应的 FAIL 评论；
7. 只有 `remote_failure_report_verified=true` 后才能修改产品代码。

若本机报告不存在，不得凭记忆伪造。只能依据仍存在的最小日志、终端历史、reflog 与已知现场事实重建，并在报告中明确标记 `reconstructed=true`。

## 4. 修复循环

固定顺序：

```text
失败报告
→ 根因定位
→ 最小修复
→ 覆盖真实失败路径的自动回归
→ 焦点测试
→ 全量 Python/Desktop/Rust
→ P0 Windows + Windows Release
→ macOS Release Gate
→ 新精确产品 Head
→ 新 Artifact / 新哈希
→ 更新 M5 任务
→ 才允许重新真机验收
```

禁止：

- 只改预期值或文案让测试变绿；
- 把错误 observed SHA 改成“正确答案”；
- 在测试中豁免 `~/Documents/acceptance`；
- 重试 Artifact `9102748834`；
- 只换 Artifact 而不新增本次失败回归；
- force push / reset --hard / clean -fdx；
- 删除未知 worktree、主人数据或第三方 AI 配置；
- 新增第二套 Runtime、数据库、队列或 Mac 专用业务分叉。

## 5. 修复 A：精确安装包身份

以失败报告的实际证据为准，先回答：

```text
expected product SHA 是什么
workflow checkout SHA 是什么
.app 内 release metadata SHA 是什么
最终 DMG 内 App SHA 是什么
安装到 /Applications 后 App/UI/diagnostics SHA 是什么
真正运行的主程序与 Sidecar 分别来自哪个 bundle
```

重点检查但不得先入为主：

```text
.github/workflows/macos-desktop.yml
Tauri build-time release metadata 注入
.app 与 DMG 是否发生二次构建
release_metadata Tauri command
安装 whole-bundle replace 后真实启动路径
Sidecar 与主程序身份来源
CI target/cache/旧 bundle 是否可能污染最终 DMG
```

### 必须新增回归

新的 macOS Gate 不能只做 `strings | grep`。

从**最终 DMG 挂载后的 App**至少验证：

```text
release_metadata.commit == expected product Head
主程序 == arm64
Sidecar == arm64 且来自同一 App bundle
DMG 内 App 与 build 前 verified App 身份一致
安装/复制后的 App 可自动验证部分仍返回同一精确 SHA
```

任何身份字段出现 PR merge commit、master docs commit、旧产品 SHA、unknown 或彼此不一致，Release Gate 必须 FAIL。

## 6. 修复 B：首次体验

先把失败报告里主人的实际观察逐条转成 UI 回归，不允许开发者自己猜“应该已经够清楚”。

目标正常路径只有：

```text
打开灵机
→ 灵机自动准备
→ 自动解决可恢复问题
→ 进入首页
→ 首页只告诉主人是否有必须决定的事情
```

正常首次启动不得要求主人理解：

```text
DataRoot
Workspace / production / acceptance
Qdrant
Embedding
SQLite
8766 / MCP
bootstrap
路径策略
```

只有自动准备真实失败时才出现**一个主要恢复动作**；手选路径和技术详情必须降为次级/折叠兜底。

重点检查：

```text
desktop/lingji-control/src/components/RuntimeBoundary.tsx
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/pages/OverviewPage.tsx
DesktopShell / 首次启动状态栏 / 可见错误文案
```

### 必须新增回归

- fresh bootstrap 正常路径无手选目录主流程；
- 正常路径不暴露 acceptance/workspace/DataRoot 等技术术语；
- 自动准备失败时只有一个清晰主动作，高级路径选择折叠；
- booting → healthy → Overview 不出现互相矛盾的状态；
- 首页无主人事项明确“无需操作”；
- error/degraded 不得同时冒充“正常/已准备好”。

## 7. 修复 C：`~/Documents/acceptance` 越界写入

失败报告必须给出实际路径、生成时间和尽量精确的写入来源。

沿真实启动链追：

```text
LINGJI_ACCEPTANCE_DATA_ROOT
runtime_bootstrap.rs
RuntimeManager 子进程环境
run_packaged_control_api.py
src/runtime/workspace.py
Settings 默认值 / fallback
验收脚本自身是否产生该目录
```

当前代码已经声明 task-scoped override，因此不能再靠写文档解决。必须找到**哪个实际路径绕过了合同**。

### 必须新增 macOS 隔离集成回归

```text
HOME=<isolated-home>
LINGJI_ACCEPTANCE_DATA_ROOT=<task-root>/runtime-data
启动与正式打包 Runtime 等价的 bootstrap + sidecar 链
```

验证：

```text
SQLite/Qdrant/log/raw/vault/backup/runtime/token 全在 task root
<isolated-home>/Documents/acceptance 不存在
任务根外新增 LingJi acceptance 路径数量 = 0
首次启动 PASS
再次启动 PASS
```

只测纯函数不算关闭本缺陷。

## 8. 双平台回归边界

不得破坏：

```text
Windows NSIS / RuntimeManager
Windows 既有 DataRoot 合同
8766 loopback + token
MCP 8767 / stdio
Autopilot Doctor-Repair-Verify
永久记忆人工确认
Qdrant destructive action人工确认
真实 AI 正文授权
Production DataRoot / Vault
```

Mac 与 Windows 继续共享同一业务核心。

## 9. 自动测试顺序

先跑焦点：

```text
身份专项
bootstrap / acceptance isolation Rust
Desktop first-run smoke
Autopilot tests
packaged runtime tests
```

焦点全部通过后再跑：

```text
Python 3.11 / 3.12 full
Windows Python
Desktop full smoke + React build
Rust/Tauri
MCP / Obsidian / browser smoke
acceptance-doc-sync
local-execution-handoff
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
```

所有远程门禁必须绑定同一个最终产品 Head。

## 10. 新 Artifact 门禁

三项根因和全量门禁全部 PASS 后才能创建新 M5 包。

必须记录全新的：

```text
product_commit
macOS workflow_run_id
macOS artifact_id
Artifact ZIP sha256
DMG sha256
DMG size
Windows artifact identity
```

Codex 必须下载新 Artifact，独立核对 ZIP/DMG 哈希，并从最终 DMG 内真实读取 App release metadata。

以下旧身份永久拒绝：

```text
171091fe764c6653cdc7325b4a1a71e0b7800822
Artifact 9102748834
DMG 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
```

## 11. 报告与清理

开发过程中更新：

```text
docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_SUMMARY.json
docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_HASHES.txt
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/MODULES/CODE_MAP.md（入口/所有权变化时）
docs/CHANGELOG.md
PR #88 body/comment
```

每个重大修改完成后更新 Markdown 报告，不堆临时报告和无用日志。

清理只允许删除本轮明确创建的临时 worktree、build output、fixture、日志和测试 DataRoot；禁止删除主人 Production、Vault、正式记忆和第三方应用配置。

## 12. 完成条件

只有以下全部成立才可把结果回执标记 `COMPLETED`：

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
cleanup_before = PASS
cleanup_after = PASS
remote_result_verified = true
pr_comment_verified = true
PR #88 = Draft / DO_NOT_MERGE
```

开发完成后，Codex只把 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 原地更新为**新精确 Artifact**并重新设为 ACTIVE；不得自行宣称真实 M5 PASS。
