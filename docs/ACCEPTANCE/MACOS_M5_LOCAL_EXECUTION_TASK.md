# LingJi macOS M5 当前真机验收任务单

> **这是当前 M5 真机验收的唯一执行入口。**
>
> 用户只需要把本文件链接交给 Codex。Codex 必须自行读取本文件中的任务身份、Artifact、验收协议、安装替换规则、隔离规则、清理规则和报告路径；禁止再次向用户索要已经写在这里的信息。
>
> 本文件采用“原地更新”策略：每轮新的 M5 验收直接覆盖当前任务身份，不为每个版本重复创建任务单。

## 0. 当前唯一任务身份

```yaml
status: ACTIVE
task_id: MACOS-M5-AUTOPILOT-PHASE4-65DE7292
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_commit: 65de729228b200869b118fd9c0798af6ad658bca
product_branch: feature/owner-autopilot-ui-codexpp
pull_request: 88
platform: macOS Apple Silicon
target: aarch64-apple-darwin
app_version: 0.1.0
bundle_format: dmg
artifact_name: lingji-macos-arm64
artifact_id: 9213728587
workflow_run_id: 31786165138
workflow_name: macOS Desktop Gate
workflow_result: success
artifact_archive_sha256: cf288e34bc8510540397489df9661fa72f8f4ec12ecfae14596a353e13ffeaa0
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46311297
dmg_sha256: 4666b0cda78baa81fc9150254f406f4c91faed520a2df850e4c8f52d2a1ff354
protocol_path: docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
implementation_report: docs/TEST_REPORTS/PR88_FINAL_ARTIFACT_CLOSEOUT.md
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_65de7292.md
report_branch: acceptance/macos-m5-physical-acceptance-65de7292
```

GitHub Actions Run：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31786165138
```

Artifact：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31786165138/artifacts/9213728587
```

PR：

```text
https://github.com/wangduoyu001/lingji/pull/88
```

被测产品身份必须始终保持：

```text
65de729228b200869b118fd9c0798af6ad658bca
```

本任务单和验收协议后续产生的文档 Commit **不改变被测产品 Commit**。

---

# 1. Codex 收到本链接后的固定读取顺序

```text
本文件
→ docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ PR #88 当前说明
→ feature/owner-autopilot-ui-codexpp @ 65de729 的相关代码与配置
→ docs/TEST_REPORTS/PR88_FINAL_ARTIFACT_CLOSEOUT.md
```

macOS 专项规则与通用规则冲突时，优先级固定为：

```text
MACOS_M5_LOCAL_EXECUTION_TASK.md
→ MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ 其他通用验收文档
```

**读完后直接执行，不再询问 task_id、commit、Artifact、DMG、临时目录、验收协议或报告路径。**

---

# 2. Artifact 必须由 Codex 自行取得

先创建唯一任务根：

```bash
export ACCEPTANCE_ROOT="$HOME/Library/Caches/LingJiAcceptance/MACOS-M5-AUTOPILOT-PHASE4-65DE7292-65de7292"
rm -rf "$ACCEPTANCE_ROOT"
mkdir -p "$ACCEPTANCE_ROOT/artifact" "$ACCEPTANCE_ROOT/logs" "$ACCEPTANCE_ROOT/app-backup" "$ACCEPTANCE_ROOT/runtime-data"
```

`rm -rf` 仅允许作用于上面**精确任务根**；执行前必须确认目标路径完全匹配当前 task_id，不允许通配符或扩大路径。

优先使用 GitHub CLI：

```bash
gh run download 31786165138 \
  -R wangduoyu001/lingji \
  -n lingji-macos-arm64 \
  --dir "$ACCEPTANCE_ROOT/artifact"
```

必须得到：

```text
$ACCEPTANCE_ROOT/artifact/灵机_0.1.0_aarch64.dmg
```

校验：

```bash
shasum -a 256 "$ACCEPTANCE_ROOT/artifact/灵机_0.1.0_aarch64.dmg"
```

期望：

```text
4666b0cda78baa81fc9150254f406f4c91faed520a2df850e4c8f52d2a1ff354
```

文件大小必须为：

```text
46311297 bytes
```

如果 GitHub Artifact 因鉴权无法下载：

1. 记录脱敏 `gh auth status`；
2. 尝试当前仓库已有 GitHub 认证；
3. 禁止改用旧 DMG；
4. 只有确认无法取得 **Artifact ID 9213728587** 时才标记：

```text
BLOCKED_ARTIFACT_DOWNLOAD_AUTH
```

此时才允许向用户索取 **同一个 Artifact ID 9213728587 对应的文件**。

---

# 3. 第一次操作前必须完成本机只读预检

严格执行 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`。

至少确认：

```text
macOS version
uname -m == arm64
Python / Node 是否原生 arm64
Gatekeeper 状态
系统盘空间
现有 /Applications/灵机.app
旧 LingJi DMG 挂载
LingJi / lingji-core / MCP 残留进程
8765 / 8766 / 8767 端口
~/Library/Application Support/LingJi 现状
~/Library/Application Support/LingJiData 现状
~/Documents/acceptance 是否在验收前已经存在
Obsidian / Ollama / Git / Vault 现状
主人正式 Production DataRoot
```

预检只读。禁止删除 Production DataRoot、Vault、正式记忆、个人模型、AI 客户端配置或任何归属不明确的文件。

必须先记录 `~/Documents/acceptance` 的验收前状态，避免把历史残留与本轮污染混为一谈。

---

# 4. 本轮最重要的物理隔离规则

本轮 Runtime **必须**使用 task-scoped 环境变量：

```bash
export LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
mkdir -p "$LINGJI_ACCEPTANCE_DATA_ROOT"
```

要求：

- 在 LingJi Runtime 启动**之前**注入；
- 本轮 SQLite、Qdrant、token、logs、raw、vault、backup 等全部只能写入该目录；
- 不持久化为主人日常 Production 配置；
- 不允许创建新的 `~/Documents/acceptance`；
- 不允许写主人 Production DataRoot；
- 普通日常启动没有该变量时不得继续复用历史 Acceptance workspace。

任何本轮 Runtime 数据出现在任务根之外：

```text
FAIL_ACCEPTANCE_ISOLATION
```

并记录：

```text
unexpected_write_count
unexpected_paths
production_pollution_count
```

---

# 5. 安装必须使用 whole-bundle replace

**禁止 overlay copy。** 不允许把新 `.app` 内文件叠加复制到旧 `/Applications/灵机.app`。

固定流程：

1. 正常退出旧 LingJi；
2. 确认旧 Core / 8766 已释放；
3. 挂载已验哈希的 DMG；
4. 如果 `/Applications/灵机.app` 已存在，把**整个旧 App**移动到：

```text
$ACCEPTANCE_ROOT/app-backup/灵机.app
```

5. 从 DMG 完整复制新 `.app` 到 `/Applications`；
6. 执行：

```bash
codesign --verify --deep --strict /Applications/灵机.app
```

7. 只有 PASS 才继续；
8. 新 App 复制或签名失败时，删除失败的新 App，完整恢复旧 App，再验证旧 App 签名。

报告必须记录：

```text
install_mode=whole_bundle_replace
post_install_codesign=PASS|FAIL
rollback_required=true|false
```

---

# 6. 启动必须保留 task-scoped 环境

不要用会丢失本轮环境变量的普通 Finder 双击作为技术隔离结论。

从**已安装 App** 的主二进制启动：

```bash
APP_BIN="$(find /Applications/灵机.app/Contents/MacOS -maxdepth 1 -type f -perm -111 | head -n 1)"
test -n "$APP_BIN"
LINGJI_ACCEPTANCE_DATA_ROOT="$LINGJI_ACCEPTANCE_DATA_ROOT" \
  "$APP_BIN" >"$ACCEPTANCE_ROOT/logs/desktop-launch.log" 2>&1 &
```

主人仍然观察正常 GUI，不需要操作终端。

---

# 7. 本轮验收目标

这不是开发任务。Codex 在验收模式下不得为了 PASS 修改产品代码。

## A. 精确身份

必须确认：

```text
Artifact / DMG SHA 匹配
App 主二进制 arm64
Sidecar arm64
codesign PASS
Release Metadata commit == 65de729228b200869b118fd9c0798af6ad658bca
UI/诊断显示的产品 commit == 65de729228b200869b118fd9c0798af6ad658bca
```

任何 PR merge commit、旧 commit 或未知 commit 都不能通过。

## B. Autopilot 首次启动

Phase 3 的正常产品行为必须是：

```text
打开 LingJi
→ 自动选择平台安全资料目录
→ 自动准备 Runtime
→ 自动连接
→ 进入首页
```

正常首次启动**不应要求主人先选择 DataRoot**。

“手动选择位置”只能在自动准备真实失败之后作为兜底出现。

本轮验收使用 task-scoped root，因此 UI 也不应要求主人再次配置存储位置。

## C. 首页智能化

主人应首先看到：

```text
有没有必须由我决定的事情
灵机当前正在自己做什么
如果有系统异常，是否正在自动处理
```

没有主人事项时：首页应明确“无需操作”或同等清晰结论，不能靠大量技术卡片证明自己还活着。

以下不应占据日常首页主区域：

```text
Qdrant
Embedding dimension
SQLite
8766
MCP 内部状态
branch
checkpoint
索引内部状态
大量 AI 元数据计数
```

它们必须保留在高级工具/诊断中，而不是删除功能。

## D. AI 来源自动接管

无需主人手工刷新、找路径或逐项导入，灵机应自动识别受支持本机 AI 元数据。

至少观察 Codex；Claude Code / WorkBuddy 以本机真实安装情况为准。

如果识别到几千条 Codex 工作记录元数据：

- 不应把数字本身做成给主人处理的主要任务；
- 应作为后台已接管状态；
- “Codex 工作记录”必须能理解为扫描到的 Session/工作上下文，不是灵机创建的聊天窗口。

## E. 主人决策边界

“需要我决定”只允许用于：

```text
读取真实对话/导出正文
导入敏感资料
永久记忆审核
删除/重建向量 Collection 等不可逆操作
```

普通错误、重试、健康异常、索引维护、扫描等应先由系统自动处理。

未授权前必须保持：

```text
真实正文读取 = 0
永久记忆自动批准 = 0
不可逆向量操作 = 0
```

## F. Runtime / 生命周期

必须验证：

```text
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_binary_available=true
8766 only 127.0.0.1
```

并完成：

```text
启动 → healthy
→ 正常退出
→ Core 退出
→ 8766/8767 释放
→ 同一 task-scoped root 再启动
→ healthy
```

不得留下重复 Core 或孤儿 MCP。

---

# 8. 主人只参与必要肉眼判断

只有以下事项需要主人：

```text
App 是否正常出现
有没有异常黑窗/终端
首次打开是否无需配置即可开始
首页能不能一眼看懂
自动化程度是否明显达到“系统自己做、我只处理关键决定”
Codex 工作记录是否能理解
真正授权动作是否清楚
```

哈希、下载、进程、端口、安装替换、Runtime、API、目录污染检查、清理、报告和 Git 回传全部由 Codex 自行完成。

Codex 不得替主人编造 UI PASS。

---

# 9. 失败处理

任一步失败：

```text
保存最小失败证据
→ 继续不受影响的只读检查
→ 判断正式数据污染
→ 必要时恢复旧 App
→ 正常退出
→ 清理本轮临时内容
→ 生成 FAIL / BLOCKED 报告
```

产品缺陷：

```text
停止本轮验收
→ 回传根因/复现/证据
→ 开发代理修复
→ 新 Commit + 新 Artifact
→ 原地更新本任务单
→ 再验收
```

**禁止拿同一个已确认失败的 DMG 反复要求主人测试。**

---

# 10. 验收结束强制清理

无论 PASS / FAIL / BLOCKED 都必须执行。

先：

```text
正常退出灵机
→ 确认 lingji-core 退出
→ 确认 8766 / 8767 释放
→ 卸载 DMG
```

然后清理本轮：

```text
ACCEPTANCE_ROOT
Artifact ZIP / DMG
临时解压目录
fixture / checkpoint
runtime-data
临时 Qdrant / SQLite
普通成功日志 / 截图
临时配置备份
临时 worktree
无复用价值的构建缓存/产物
```

App 回滚规则：

- 新 App PASS：旧 App 备份随任务根删除；
- 新 App FAIL 且需回滚：先恢复旧 App并验证，再删除任务根。

只长期保留：

```text
/Applications/灵机.app 当前有效版本
主人正式 Production DataRoot
主人明确要求保留的数据
Obsidian Vault
正式 Git 仓库
最终 Markdown 验收报告
脱敏公开证据/哈希
明确要求保留的失败证据
```

不得删除其他软件缓存或归属不明的主人文件。

---

# 11. 清理后复查

必须确认：

```text
本轮 ACCEPTANCE_ROOT 不存在
DMG 已卸载
重复 App 不存在
本轮临时 Runtime/Qdrant/SQLite 不存在
本轮没有新建 ~/Documents/acceptance
Production DataRoot / Vault 无非预期变化
8766 / 8767 已释放
LingJi/lingji-core 无孤儿进程
```

清理失败：

```text
BLOCKED_POST_CLEANUP
```

不得标记完整 PASS。

---

# 12. 最终报告与回传

写入：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_65de7292.md
```

提交到：

```text
acceptance/macos-m5-physical-acceptance-65de7292
```

至少包含：

```text
task_id
product_commit
artifact_id
dmg_sha256
macOS_version
machine_architecture
precheck_result
artifact_integrity_result
embedded_commit_exact
install_mode
post_install_codesign
rollback_required
acceptance_root_isolated
unexpected_write_count
unexpected_paths
first_launch_result
runtime_result
api_result
autodiscovery_result
codex_work_record_clarity
owner_decision_vs_system_issue_clarity
technical_detail_visibility
ui_owner_observation
restart_result
production_pollution_count
cleanup_after
local_temp_root_absent
retained_core_files
failed_step
root_cause_if_known
verdict
```

结论只允许：

```text
PASS
FAIL
BLOCKED
```

只有同时满足：

```text
精确 Artifact 身份通过
whole-bundle 安装与签名通过
task-scoped 物理隔离通过
Runtime/API/生命周期通过
主人确认 Phase 3 UI/自动化体验可接受
正式数据污染 = 0
本轮垃圾清理完成
任务根不存在
远程报告已提交并复读
```

才能标记 PASS。

---

# 13. 给 Codex 的最后约束

读完本文件后直接执行。

以下信息已经提供，**禁止再次向用户索要**：

```text
task_id
repository
product_commit
product_branch
PR
platform
target
workflow run
artifact name
artifact id
DMG name
DMG SHA256
验收协议
ACCEPTANCE_ROOT
LINGJI_ACCEPTANCE_DATA_ROOT
安装替换规则
报告路径
报告分支
```

只有以下两种情况才与主人交互：

1. 需要主人肉眼判断 UI / 自动化程度；
2. 出现本文件定义的真实外部阻断。

除此之外全部由 Codex 自行完成。
