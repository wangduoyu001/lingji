# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达当前任务的唯一权威入口。
>
> 当前不是再次 M5 验收。旧产品 `171091fe...` / Artifact `9102748834` 已在真实 M5 上 **FAIL**，永久禁止重试。
>
> **本任务现在切换为一次性 Closeout 模式：从读取本文件开始，Codex 必须连续执行到“新的精确 M5 Artifact 已准备好”或出现无法自行解决的真实外部阻断。阶段性进展只写仓库，不得作为停止条件。**

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
source_failure_report_branch: acceptance/pr88-m5-phase4-failure-repair-171091fe
auth_sync_contract_path: docs/AUTH_CREDENTIAL_STATE_SYNC.md
auth_state_sync_required: true
secret_export_count_required: 0
single_pass_closeout_required: true
intermediate_owner_updates_forbidden: true
intermediate_artifacts_forbidden: true
stop_only_on_new_artifact_or_external_blocker: true
```

## 2. 已确认事实，不得重复做

真实 M5 失败结论已经远程闭环：

```text
physical verdict = FAIL
failed product commit = 171091fe764c6653cdc7325b4a1a71e0b7800822
failed artifact id = 9102748834
failed DMG sha256 = 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
failure report branch = acceptance/pr88-m5-phase4-failure-repair-171091fe
failure report content commit = 602d5326e8990796e8e9206f82d6fd9a37366adc
failure report remote verification commit = 36421dba21b3f36040493119a062988b77129c37
PR #88 FAIL / DO NOT MERGE comment id = 5254742686
```

三个真实缺陷仍是：

```text
M5-IDENTITY-002   安装包 / 已安装 App 身份不精确
M5-UX-003         首次使用体验仍不清晰
M5-ISOLATION-002  错误写入 ~/Documents/acceptance
```

主人已完成失败现场收尾：旧失败 Runtime 已停止、8766/8767 已释放、测试数据已清理、旧有效签名 `/Applications/灵机.app` 已恢复。不得要求主人重复这些动作。

## 3. 已完成开发检查点，不得从头重做

### UX 检查点

已完成：

```text
手动选择资料目录不再与“自动准备”并列
手动路径选择降为高级兜底
对应 UI 回归先 FAIL、修复后 PASS
前端构建 PASS
```

这只是已完成开发检查点。只有统一最终产品 Head + 完整 CI + 新 Artifact 通过后，才可把 `first_run_ux_root_cause_fixed=true`。

### Identity 检查点

已发布修复链：

```text
fix/pr88-m5-phase4-171091fe
90b7a70de2a5053c1224ee810949256a378f582a
```

macOS Gate 已改为从最终 DMG 挂载后的真实 App 导出 release metadata，并验证：

```text
metadata.commit == exact product Head
主程序 arm64
Sidecar arm64 且来自同一 App bundle
build 前 App metadata == 最终 DMG App metadata
不再仅依赖 strings | grep
```

当前环境曾缺少 cargo，所以该检查点不能单独宣称 Identity 已关闭。最终统一 Head 必须由 CI 真正跑 Rust/Tauri 与 macOS Gate。

### Isolation 检查点

当前连续修复分支：

```text
fix/pr88-m5-isolation-171091fe
latest verified head = 41a4ba832ab9253ec3bfb53fad89578cdfdfb79f
```

已完成：

```text
Sidecar acceptance 模式存在 LINGJI_ACCEPTANCE_DATA_ROOT 时必须精确使用同一目录
不同 data_root 直接拒绝
对应回归先 FAIL、修复后 PASS
```

并已发布最终 DMG Desktop 启动链 Gate：

```text
挂载最终 DMG
→ 启动真实 App 主程序
→ 注入 isolated HOME + task-scoped LINGJI_ACCEPTANCE_DATA_ROOT
→ 等待 8766 token + authenticated ping
→ 停止
→ 第二次启动
→ 再次 authenticated ping
→ 检查 runtime-data
→ 检查 isolated HOME/Documents/acceptance 不存在
```

该 Gate 尚未在真实 macOS CI 上 PASS，所以 `M5-ISOLATION-002` 仍未关闭。

## 4. 一次性 Closeout 执行规则

从现在开始，不再采用：

```text
修一个点
→ 停下来给主人汇报
→ 等“继续”
→ 再修下一个点
```

改为：

```text
继续隔离真实链验证
→ 实现最小安全 CredentialStore / AuthStatus
→ 整合 UX + Identity + Isolation + Auth
→ 建立一个统一候选产品 Head
→ 跑焦点测试
→ 跑全量双平台 CI / Release
→ 自动分析红灯并修复
→ 重新跑直到全部 Gate PASS
→ 锁定最终产品 Head
→ 生成新的 macOS / Windows Artifact
→ 下载 Artifact 并独立复核
→ 更新报告 / 回执 / M5 固定任务单
→ 才结束本轮开发任务
```

### 中途不得停止的情况

以下都不是停止理由：

- 某一个焦点测试 PASS；
- 某一个修复分支已经 push；
- 前端 build PASS；
- 没有本地 cargo，但 GitHub macOS/Windows CI 可继续验证；
- 某一个 CI job 红灯，但日志足以定位并继续修；
- 已实现 CredentialStore 但尚未跑 Release；
- 已生成中间 commit；
- 已写阶段性报告。

### 只有两种允许结束

**A. READY_FOR_M5_REACCEPTANCE**

必须已经有新的精确产品 Head、新 macOS Artifact、新 Windows Artifact、所有要求 Gate PASS、哈希与最终 DMG metadata 独立复核完成，并更新 M5 固定任务单。

**B. BLOCKED_EXTERNAL**

仅限 Codex 无法自行解决的真实外部阻断，例如：

```text
GitHub 权限/认证实际失效且无法恢复
CI 平台长期不可用
需要主人真实 Keychain / Credential Manager 交互且系统不给非交互路径
需要主人做不可替代的物理视觉判断
```

如果属于 B，必须先完成所有不依赖该阻断的工作，并在结果回执中写清：`blocker / attempted / remaining / exact owner action`。不得用“环境没有 cargo”作为阻断，因为正式 Rust/Tauri 可交给远程 CI。

## 5. 剩余任务 A：完整关闭 M5-ISOLATION-002

当前不要继续堆纯函数测试。使用已经发布的最终 DMG Desktop 首启/二启 Gate 作为核心证据。

必须让真实 macOS Gate 证明：

```text
HOME=<isolated-home>
LINGJI_ACCEPTANCE_DATA_ROOT=<task-root>/runtime-data
最终 DMG App 主程序真实启动
Sidecar 真实启动
8766 authenticated ping PASS
首次启动 PASS
第二次启动 PASS
SQLite/Qdrant/log/raw/runtime/token 等均位于 task root
<isolated-home>/Documents/acceptance 不存在
任务根外新增 LingJi acceptance 路径数量 = 0
```

如果真实 Gate FAIL：直接读取日志追 `RuntimeManager → bootstrap → child env → packaged Sidecar → workspace/settings fallback`，最小修复后重跑。不得先生成 Artifact 交给主人试错。

## 6. 剩余任务 B：一次完成认证状态安全同步

权威规范：`docs/AUTH_CREDENTIAL_STATE_SYNC.md`。

永久原则：

```text
Secrets never sync. Secret state syncs.
```

仓库审计已经确认没有现成 CredentialStore/AuthStatus，因此实现**最小跨平台抽象**，禁止过度设计。

目标：

```text
macOS Keychain / Windows Credential Manager
→ CredentialStore interface
→ 本机认证验证
→ lingji_state.db 只存非敏感 AuthStatus
→ Desktop / Health / Autopilot 只显示结论
→ allowlist sanitized snapshot
→ GitHub 只保存认证状态
```

CredentialStore 只负责 Secret 的 get/set/delete/exists 与标准错误映射；Provider 不得各自创建 Secret 文件。

统一状态至少支持：

```text
not_configured
credential_present
verifying
verified
expired
permission_insufficient
invalid
error
```

`lingji_state.db` 只允许：

```text
provider
auth_method
state
credential_present
credential_valid
permissions_ok
account_bound
last_verified_at
expires_at
last_error_code
last_error_at
```

严禁进入 SQLite / JSON / Markdown / Git / 日志：

```text
Token
Refresh Token
API Key
Cookie
Authorization Header
密码
Secret 片段
Secret hash / fingerprint
```

CI 使用 fake / in-memory backend，不操作真实系统凭据。真实 Keychain / Credential Manager 只留给最终本机验收验证。

必须生成：

```text
docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_PR88.json
```

采用 allowlist schema，禁止先 dump 全对象再 redact。

至少回归：

```text
CredentialStore fake backend get/set/delete/exists/error
AuthStatus 状态转换
Runtime 重启恢复非敏感状态
snapshot allowlist
fake Token/Cookie/Authorization Header 不得进入 snapshot
仓库 evidence secret scan
Desktop 只展示“已连接/需重新认证/权限不足”等结论
Windows / macOS 使用同一状态模型
```

硬门禁：

```text
secret_export_count = 0
```

发现疑似 Secret 时，快照生成 / 提交 / 验收必须 FAIL。

## 7. 统一候选产品 Head

完成剩余实现后，把已有：

```text
UX 修复
Identity 修复
Isolation guard + 最终 DMG Desktop Gate
CredentialStore / AuthStatus / sanitized snapshot
```

收敛到**一个新的产品候选 Head**。不得保留互相漂移的多条发布候选分支，不得 force push，不得引入 Mac 专用业务分叉。

统一 Head 产生后，后续所有自动门禁、Windows Artifact、macOS Artifact、报告和哈希都必须绑定这一 SHA。

## 8. 测试与自动修红灯循环

先跑焦点：

```text
Identity 专项
Desktop first-run smoke
packaged acceptance isolation
Autopilot
packaged runtime
CredentialStore / AuthStatus / snapshot / secret scan
```

然后完整执行：

```text
Python 3.11 / 3.12 full
Windows Python
Desktop full smoke + React production build
Rust/Tauri
MCP / Obsidian / browser smoke
acceptance-doc-sync
local-execution-handoff
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
```

如果任何 Gate FAIL：

```text
读取失败 job / logs
→ 判断产品缺陷还是过期测试合同
→ 最小修复
→ 增加/更新回归
→ 形成新统一 Head
→ 重跑受影响焦点
→ 重跑最终全量 Gate
```

不得为了绿灯删除真实失败回归或降低验收标准。

## 9. 新 Artifact 硬门禁

只有全部成立才允许创建/认定新 M5 包：

```text
identity_root_cause_fixed = true
first_run_ux_root_cause_fixed = true
acceptance_isolation_root_cause_fixed = true
three_real_failure_regressions = PASS
auth_state_sync_implemented = true
auth_status_regressions = PASS
auth_snapshot_generated = true
secret_export_count = 0
full_ci = PASS
windows_release = PASS
macos_release = PASS
```

必须记录全新的：

```text
product_commit
macOS workflow_run_id
macOS artifact_id
Artifact ZIP sha256
DMG sha256
DMG size
Windows artifact identity
auth_snapshot_path
secret_export_count = 0
```

Codex 必须下载新 Artifact 独立核对 ZIP/DMG 哈希，并从最终 DMG 内真实 App 导出 release metadata，确认等于最终产品 Head。

以下旧身份永久拒绝：

```text
171091fe764c6653cdc7325b4a1a71e0b7800822
Artifact 9102748834
DMG 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
```

## 10. 安全与双平台边界

不得破坏：

```text
Windows NSIS / RuntimeManager
Windows DataRoot 合同
8766 loopback + token
MCP 8767 / stdio
Autopilot Doctor-Repair-Verify
永久记忆人工确认
Qdrant destructive action 人工确认
真实 AI 正文授权
Production DataRoot / Vault
```

禁止：

```text
force push / reset --hard / clean -fdx
删除未知 worktree/主人数据/第三方 AI 配置
把 Secret 写入仓库或 lingji_state.db
自动批准永久记忆
自动执行 destructive Qdrant rebuild
新增第二套 Runtime / DB / Queue
为了 Mac 修复破坏 Windows
```

## 11. 报告与进度规则

阶段性进展仍需写仓库，但**只作为 checkpoint，不作为停止点**：

```text
docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md
docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_SUMMARY.json
docs/TEST_REPORTS/evidence/PR88_M5_PHASE4_FAILURE_REPAIR_HASHES.txt
docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_PR88.json
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/MODULES/CODE_MAP.md（入口/所有权变化时）
docs/CHANGELOG.md
PR #88 body/comment
```

每个大功能/大段代码测试完成后更新 Markdown 报告。不要创建大量临时报告。

## 12. 完成条件

只有以下全部成立，结果回执才可标记 `COMPLETED`：

```text
source_failure_report_read = true
remote_failure_report_verified = true
identity_root_cause_fixed = true
first_run_ux_root_cause_fixed = true
acceptance_isolation_root_cause_fixed = true
three_real_failure_regressions = PASS
auth_state_sync_implemented = true
auth_status_regressions = PASS
auth_snapshot_generated = true
secret_export_count = 0
full_ci = PASS
windows_release = PASS
macos_release = PASS
new_exact_product_head = recorded
new_artifact_id = recorded
new_artifact_hashes_verified = true
old_artifact_retry = false
cleanup_before = PASS
cleanup_after = PASS
remote_branch_verified = true
remote_commit_verified = true
remote_report_verified = true
remote_result_verified = true
pr_comment_verified = true
local_temp_root_absent = true
PR #88 = Draft / DO_NOT_MERGE
```

完成开发后：

1. 原地更新 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 为**新的精确 Artifact**并设为 ACTIVE；
2. 不得自行宣称真实 M5 PASS；
3. 最终只向主人回报“新 M5 验收包已准备好 + 固定任务链接”，不再提交阶段性请求让主人决定是否继续。
