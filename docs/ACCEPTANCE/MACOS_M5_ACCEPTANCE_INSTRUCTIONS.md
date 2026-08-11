# LingJi macOS M5 真机验收指令

> 本文件是 Apple Silicon / M5 Mac 真机验收的专项强制协议。
>
> 目标不是“能打开一次”，而是在不污染主人正式数据和系统环境的前提下完成可重复验收，并在验收结束后恢复干净现场。
>
> 若通用文档包含 Windows 专属路径或操作，本文件在 macOS 验收中优先。具体产品 Commit、Artifact、哈希和任务根以 `MACOS_M5_LOCAL_EXECUTION_TASK.md` 为准。

## 0. 强制执行顺序

```text
读取当前任务单
→ 本机环境盘点
→ 保存必要安全快照
→ 创建唯一验收临时根目录
→ 下载并验证精确 Artifact / Commit / 架构 / 签名
→ 清理确认属于旧 LingJi 验收的残留进程和端口
→ 安全整体替换 App
→ 使用 task-scoped acceptance data root 启动已安装 App
→ Runtime / API / UI / 生命周期验收
→ 保存最小失败证据或最终证据
→ 正常退出 LingJi 并确认无残留进程
→ 删除本轮垃圾和临时文件
→ 复查主人正式数据未受影响
→ 提交并远程复读报告
```

环境盘点没有完成前，禁止安装和启动本轮验收包。

结束清理没有完成前，禁止把任务标记为 `PASS` 或 `COMPLETED`。

---

# 1. 第一次验收前本机环境检查

## 1.1 系统与架构

必须记录但不得泄露私人用户名：

```bash
sw_vers
uname -m
uname -a
python3 -c 'import platform; print(platform.machine())'
rustc -Vv 2>/dev/null || true
node -p 'process.arch' 2>/dev/null || true
```

硬门禁：

```text
uname -m == arm64
```

如果验收所用 Python、Rust、Node 或构建进程实际运行在 Rosetta / x86_64 下：

```text
BLOCKED_NON_NATIVE_TOOLCHAIN
```

不得用 Rosetta 构建结果冒充 M5 原生验收。

## 1.2 macOS 安全状态

只读检查：

```bash
spctl --status
```

禁止为了让验收通过而全局关闭 Gatekeeper、SIP 或其他系统安全功能。

## 1.3 磁盘与目录

验收前至少确认：

- 系统盘剩余空间足够；
- `/Applications` 可正常访问；
- `~/Library/Application Support` 可正常访问；
- `~/Library/Caches` 可正常访问；
- 没有将正式 LingJi 数据误放进本轮临时目录。

不得删除、移动或覆盖主人正式：

- Production DataRoot；
- 主人明确要求长期保留的 Acceptance 数据；
- Obsidian Vault；
- 正式记忆正文；
- Git 仓库正式分支；
- Codex、Claude、Obsidian、Ollama 用户配置；
- 任何无法确认归属的文件。

## 1.4 现有 LingJi 安装盘点

只读检查：

```text
/Applications/灵机.app
/Applications/LingJi.app
~/Applications/灵机.app
~/Applications/LingJi.app
```

同时检查当前已挂载的 LingJi DMG、旧安装包和旧验收目录。

必须记录：

```text
是否已安装
当前版本
当前 Commit（如果 release metadata 可读）
是否存在多个安装副本
是否存在旧 DMG 挂载
```

发现多个正式安装副本时不得直接删除；先确认归属。

## 1.5 LingJi 进程与端口现场

```bash
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
lsof -nP -iTCP:8767 -sTCP:LISTEN || true
lsof -nP -iTCP:8765 -sTCP:LISTEN || true
```

只允许结束确认属于 LingJi 的残留进程。

禁止：

```text
killall python
killall node
killall codex
pkill -f python
```

## 1.6 外部依赖盘点

只检测，不因缺失擅自安装：

- Obsidian；
- Ollama；
- Git；
- Vault；
- 当前模型；
- Codex / MCP。

可选依赖缺失必须显示真实状态，不得伪造成系统整体失败。

---

# 2. 唯一验收临时根目录

本轮所有非正式数据必须集中到：

```text
~/Library/Caches/LingJiAcceptance/<task-id>-<short-commit>/
```

建议子目录：

```text
artifact/
logs/
evidence-private/
evidence-public/
fixtures/
checkpoint/
temp-config-backup/
runtime-data/
app-backup/
report/
```

禁止把验收日志、fixture、临时数据库、Qdrant、截图、解压包、Runtime 数据散落在：

```text
Desktop
Documents
Downloads
仓库根目录
/Applications（App 本体除外）
正式 Production DataRoot
正式 Vault
```

上一轮同任务临时根目录存在时，先确认不含主人正式数据，再整体删除重建。

---

# 3. Artifact 与安装包核验

必须验证：

- Artifact 对应任务指定的**精确产品 Commit**；
- Release Metadata / 嵌入 Commit 与任务单完全一致，不接受 PR merge commit 替代 Head；
- 目标架构为 `aarch64-apple-darwin`；
- DMG 哈希与任务单一致；
- DMG 可挂载；
- `.app` 存在；
- App 主二进制为 arm64；
- Sidecar 为 arm64；
- Sidecar 和 `lingji_core_lib` 存在；
- `codesign --verify --deep --strict` 通过当前签名合同。

身份、哈希或架构不一致立即：

```text
FAIL_ARTIFACT_INTEGRITY
```

不得为了继续 UI 验收而忽略身份失败。

---

# 4. 安装与安全替换

## 4.1 禁止 overlay 覆盖 `.app`

**不得**把新 App 的内部文件直接复制到旧 `/Applications/灵机.app` 中。

原因：旧 sealed resources 可能残留，导致新 bundle 的签名验证失败。

正确替换流程：

1. 确认 LingJi 和受管 Runtime 已退出；
2. 如果 `/Applications/灵机.app` 已存在，把整个旧 App 移到本轮：

```text
$ACCEPTANCE_ROOT/app-backup/灵机.app
```

3. 从已验证 DMG 完整复制新的 `.app` 到 `/Applications`；
4. 对新的 `/Applications/灵机.app` 执行：

```bash
codesign --verify --deep --strict /Applications/灵机.app
```

5. 只有验证通过，才继续启动；
6. 若复制或签名验证失败：删除本轮失败的新 App，并完整恢复备份 App；
7. 不得因此删除任何 DataRoot、Vault 或用户配置。

最终报告必须记录：

```text
install_mode=whole_bundle_replace
post_install_codesign=PASS|FAIL
rollback_required=true|false
```

## 4.2 验收 Runtime 必须先注入任务根

Phase 3 起，真实验收使用临时环境变量：

```text
LINGJI_ACCEPTANCE_DATA_ROOT
```

任务单必须把它设置为本轮唯一目录，例如：

```bash
export LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
mkdir -p "$LINGJI_ACCEPTANCE_DATA_ROOT"
```

然后必须从**已安装 App** 的主二进制启动，并让该环境变量在 Runtime 启动之前生效：

```bash
APP_BIN="$(find /Applications/灵机.app/Contents/MacOS -maxdepth 1 -type f -perm -111 | head -n 1)"
test -n "$APP_BIN"
LINGJI_ACCEPTANCE_DATA_ROOT="$LINGJI_ACCEPTANCE_DATA_ROOT" "$APP_BIN" >"$ACCEPTANCE_ROOT/logs/desktop-launch.log" 2>&1 &
```

要求：

- 验收 Runtime 的所有 SQLite、Qdrant、token、logs、raw、vault、backup 等只允许写入该 task-scoped root；
- 不允许创建 `~/Documents/acceptance`；
- 不允许写主人 Production DataRoot；
- `LINGJI_ACCEPTANCE_DATA_ROOT` 只作用于本轮验收进程，不写成长期用户配置；
- 普通日常启动没有该变量时不得继续复用历史 Acceptance workspace。

任何任务数据出现在任务根之外：

```text
FAIL_ACCEPTANCE_ISOLATION
```

并立即记录 `production_pollution_count` / `unexpected_path`。

---

# 5. 首次启动与主人观察

Phase 3 的正常产品首次启动预期是：

```text
打开 LingJi
→ LingJi 自动选择平台默认安全资料目录
→ 自动准备 Runtime
→ 自动进入首页
```

**正常首次启动不应要求主人先选择 DataRoot。**

“手动选择资料目录”只能在自动准备失败后的高级兜底中出现。

主人只确认：

- App 是否能正常出现；
- 是否出现异常终端 / 黑窗；
- 是否出现无法理解的系统弹窗；
- 第一次打开是否无需配置即可进入可用状态；
- 首页是否能一眼知道“现在需要我做什么”；
- 没有主人事项时是否明确“无需操作”；
- 自动发现是否安静工作，而不是把数千条元数据当成任务压给主人；
- 真正需要正文读取 / 永久记忆 / 不可逆操作时，授权动作是否清楚。

Codex 不能替主人写“肉眼 PASS”。

---

# 6. Runtime 与 API 真机验收

启动后必须确认：

```text
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_binary_available=true
```

同时确认：

- 8766 只监听 `127.0.0.1`；
- 不存在第二个 Core；
- 不存在孤儿 MCP；
- Sidecar 来自当前安装 App；
- Runtime 数据只写入本轮 `LINGJI_ACCEPTANCE_DATA_ROOT`；
- 不把运行垃圾写入 App bundle；
- release metadata 的 commit 与任务单精确一致。

---

# 7. UI 最低验收范围

日常主界面至少检查：

1. 首页：主人行动优先，技术指标不占第一屏；
2. 当前工作；
3. 需要我决定；
4. AI 来源自动接管；
5. Codex 工作记录解释；
6. 高级工具 / 诊断入口；
7. 退出与再次启动。

专项高级能力继续从高级工具抽查：

- Workspace / DataRoot；
- Runtime / Control API；
- Obsidian / Vault；
- Qdrant / Embedding；
- 模型与依赖；
- 日志 / 诊断。

所有状态必须来自真实后端，不得用默认绿色或假成功代替未知状态。

---

# 8. 生命周期验收

至少执行：

```text
启动
→ healthy
→ 正常退出
→ Core 退出
→ 8766 释放
→ 使用同一 task-scoped root 再启动
→ 再次 healthy
```

检查：

```bash
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
```

不得留下重复 Core 或僵尸 Sidecar。

---

# 9. 失败处理

任何失败先保存：

- 失败步骤；
- 可复现方式；
- 最小相关日志；
- 进程与端口状态；
- 当前 Artifact / Commit；
- 必要截图；
- 是否污染正式数据；
- 是否需要恢复旧 App。

只保留与失败根因直接相关的证据。

失败后如果需要开发修复：

```text
根因分析
→ 最小修复
→ 自动测试
→ 新 Commit + 新 Artifact
→ 原地更新当前任务单
→ 再次真机验收
```

不得拿同一个已知失败包让主人反复验收。

---

# 10. 验收结束后的强制清理

这是完成条件，不是可选优化。

## 10.1 先正常退出

1. 正常退出 LingJi；
2. 等待受管 Runtime 退出；
3. 确认 8766 / 8767 已释放；
4. 卸载本轮 DMG；
5. 只结束确认属于本轮 LingJi 的残留进程。

## 10.2 必须删除

- 整个 `$ACCEPTANCE_ROOT`；
- 本轮重复 Artifact ZIP / DMG；
- 临时解压目录；
- fixture / checkpoint；
- task-scoped Runtime 数据；
- 临时 Qdrant / SQLite；
- 普通成功日志和截图；
- 临时配置备份；
- 本轮专用 worktree；
- 无复用价值的本轮构建产物。

删除 `$ACCEPTANCE_ROOT` 前，如果 `app-backup` 中保存着验收前旧 App：

- 新 App 验收 PASS 时，旧备份不再需要，随任务根删除；
- 新 App 验收 FAIL 且需要回滚时，先恢复旧 App并验证签名，再删除任务根。

## 10.3 默认保留核心文件

只保留：

- `/Applications/灵机.app` 当前有效版本（新版本 PASS 或失败后恢复的旧版本）；
- 主人正式 Production DataRoot；
- 主人明确要求长期保留的数据；
- Obsidian Vault；
- 正式 Git 仓库；
- 最终 Markdown 验收报告；
- 脱敏公开证据摘要 / 哈希清单；
- 主人明确要求保留的失败证据。

本地 DMG 默认不长期保存；GitHub Artifact 可重复获取。

## 10.4 禁止擅自清理

不得删除：

- Production DataRoot；
- Vault；
- 正式记忆；
- 用户个人模型；
- Codex / Claude / Obsidian / Ollama 配置；
- 无法确认归属的缓存或数据；
- 其他软件缓存；
- macOS 系统缓存。

---

# 11. 清理后复查

```bash
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
lsof -nP -iTCP:8767 -sTCP:LISTEN || true
```

确认：

```text
本轮临时根不存在
DMG 已卸载
重复安装包不存在
重复 App 不存在
临时 Runtime/Qdrant/SQLite 不存在
~/Documents/acceptance 不因本轮被创建
普通成功日志和截图已删除
正式 DataRoot / Vault 无非预期变化
```

清理失败：

```text
BLOCKED_POST_CLEANUP
```

不得标记完整 PASS。

---

# 12. 最终回执

```yaml
platform: macOS
architecture: arm64
physical_m5_checked: true|false
artifact_identity: PASS|FAIL
embedded_commit_exact: true|false
preflight_environment: PASS|FAIL
pre_cleanup: PASS|FAIL
install_mode: whole_bundle_replace
post_install_codesign: PASS|FAIL
acceptance_root_isolated: true|false
unexpected_write_count: 0
first_launch: PASS|FAIL
runtime: PASS|FAIL
control_api: PASS|FAIL
ui: PASS|FAIL
restart_cycle: PASS|FAIL
production_pollution_count: 0
post_cleanup: PASS|FAIL
temp_root_absent: true|false
duplicate_app_count: 0
orphan_runtime_count: 0
final_verdict: PASS|FAIL|BLOCKED
```

只有以下全部满足才允许 `PASS`：

```text
本机环境检查完成
Artifact 精确身份正确
安全整体替换安装通过
task-scoped Runtime 物理隔离通过
真实 M5 启动完成
Runtime/API/UI 验收完成
主人确认 UI 可理解且自动化主流程达标
Production 污染 = 0
退出与重启正常
结束垃圾清理完成
临时根目录已删除
最终报告已提交并远程复读
```

---

# 13. 主人参与边界

主人只参与无法可靠自动化的部分：

- App 是否正常出现；
- 是否有异常窗口；
- 页面是否能看懂；
- 首页是否真的“无需配置、少打扰”；
- 自动化程度是否达到产品预期；
- 需要主人授权的正式数据操作。

环境检查、Artifact 核验、安装替换、进程端口检查、日志采集、临时目录管理、清理、报告和 Git 回传全部由 Codex 完成。
