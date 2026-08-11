# LingJi macOS M5 真机验收指令

> 本文件是 Apple Silicon / M5 Mac 真机验收的专项强制协议。
>
> 目标不是“能打开一次”，而是在不污染主人正式数据和系统环境的前提下完成可重复验收，并在验收结束后恢复干净现场。
>
> 本文件与 `docs/ACCEPTANCE/README.md`、`CODEX_ACCEPTANCE_INSTRUCTIONS.md`、`LOCAL_EXECUTION_TASK.md` 一起生效。若通用文档包含 Windows 专属路径或操作，本文件在 macOS 验收中优先。

## 0. 强制执行顺序

任何第一次 M5 验收都必须严格按以下顺序：

```text
读取任务身份
→ 本机环境盘点
→ 保存必要安全快照
→ 验证 Artifact / 架构 / 签名
→ 清理旧 LingJi 残留进程和端口
→ 创建唯一验收临时根目录
→ 安装与启动
→ Runtime / API / UI / 生命周期验收
→ 保存失败或最终证据
→ 退出 LingJi 并确认无残留进程
→ 删除本轮垃圾和临时文件
→ 复查主人正式数据未受影响
→ 远程回传报告
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

如果验收所用 Python、Rust、Node 或构建进程实际运行在 Rosetta / x86_64 下，必须标记：

```text
BLOCKED_NON_NATIVE_TOOLCHAIN
```

不得用 Rosetta 构建结果冒充 M5 原生验收。

## 1.2 macOS 安全状态

只读检查：

```bash
spctl --status
```

如果系统因 Gatekeeper、隔离属性、签名或权限阻止启动，必须先记录原始错误，再按任务单允许的方式处理。

禁止为了让验收通过而全局关闭 Gatekeeper、SIP 或其他系统安全功能。

## 1.3 磁盘与目录

验收前至少确认：

- 系统盘剩余空间足够；
- `/Applications` 可正常访问；
- 当前用户主目录可读写；
- `~/Library/Application Support` 可正常访问；
- `~/Library/Caches` 可正常访问；
- 没有将正式 LingJi 数据误放进本轮临时目录。

不得删除、移动或覆盖主人正式：

- Production DataRoot；
- Acceptance 中主人要求长期保留的数据；
- Obsidian Vault；
- 正式记忆正文；
- Git 仓库正式分支；
- 用户自己的 Codex、Claude、Obsidian、Ollama 配置；
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
当前 Commit（如果 UI / build metadata 可读）
是否存在多个安装副本
是否存在旧 DMG 挂载
```

发现多个正式安装副本时，不得直接删除；先确认哪一个是当前正式安装，其他副本只在确认属于旧验收产物后清理。

## 1.5 LingJi 进程与端口现场

验收前必须检查：

```bash
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
lsof -nP -iTCP:8767 -sTCP:LISTEN || true
lsof -nP -iTCP:8765 -sTCP:LISTEN || true
```

要求：

- 没有未知来源 LingJi Desktop；
- 没有旧 `lingji-core`；
- 没有孤儿 MCP；
- 8766 未被旧 LingJi 占用；
- 8767 未被旧 MCP 占用；
- 8765 如果存在，只能确认属于兼容用途。

只允许结束确认属于 LingJi 的残留进程。

禁止粗暴执行：

```text
killall python
killall node
killall codex
pkill -f python
```

## 1.6 外部依赖盘点

只做检测，不因为缺失就擅自安装：

- Obsidian 是否安装；
- Ollama 是否安装和是否运行；
- Git 是否可用；
- 当前 Vault 是否存在；
- 当前模型是否存在；
- Codex / MCP 是否属于本轮范围。

未安装的可选依赖必须显示真实状态，不得伪造成系统整体失败。

---

# 2. 唯一验收临时根目录

本轮所有非正式数据必须集中到一个可整体删除的位置：

```text
~/Library/Caches/LingJiAcceptance/<task-id>-<short-commit>/
```

只允许创建：

```text
artifact/
logs/
evidence-private/
evidence-public/
fixtures/
checkpoint/
temp-config-backup/
test-data-root/
report/
```

禁止把验收日志、fixture、临时数据库、Qdrant、截图、解压包散落在：

```text
Desktop
Documents
Downloads
仓库根目录
/Applications
正式 DataRoot
正式 Vault
```

上一轮同任务临时根目录存在时，先确认不含主人正式数据，再整体删除重建。

---

# 3. Artifact 与安装包核验

必须验证：

- Artifact 对应任务指定 Commit；
- 目标架构为 `aarch64-apple-darwin`；
- DMG 哈希与任务单一致；
- DMG 可挂载；
- `.app` 存在；
- App 主二进制为 arm64；
- Sidecar 为 arm64；
- Sidecar 和 `lingji_core_lib` 存在；
- `codesign --verify --deep --strict` 结果符合当前发布合同。

不得拿旧 DMG 验收新 Commit。

身份、哈希或架构不一致：

```text
FAIL_ARTIFACT_INTEGRITY
```

---

# 4. 第一次安装与启动

## 4.1 安装

验收包从 DMG 安装到：

```text
/Applications
```

禁止长期直接从挂载 DMG 中运行作为正式验收结论。

首次验收不得删除主人旧 DataRoot 来制造“干净启动”。

需要隔离测试时，只使用：

```text
~/Library/Caches/LingJiAcceptance/<task-id>-<short-commit>/test-data-root
```

## 4.2 首次启动主人观察

必须让主人确认：

- App 是否能正常打开；
- 是否出现无法理解的系统弹窗；
- 是否出现终端 / 黑色控制台窗口；
- 第一次打开是否明确知道下一步；
- 数据目录选择是否看得懂；
- Production / Acceptance 是否明确；
- 错误提示是否告诉用户下一步。

Codex 不能替主人写“肉眼 PASS”。

---

# 5. Runtime 与 API 真机验收

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
- Sidecar 来自当前安装的 App；
- Runtime 数据写入预期 DataRoot；
- 不把测试数据写进主人 Production；
- 不把运行垃圾散落到 App 安装目录。

---

# 6. UI 最低验收范围

第一次 M5 验收至少覆盖：

1. 启动页 / 总览；
2. Workspace 与 DataRoot；
3. Runtime 状态；
4. Control API 状态；
5. Obsidian / Vault 状态；
6. Qdrant / Embedding 状态；
7. 模型与依赖状态；
8. 日志 / 诊断入口；
9. 退出；
10. 再次启动。

所有状态必须来自真实后端，不得用默认绿色或假成功代替未知状态。

---

# 7. 生命周期验收

至少执行：

```text
启动
→ healthy
→ 正常退出
→ 确认 Core 退出
→ 确认 8766 释放
→ 再启动
→ 再次 healthy
```

检查：

```bash
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
```

不得留下重复 Core 或僵尸 Sidecar。

---

# 8. 失败处理

任何失败必须先保存：

- 失败步骤；
- 可复现方式；
- 最小相关日志；
- 进程和端口状态；
- 当前 Artifact / Commit；
- 必要截图；
- 是否污染正式数据。

只保留与失败根因直接相关的证据。

禁止无限累积每一轮完整日志、截图和旧包。

失败后如果需要开发修复：

```text
根因分析
→ 最小修复
→ 自动测试
→ 新 Artifact
→ 再次真机验收
```

不得重复拿同一个已知失败包让主人反复验收。

---

# 9. 验收结束后的强制清理

这是完成条件，不是可选优化。

## 9.1 先正常退出

清理前：

1. 正常退出 LingJi；
2. 等待受管 Runtime 退出；
3. 确认 8766 / 8767 已释放；
4. 只结束确认属于本轮 LingJi 的残留进程。

## 9.2 必须删除

本轮验收结束后删除：

- `~/Library/Caches/LingJiAcceptance/<task-id>-<short-commit>/` 整个临时根目录；
- 已挂载的验收 DMG；
- 本轮重复下载的 ZIP / DMG；
- 临时解压目录；
- fixture；
- checkpoint；
- 临时 DataRoot；
- 临时 Qdrant；
- 临时 SQLite；
- 临时配置备份；
- 普通成功日志；
- 普通成功截图；
- 构建产生但后续不会重复使用的临时产物；
- 本轮专用临时 worktree；
- 仓库外散落的本轮测试文件。

如果本轮使用源码构建，验收结束应清理无复用价值的大体积构建产物，例如本轮专用 `target`、PyInstaller 临时目录和临时 bundle；不得因此删除共享源码或主人已有开发环境。

## 9.3 默认保留的核心文件

只保留后续会重复使用或属于主人正式资产的内容：

- `/Applications/灵机.app` 当前验收版本；
- 主人正式 Production DataRoot；
- 主人明确要求长期保留的 Acceptance 数据；
- Obsidian Vault；
- 正式 Git 仓库源码；
- 仓库中的最终 Markdown 验收报告；
- 脱敏公开证据摘要；
- 哈希清单；
- 主人明确要求保留的失败证据。

本地 DMG 默认不属于核心长期文件，因为 GitHub Artifact 可重新获取。除非任务单明确要求后续离线重复安装，否则本机只保留一个最新验收 DMG，旧 DMG 全部删除。

## 9.4 禁止擅自清理的内容

任何情况下不得因为“保持干净”而删除：

- 主人正式 DataRoot；
- Vault；
- 正式记忆；
- 用户个人模型；
- 用户 Codex / Claude / Obsidian / Ollama 配置；
- 无法确认归属的缓存或数据；
- 其他软件的缓存；
- macOS 系统缓存。

只清理 **LingJi 本轮验收明确产生** 的垃圾。

---

# 10. 清理后复查

清理后必须再次检查：

```bash
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
lsof -nP -iTCP:8767 -sTCP:LISTEN || true
```

并确认：

```text
本轮临时根目录不存在
DMG 已卸载
重复安装包不存在
重复 App 不存在
临时测试 DataRoot 不存在
临时 Qdrant / SQLite 不存在
普通成功日志和截图已删除
正式 DataRoot / Vault 未变化或变化符合验收预期
```

结束清理失败时：

```text
BLOCKED_POST_CLEANUP
```

不得标记为完整 PASS。

---

# 11. 最终回执必须包含

```yaml
platform: macOS
architecture: arm64
physical_m5_checked: true|false
artifact_identity: PASS|FAIL
preflight_environment: PASS|FAIL
pre_cleanup: PASS|FAIL
install: PASS|FAIL
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

只有以下条件全部满足，才允许写最终 `PASS`：

```text
本机环境检查完成
Artifact 身份正确
真实 M5 启动完成
Runtime/API/UI 验收完成
无 Production 污染
退出与重启正常
结束垃圾清理完成
临时根目录已删除
最终报告已回传
```

---

# 12. 主人参与边界

主人只需要参与无法可靠自动化的部分：

- App 是否正常打开；
- 系统是否弹出异常窗口；
- 页面是否能看懂；
- 第一次打开是否知道下一步；
- UI 是否有明显死按钮或错误状态；
- 需要主人授权的正式数据操作。

环境检查、进程端口检查、Artifact 核验、日志采集、临时目录管理、验收结束清理、报告和 Git 回传全部由 Codex 完成。
