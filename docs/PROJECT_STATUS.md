# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-02
> Formal and default branch: `master`
> Stable Windows baseline: `18b99a6909e929df432253686eeaeee3ed9f7024`
> Current UI work: PR #56 `feature/desktop-guided-usage`
> Current stacked connector work: PR #60 `feature/unified-ai-memory-connectors`
> Current local closeout repair: `codex/pr60-vector-snapshot-truth-05376996`
> Current cleanup repair: `codex/pr60-cleanup-readonly-dir-623d3c9d`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 已完成 Windows Desktop 生命周期、Sidecar 管理、非系统盘 DataRoot、安装/重装/卸载保护和控制台黑窗缺陷修复。

当前最高优先级是让第一次接触灵机的用户能够独立完成：

```text
扫描 AI 工具
→ 连接统一记忆网关
→ 导入已有资料
→ 查看处理进度
→ 审核永久记忆
```

正式主线：

```text
master
```

当前进行中：

```text
PR #56
Desktop guided usage + AI Assistant Hub + memory import onboarding
状态：DRAFT / automated CI passed / Owner 真机验收待完成

feature/unified-ai-memory-connectors
Codex / Claude Code / WorkBuddy shared-memory connector productization
状态：PR #60 DRAFT / final local closeout RUNNING

codex/pr60-vector-snapshot-truth-05376996
Fresh Day 0 generated-scaffold truth recovery
状态：PHASE_2_REPAIR / regression and release validation in progress
```

固定 `05376996 / Artifact 8832376546` 的独立空白 Day 0 已在 2026-08-02 复现 P0：自动生成的永久记忆仪表盘和模板被错误计为 2 个正式文档、11 个分块与 11 个健康向量。当前最小修复保留 Obsidian 操作界面，只从唯一检索资格规则排除生成 Dashboard/Template；新 Artifact 和重新 Day 0 通过前，PR #60 不得转 Ready。

下一后端阶段：

```text
Issue #57  Unified Qdrant SemanticProvider Integration
状态：BLOCKED_BY_UI_AND_CONNECTOR_OWNER_ACCEPTANCE
```

## 2. 已合并稳定基线

```text
PR #47  Packaged Runtime Sidecar Manager         MERGED_AND_VALIDATED
PR #48  Observation-first Desktop UI             MERGED_AND_VALIDATED
PR #49  Repository Governance Cleanup            MERGED_AND_VALIDATED
PR #50  Context Routing and Local Validation     MERGED_AND_VALIDATED
PR #51  Mainline History Convergence              MERGED_AND_VALIDATED
PR #52  Master CI and Validation Finalization    MERGED_AND_VALIDATED
PR #53  Windows lifecycle and console defects    MERGED_AND_OWNER_VALIDATED
```

PR #53 squash 合并提交：

```text
18b99a6909e929df432253686eeaeee3ed9f7024
```

Owner 真机确认：

- Runtime connected / healthy / managed；
- production / acceptance Workspace 隔离；
- 非系统盘 DataRoot 保持；
- 三轮 Core 重启通过；
- Windows 重启恢复通过；
- 应用重启、同版本重装和卸载数据保护通过；
- 启动与重启不再出现 PowerShell、CMD 或黑色控制台窗口。

## 3. PR #56 新手引导基线

### 已实现

- 统一页面使用说明；
- 首页新手流程；
- 全局“怎么使用”抽屉；
- `AI 助手与记忆导入` 页面；
- Codex、Claude Code、WorkBuddy 安全扫描；
- ChatGPT Export 一键提交；
- Codex Report 一键提交；
- 导入任务复用现有 Capture / Extraction Queue；
- 永久记忆默认人工审核；
- Assistant Hub Python/API/Desktop Smoke；
- 快速上手、模块文档、代码地图和测试报告。

### 自动验证

```text
PR #56 Head: 8c69dfa3bc9562f80f190701244ece82896c7e17
tests #1023: SUCCESS
P0 Windows Gate #233: SUCCESS
Windows Desktop Release Baseline #122: SUCCESS
```

### 当前真实导入能力

| 工具 | 扫描 | 历史导入 | 自动历史同步 |
|---|---:|---:|---:|
| ChatGPT | 手动导出 | ZIP/JSON 可用 | 未实现 |
| Codex | 可检测 | Report JSON 可用 | 未实现 |
| Claude Code | 可检测 | Adapter 待开发 | 未实现 |
| WorkBuddy | 安装检测 | Adapter 待开发 | 未实现 |

“检测到”不得显示为“已连接”。Claude Code 与 WorkBuddy 当前不会读取对话正文。

## 4. 统一 AI 记忆连接器阶段

### 目标

让本机 AI 在今后的任务中使用同一套 LingJi Memory Gateway：

```text
AI 读取主人批准的记忆
→ 完成任务
→ propose_memory 提交候选
→ 主人人工审核
→ 正式永久记忆
```

### 已实现代码

- 安装版 `lingji-core.exe --service mcp`；
- Control Runtime 托管 hidden/no-window MCP 子进程；
- authenticated `127.0.0.1:8767/mcp`；
- owner-local MCP Token；
- MCP Runtime 状态与父进程退出治理；
- Codex 配置预览、冲突检测、备份、写入、测试和回滚；
- Claude Code 官方 CLI 设置、测试和移除；
- WorkBuddy / CodeBuddy 安全配置复制；
- Desktop 连接状态、预览、确认、测试和回滚；
- 8766 管理接口认证；
- 8767 Bearer 认证；
- Python、Desktop Smoke 和 Windows 打包合同测试；
- 模块文档与实施报告。

### 当前连接能力

| 客户端 | 实时读取 LingJi | 提交候选记忆 | 设置方式 | 历史导入 |
|---|---:|---:|---|---:|
| Codex | 代码完成，待真机 | 代码完成，待真机 | 一键预览与设置 | Report 已有 |
| Claude Code | 代码完成，待真机 | 代码完成，待真机 | 官方 CLI 一键设置 | 待 Adapter |
| WorkBuddy / CodeBuddy | 配置生成，待客户端验证 | 配置生成，待客户端验证 | 复制到官方自定义连接器 | 待 Adapter |
| ChatGPT | 本轮不覆盖本地实时连接 | 本轮不覆盖 | 后续远程/受管方案 | Export 已有 |

### 强制限制

```text
automatic_core_memory_write = false
owner_approved_memory_only = true
candidate_write_available = true
```

第一版所有本机客户端使用同一 `lingji-local` owner-approved 记忆视图。每个 AI 的独立 Agent Scope、私密记忆权限矩阵和远程访问尚未实现，不得提前宣称完成。

## 5. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则：

- 新正式能力进入 `src/`；
- Desktop 只通过认证的 8766 Local Control API 访问后端；
- 安装版 AI 客户端只通过认证的 8767 MCP 使用记忆；
- `second_brain/` 不接收新的正式产品能力；
- Obsidian CLI 正式实现位于 `src/obsidian/`；
- 开发环境 MCP 可使用 stdio，安装版使用受管 Streamable HTTP；
- 8765 仅为迁移期兼容 API。

## 6. 数据权威

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、运行状态与审计事件

lingji_memory.db
= 可重建 Lexical/Metadata Index 与 Structured Read Model

Qdrant
= 可重建 Semantic Index
```

SQLite 索引、Qdrant 和 Structured Read Model 均为派生数据，不得取代 Obsidian Vault + Git 的正式知识权威。

## 7. 当前安全边界

- Auto Review 仅 OFF/SHADOW，ACTIVE 继续拒绝；
- 不自动批准、拒绝、删除或覆盖正式记忆；
- 不自动删除或重建生产 Qdrant Collection；
- 不自动下载大型模型；
- 8766 与 8767 默认只绑定 `127.0.0.1`；
- Desktop 不直连数据库、Qdrant、Ollama 或兼容 API；
- Connector API 不接受任意客户端、任意命令或任意配置路径；
- 客户端配置写入前必须预览、备份和明确确认；
- Token 不得进入公开诊断、日志、截图或 Git；
- Windows 打包版尚不宣称自动更新或代码签名；
- AI 助手发现不得读取未知第三方数据库或账号凭据。

## 8. 当前风险与阻塞

```text
P0 Windows lifecycle defects: closed by PR #53
PR #56 owner-machine onboarding acceptance: pending
Unified connector automated CI: pending
Unified connector installed artifact: pending
Unified connector owner-machine acceptance: pending
Claude Code history adapter: not implemented
WorkBuddy / CodeBuddy history adapter: not implemented
Per-AI Agent Scope UI: not implemented
ChatGPT live connector: not implemented
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible
```

当前 `bge-m3` / Qdrant 统一语义主线仍由 Issue #57 管理，不在 UI 与连接器阶段顺手扩展。

## 9. 下一步

```text
锁定 unified connector 最终代码树
→ 创建 stacked Draft PR 到 feature/desktop-guided-usage
→ tests / P0 Windows Gate / Windows Release 全部成功
→ 生成唯一 Windows 验收安装包
→ Owner 先验收 PR #56 新手流程
→ Owner 验收 Codex / Claude / WorkBuddy 连接、读取、候选提交与回滚
→ Owner 明确 PASS 后先合并 PR #56
→ 将 connector PR 重定向到最新 master 并重新跑最终 CI
→ 合并 connector PR
→ 启动 Issue #57
```

UI 与连接器未通过 Owner 真机验收前，不得宣布“所有 AI 已接入灵机记忆”，也不得开始 Qdrant 后端主线。
