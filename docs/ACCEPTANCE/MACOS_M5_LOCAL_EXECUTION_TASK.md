# LingJi macOS M5 当前真机验收任务单

> 这是当前 M5 真机验收的唯一执行入口。
>
> 用户只需要把本文件链接交给 Codex。Codex 必须自行读取本文件列出的任务身份、Artifact 和协议，不得再次向用户索要已经写在这里的 task_id、commit、Artifact ID、DMG 名称或下载位置。

## 0. 当前任务身份

```yaml
status: ACTIVE
task_id: MACOS-M5-PHYSICAL-ACCEPTANCE-C10D255
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_commit: c10d25541ec8814179545e03f3c6709b7beeb283
product_branch: master
platform: macOS Apple Silicon
target: aarch64-apple-darwin
app_version: 0.1.0
bundle_format: dmg
artifact_name: lingji-macos-arm64
artifact_id: 9030728866
workflow_run_id: 31288663236
workflow_name: macOS Desktop Gate
workflow_result: success
artifact_archive_sha256: c7d052daebfb65ac4adfd443efa8dd7d2f471c5aad77f6849b54e06b18d1f81e
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46204704
dmg_sha256: 65714a3eaab7d1a77a1dd5d1b8ce895daf3ba1a050970532afc5f9f805e2a45b
protocol_path: docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_c10d255.md
```

GitHub Actions run：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31288663236
```

Artifact 页面：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31288663236/artifacts/9030728866
```

当前任务所验收的产品 Commit 必须保持为：

```text
c10d25541ec8814179545e03f3c6709b7beeb283
```

本任务单或验收报告之后的文档 Commit 不改变被测产品身份。

---

# 1. Codex 读取顺序

收到本文件链接后固定执行：

```text
本文件
→ docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md 中非 Windows 专属规则
→ 被测 Commit c10d255 的相关代码和构建配置
```

macOS 与通用文档冲突时，以：

```text
MACOS_M5_LOCAL_EXECUTION_TASK.md
→ MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
```

优先。

不得因为通用文档里存在 Windows 路径、Windows 重启或 NSIS 内容而要求用户补充 Mac 任务身份。

---

# 2. Artifact 获取规则

Codex 必须优先自行从 GitHub Actions 下载，不得先让用户手工下载或重新提供 DMG。

如果本机已登录 GitHub CLI：

```bash
gh run download 31288663236 \
  -R wangduoyu001/lingji \
  -n lingji-macos-arm64 \
  --dir "$ACCEPTANCE_ROOT/artifact"
```

下载后必须得到：

```text
灵机_0.1.0_aarch64.dmg
```

然后验证：

```bash
shasum -a 256 "$ACCEPTANCE_ROOT/artifact/灵机_0.1.0_aarch64.dmg"
```

期望：

```text
65714a3eaab7d1a77a1dd5d1b8ce895daf3ba1a050970532afc5f9f805e2a45b
```

如果 GitHub Actions Artifact 因鉴权无法自动下载：

1. 先记录 `gh auth status` 的脱敏结果；
2. 尝试仓库已有 GitHub 连接方式；
3. 不允许换一个旧 DMG；
4. 只有确定本机没有可用 GitHub 凭据、也无法通过当前仓库连接获取精确 Artifact 时，才标记：

```text
BLOCKED_ARTIFACT_DOWNLOAD_AUTH
```

此时才允许请求用户提供 **同一个 Artifact ID 9030728866 对应的文件**。

不得再次询问 task_id、目标 commit 或 Artifact ID。

---

# 3. 第一次验收前环境盘点

严格执行 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md` 第 1 节。

至少确认：

```text
macOS 版本
uname -m == arm64
Python / Node 原生架构
Gatekeeper 状态
磁盘剩余空间
/Applications 状态
~/Library/Application Support 状态
~/Library/Caches 状态
现有 LingJi 安装
旧 LingJi DMG 挂载
LingJi / lingji-core / MCP 残留进程
8765 / 8766 / 8767 端口
Obsidian / Ollama / Git / Vault 可用性
```

环境盘点只读，不删除正式数据。

如果当前机器已经完成过同一任务 ID 的安全只读预检，Codex仍需快速复核关键环境是否变化，但不得要求用户重新提供已确定的产品身份。

---

# 4. 唯一临时目录

本轮固定使用：

```text
~/Library/Caches/LingJiAcceptance/MACOS-M5-PHYSICAL-ACCEPTANCE-C10D255-c10d255/
```

建议：

```bash
export ACCEPTANCE_ROOT="$HOME/Library/Caches/LingJiAcceptance/MACOS-M5-PHYSICAL-ACCEPTANCE-C10D255-c10d255"
```

所有本轮：

```text
Artifact
日志
截图
fixture
checkpoint
临时配置备份
测试 DataRoot
临时 Qdrant
临时 SQLite
报告中间文件
```

必须集中在该目录或仓库正式报告路径，不得散落 Desktop、Documents、Downloads 或正式 DataRoot。

---

# 5. 当前验收目标

本轮不是开发任务，目标是验证精确 Artifact 在真实 M5 Mac 上是否可作为下一阶段基础版本。

必须完成：

## A. 安装包身份

- DMG SHA256 精确匹配；
- DMG 可挂载；
- `.app` 存在；
- 主 App 二进制为 arm64；
- Sidecar 为 arm64；
- `codesign --verify --deep --strict` 符合当前 ad-hoc 验收合同。

## B. 首次安装与启动

- 安装到 `/Applications`；
- 从 `/Applications` 启动，不把直接从 DMG 运行作为正式结论；
- 不删除主人正式 DataRoot；
- 第一次隔离测试使用本轮临时 `test-data-root`。

## C. Runtime

必须验证：

```text
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_binary_available=true
```

并确认：

```text
8766 仅监听 127.0.0.1
无重复 Core
无孤儿 MCP
退出后 Core 退出
退出后 8766 释放
再次启动可恢复 healthy
```

## D. 最低 UI 范围

至少检查：

```text
总览
Workspace / DataRoot
Runtime
Control API
Obsidian / Vault
Qdrant / Embedding
模型 / 外部依赖
日志 / 诊断
正常退出
再次启动
```

## E. 主人只参与必要肉眼检查

只有以下节点需要主人观察：

```text
App 是否正常出现
是否有异常终端/黑窗
首次页面是否知道下一步
数据目录/Workspace 是否容易理解
是否有无法操作或明显错误的 UI
```

其余 Git、哈希、进程、端口、文件、日志、API、清理均由 Codex 自己完成。

---

# 6. 失败处理

任一步失败：

```text
保存最小失败证据
→ 继续不受影响的只读检查
→ 确认是否污染正式数据
→ 正常退出并清理
→ 生成 FAIL 报告
```

如果失败属于产品缺陷：

```text
本轮验收停止
→ 报告根因和复现步骤
→ 返回主开发代理修复
→ 生成新 Commit + 新 Artifact
→ 更新本任务单身份
→ 再验收
```

禁止拿同一个已知失败的 DMG 反复要求主人测试。

Codex 在验收模式下不得为了 PASS 擅自修改产品代码。

---

# 7. 验收结束强制清理

无论 PASS / FAIL，都必须执行。

先：

```text
正常退出灵机
→ 确认 lingji-core 退出
→ 确认 8766 / 8767 释放
→ 卸载本轮挂载 DMG
```

然后删除本轮产生的：

```text
ACCEPTANCE_ROOT
重复 Artifact ZIP
重复 DMG
临时解压内容
fixture
checkpoint
临时 DataRoot
临时 Qdrant
临时 SQLite
普通成功日志
普通成功截图
临时配置备份
本轮临时 worktree
无复用价值的本轮专用构建缓存/产物
```

只保留：

```text
/Applications/灵机.app 当前验收版本
主人正式 Production DataRoot
主人明确要求长期保留的 Acceptance 数据
Obsidian Vault
正式 Git 仓库
最终 Markdown 验收报告
脱敏公开证据摘要
哈希清单
主人明确要求保留的失败证据
```

本轮本地 DMG 默认不属于必须长期保存的核心文件；GitHub Artifact 可重复取得。若后续复验明确需要离线安装，只允许保留一个当前最新版 DMG。

禁止清理任何无法确认归属的主人数据或其他软件缓存。

---

# 8. 最终报告

最终报告写入：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_c10d255.md
```

报告至少包含：

```text
task_id
product_commit
artifact_id
dmg_sha256
macOS version
machine architecture
precheck_result
artifact_integrity_result
install_result
first_launch_result
runtime_result
api_result
ui_owner_observation
restart_result
production_pollution_count
cleanup_after
local_temp_root_absent
verdict
failed_step
root_cause_if_known
retained_core_files
```

结论只允许：

```text
PASS
FAIL
BLOCKED
```

只有同时满足：

```text
核心验收项通过
正式数据污染 = 0
清理完成
本轮临时根目录不存在
```

才能标记 PASS。

---

# 9. 给 Codex 的最后约束

读完本文件后直接开始执行。

以下信息已经提供，禁止再向用户索要：

```text
task_id
repository
product_commit
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

只有真正需要主人肉眼判断 UI，或出现本文件定义的外部阻断时，才与主人交互。
