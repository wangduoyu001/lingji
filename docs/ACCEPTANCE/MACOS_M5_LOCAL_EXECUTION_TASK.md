# LingJi macOS M5 当前真机验收任务单

> **这是当前 M5 真机验收的唯一执行入口。**
>
> 用户只需要把本文件链接交给 Codex。Codex 必须自行读取本文件中的任务身份、Artifact、验收协议、清理规则和报告路径；禁止再次向用户索要已经写在这里的信息。
>
> 本文件采用“原地更新”策略：每轮新的 M5 验收直接覆盖当前任务身份，不为每个版本重复创建任务单。

## 0. 当前唯一任务身份

```yaml
status: ACTIVE
task_id: MACOS-M5-UX-REACCEPTANCE-BF9DA9FF
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_commit: bf9da9ffec54c8e9cb927ffd0f3b9fd7213df928
product_branch: feature/owner-autopilot-ui-codexpp
pull_request: 88
platform: macOS Apple Silicon
target: aarch64-apple-darwin
app_version: 0.1.0
bundle_format: dmg
artifact_name: lingji-macos-arm64
artifact_id: 9095953036
workflow_run_id: 31477467940
workflow_name: macOS Desktop Gate
workflow_result: success
artifact_archive_sha256: 230b51c44d3eb48f441dbee66165a65dbb9541b3572061a9b306c91e4417f0fe
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46237964
dmg_sha256: 2373bf05629ea4aaec8f47433e1a0805f004bd3edd2e9638c972a8361c5ab39d
protocol_path: docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bf9da9ff.md
```

GitHub Actions Run：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31477467940
```

Artifact：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31477467940/artifacts/9095953036
```

被测产品身份必须始终保持：

```text
bf9da9ffec54c8e9cb927ffd0f3b9fd7213df928
```

本任务单自身后续产生的文档 Commit **不改变被测产品 Commit**。

---

# 1. Codex 收到本链接后的固定读取顺序

```text
本文件
→ docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ docs/ACCEPTANCE/README.md
→ PR #88 的产品变更说明
→ 被测 Commit bf9da9ff 的相关代码与配置
```

macOS 专项规则与通用规则冲突时，优先级固定为：

```text
MACOS_M5_LOCAL_EXECUTION_TASK.md
→ MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ 通用验收文档
```

**读完后直接执行，不再询问 task_id、commit、Artifact、DMG、报告路径或临时目录。**

---

# 2. Artifact 必须由 Codex 自行取得

优先使用 GitHub CLI：

```bash
export ACCEPTANCE_ROOT="$HOME/Library/Caches/LingJiAcceptance/MACOS-M5-UX-REACCEPTANCE-BF9DA9FF-bf9da9ff"
mkdir -p "$ACCEPTANCE_ROOT/artifact"

gh run download 31477467940 \
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

期望值：

```text
2373bf05629ea4aaec8f47433e1a0805f004bd3edd2e9638c972a8361c5ab39d
```

如果 GitHub Artifact 因鉴权无法下载：

1. 记录脱敏 `gh auth status`；
2. 尝试当前仓库已有 GitHub 认证方式；
3. 禁止改用旧 DMG；
4. 只有确认无法获取 **Artifact ID 9095953036** 时，才标记：

```text
BLOCKED_ARTIFACT_DOWNLOAD_AUTH
```

此时才允许让用户提供 **同一个 Artifact ID 9095953036 对应的文件**。

---

# 3. 第一次验收前必须先做本机环境预检

严格执行 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`。

至少只读确认：

```text
macOS 版本
uname -m == arm64
Python / Node 是否为原生 arm64
Gatekeeper 状态
系统盘可用空间
/Applications 中已有灵机版本
~/Library/Application Support 中 LingJi 现有数据
~/Library/Caches 中旧验收残留
是否存在已挂载旧 DMG
LingJi / lingji-core / MCP 残留进程
8765 / 8766 / 8767 端口占用
Obsidian / Ollama / Git / Vault 现状
正式 Production DataRoot 位置
```

预检阶段：

- 只读；
- 不删除正式 DataRoot；
- 不删除 Vault；
- 不修改其他软件配置；
- 不为了“环境干净”误删用户长期数据。

如果本机之前已经做过预检，只快速复核可能变化的项目，不要求用户重复回答已经明确的信息。

---

# 4. 本轮唯一临时目录

```text
~/Library/Caches/LingJiAcceptance/MACOS-M5-UX-REACCEPTANCE-BF9DA9FF-bf9da9ff/
```

所有本轮产生的内容必须集中在这里，包括：

```text
Artifact
临时 DMG
日志
截图
fixture
checkpoint
临时配置备份
测试 DataRoot
临时 Qdrant
临时 SQLite
测试导入材料
报告中间文件
```

禁止散落到 Desktop、Documents、Downloads 或正式 Production DataRoot。

---

# 5. 本轮验收目标

这不是开发任务。Codex 在本轮不得为了 PASS 修改产品代码。

本轮需要验证两层内容。

## A. 技术安装与 Runtime 基线

必须确认：

- DMG SHA256 精确匹配；
- DMG 可挂载；
- `.app` 存在；
- App 与 Sidecar 为 arm64；
- 安装到 `/Applications` 后启动；
- Runtime 能到 healthy；
- Control API 正常；
- 8766 仅监听本机；
- 无重复 Core；
- 退出后 Core 和端口正常释放；
- 再次启动可恢复。

## B. 本轮最重要的 UI / 自动化体验复验

本轮主要验证 PR #88 的“Owner-first / Autopilot”改造，而不是重新检查所有按钮。

主人只需要参与肉眼判断以下内容：

### 1. 首次启动

主人不需要理解这些技术词才能开始：

```text
DataRoot
Qdrant
Embedding
MCP
8766
workspace internals
```

正常主流程应该能直接理解为“选择灵机资料存放位置并开始使用”。

### 2. 首页能不能一眼看懂

主人应能快速知道：

```text
灵机发现了什么
灵机正在做什么
灵机已经处理了什么
什么事情真的需要我决定
```

### 3. 自动发现是否真的自动

无需主人逐个填写路径或点击刷新，灵机应自动发现受支持的本机 AI 来源和元数据。

至少观察：

```text
Codex
Claude Code（若本机存在）
WorkBuddy（若本机存在）
受支持导出包候选（若存在）
```

### 4. “Codex 工作记录”是否能理解

如果显示类似：

```text
2 条 Codex 工作记录
```

必须明确知道这是：

```text
灵机扫描本机识别出的 Codex Session / 工作上下文
```

而不是：

```text
灵机莫名其妙创建了 2 个聊天窗口
```

### 5. 主人决策与系统异常必须分开

失败任务、健康异常、重试、低磁盘等普通系统问题：

- 不得冒充“需要我决定”；
- 应进入系统异常/自动处理逻辑；
- 能自动处理的先自动处理。

“需要我决定”只用于真正的主人边界，例如：

```text
读取真实对话正文
导入敏感资料
永久记忆审核
删除/重建向量 Collection 等不可逆操作
```

### 6. 技术细节默认退居高级区域

以下信息不应占据日常首页第一屏：

```text
Qdrant
Embedding dimension
分支
checkpoint
索引内部状态
端口
SQLite
MCP 细节
```

主人需要诊断时仍必须可以进入高级工具查看，功能不能被删除。

### 7. 安全边界

未明确授权前：

```text
真实对话正文读取 = 0
永久记忆自动批准 = 0
不可逆向量操作 = 0
```

---

# 6. 失败处理

任一步失败：

```text
保存最小失败证据
→ 继续不受影响的只读检查
→ 判断是否污染正式数据
→ 正常退出
→ 清理本轮临时内容
→ 生成 FAIL / BLOCKED 报告
```

如果属于产品缺陷：

```text
停止本轮验收
→ 报告根因 / 复现步骤 / 证据
→ 返回开发代理修复
→ 新 Commit
→ 新 Artifact
→ 原地更新本任务单
→ 再验收
```

**禁止拿同一个已经确认有问题的 DMG 反复要求主人测试。**

---

# 7. 验收结束强制清理

无论 PASS / FAIL / BLOCKED 都必须执行。

先完成：

```text
正常退出灵机
→ 确认 lingji-core 退出
→ 确认 8766 / 8767 释放
→ 卸载本轮 DMG
```

然后删除本轮产生的：

```text
ACCEPTANCE_ROOT
重复 Artifact ZIP
重复 DMG
临时解压目录
fixture
checkpoint
测试 DataRoot
临时 Qdrant
临时 SQLite
普通成功日志
普通成功截图
临时配置备份
临时 worktree
无复用价值的本轮专用构建缓存/产物
```

只允许长期保留真正会重复使用的核心文件：

```text
/Applications/灵机.app 当前有效版本
正式 Production DataRoot
主人明确要求保留的 Acceptance 数据
Obsidian Vault
正式 Git 仓库
最终 Markdown 验收报告
脱敏证据摘要
哈希清单
明确要求保留的失败证据
```

本地 DMG 默认不长期保存；GitHub Artifact 可重新取得。只有明确需要离线复验时，最多保留一个当前最新版 DMG。

禁止删除归属不明确的主人数据或其他应用缓存。

---

# 8. 最终报告

写入：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bf9da9ff.md
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
install_result
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
核心技术基线通过
本轮 Owner-first UI 体验通过
正式数据污染 = 0
清理完成
本轮临时根目录不存在
```

才能标记 PASS。

---

# 9. 给 Codex 的最后约束

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
临时目录
报告路径
```

只有以下两种情况才与主人交互：

1. 需要主人肉眼判断 UI 是否清晰、自动化是否符合预期；
2. 出现本文件定义的真实外部阻断。

除此之外，环境检查、下载、哈希、安装包检查、进程、端口、日志、API、清理和报告均由 Codex 自行完成。
