# Owner Autopilot Phase 3 实施与测试报告

## 1. 来源

本轮直接由 M5 真机报告 `MACOS_M5_PHYSICAL_ACCEPTANCE_bf9da9ff.md` 驱动，不以代码门禁通过代替主人体验。

上一轮真实结论：`FAIL / DO NOT MERGE`。

确认阻断：

- `M5-IDENTITY-001`：PR Artifact 内嵌 GitHub PR merge commit，而不是产品 Head；
- `M5-UX-002`：首次启动仍要求主人手动选择资料目录，智能化不足；
- `M5-ISOLATION-001`：验收 Runtime 在任务根目录之外创建 `~/Documents/acceptance`；
- `M5-INSTALL-001`：覆盖旧 `.app` 时可能残留旧 sealed resources 并导致签名失效。

主人补充结论：第二轮主要是信息收敛，仍未达到“系统自动扫描、自动判断、自动完成安全动作，只在真正权限边界询问主人”的目标。

## 2. Phase 3 产品目标

本轮不再做卡片压缩或文案换皮，改造首次启动与日常首页的控制合同：

```text
启动 LingJi
→ 自动选择平台安全资料目录
→ 自动建立/恢复 Runtime
→ 自动扫描与维护已允许的元数据
→ 自动重试/恢复可逆异常
→ 首页只显示当前结果与例外
→ 只有正文读取、永久记忆、不可逆操作询问主人
```

这与 Codex++ 值得参考的部分一致：后台 launcher/manager 尽量自行完成启动、诊断、修复与同步，管理 UI 用于例外和干预，而不是要求用户逐项配置。

## 3. 实现范围

### 3.1 首次启动自动准备

`runtime_bootstrap.rs` 新增：

- macOS 自动默认资料根：用户 `Library/Application Support/LingJiData`；
- 自动选择配置用 `auto_selected=true` 标记；
- `runtime_autoconfigure` / `configure_default()`；
- 正常首次启动不再依赖 `owner_confirmed=true`；
- 已有合法 Production 配置继续复用；
- 手动选目录保留为自动准备失败后的高级兜底；
- Windows 不偷偷写系统盘：如果不能安全确定非系统盘，继续进入手动兜底，而不是复制 Mac 策略。

### 3.2 验收环境物理隔离

新增临时环境变量：

```text
LINGJI_ACCEPTANCE_DATA_ROOT
```

规则：

- 只用于明确的本机验收进程；
- 优先级高于日常 Production bootstrap；
- 使用任务单指定的绝对临时根；
- 不持久化为日常配置；
- 普通启动没有该变量时，不允许继续复用历史 `acceptance` workspace；
- 验收结束删除该任务根，不影响主人 Production。

目标是堵住 `~/Documents/acceptance` 这种跨任务写入。

### 3.3 首页从“状态面板”变为“主人例外面板”

首页删除技术 Metric 网格。默认只表达：

1. 当前是否有主人必须确认的事项；
2. 灵机是否正在自动处理系统异常；
3. 当前工作；
4. AI 来源是否已自动接管元数据。

Qdrant、Embedding、模型、磁盘、端口等仍保留在高级工具/诊断，不从系统删除，只是不占日常首页。

### 3.4 AI 来源从“发现”升级为“接管”

- 15 秒元数据扫描继续后台执行；
- 无需主人操作时压成被动状态行；
- 发现 Codex 等工具后，不把几千条元数据计数做成主要任务；
- 发现真正需要正文读取的导出包时，只弹一个授权动作；
- 授权后继续走现有正式队列、去重、处理链；
- 未授权正文读取仍为 0；
- 永久记忆仍需审核。

### 3.5 精确 Artifact 身份

macOS / Windows PR release workflow 改为显式 checkout：

```text
github.event.pull_request.head.sha || github.sha
```

并验证：

```text
git rev-parse HEAD == expected product SHA
```

macOS 进一步检查 `.app` 与最终 DMG 内主二进制包含精确产品 SHA，防止再次出现 PR merge commit 冒充产品 Head。

### 3.6 安装替换

验收协议同步升级：禁止把新 `.app` 内容直接叠加复制到旧 `.app` 包内部。旧 App 先整体移到任务临时备份，再完整复制新 App；新 App 签名验证失败则恢复旧 App。

## 4. 安全边界

Phase 3 自动化明确不包含：

- 未授权读取 ChatGPT / Codex / Claude 等真实正文；
- 自动批准永久记忆；
- 自动删除或重建 Production Qdrant；
- 自动修改外部 AI 客户端配置；
- 自动删除主人文件；
- 高风险修复无备份直接执行。

“智能化”只扩大安全、可逆、可验证动作的自动化范围，不通过放宽隐私或不可逆操作门禁实现。

## 5. 自动测试合同

本提交同步更新：

- `assistant-autopilot-smoke.mjs`
  - 自动接管而非大块发现 UI；
  - 正文/永久记忆授权边界；
  - 自动 bootstrap；
  - acceptance override；
- `observation-first-ui-smoke.mjs`
  - 首次启动不得以手选目录作为正常主流程；
  - 首页不得恢复技术 Metric 网格；
  - 手动路径只能作为失败兜底；
- `macos-release-smoke.mjs`
  - macOS 自动默认目录合同；
  - task-scoped acceptance override；
  - exact product source / embedded commit identity；
- Rust unit tests
  - `auto_selected` 与 owner-selected 配置合同；
  - workspace/path 基础约束。

## 6. CI 状态

本报告随 Phase 3 产品变更进入同一提交。提交前不宣称 CI 已通过。

必须等待以下全部为 `PASS`：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
acceptance-doc-sync
local-execution-handoff
```

任何失败先修复再生成新 Artifact，不允许把红灯写成“已知不影响”。

## 7. 下一轮 M5 验收重点

新 Artifact 生成后，真机必须重新验证：

- 第一次打开不需要主人选择存储目录即可进入正常首页；
- 验收 Runtime 所有写入都在 `LINGJI_ACCEPTANCE_DATA_ROOT` 指定任务根；
- 页面不再用“发现 2 个工具 / 4400 条记录”作为主要价值展示；
- 没有主人决策时首页应非常安静，明确“无需操作”；
- 有系统异常时先显示“自动处理中”，不冒充主人待办；
- 真实正文读取、永久记忆和不可逆操作继续要求主人；
- App 替换安装后 `codesign --verify --deep --strict` 仍通过；
- UI/Release Metadata 中产品 commit 与任务单精确一致。

## 8. 合并条件

PR #88 保持 Draft。只有 Phase 3 精确 Artifact 完成 M5 真机复验，且主人明确认为智能化/自动化主流程达到可用水平后，才进入合并评估。
