# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-07-29
> Formal and default branch: `master`
> Stable Windows baseline: `18b99a6909e929df432253686eeaeee3ed9f7024`
> Current UI work: PR #56 `feature/desktop-guided-usage`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 已完成 Windows Desktop 生命周期、Sidecar 管理、非系统盘 DataRoot、安装/重装/卸载保护和控制台黑窗缺陷修复。

当前最高优先级不是继续堆后台能力，而是让第一次接触灵机的用户能够独立完成：

```text
扫描 AI 工具
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
PR #56  Desktop guided usage + AI Assistant Hub + memory import onboarding
状态：DRAFT / CI 与 Owner 真机验收中
```

下一后端阶段：

```text
Issue #57  Unified Qdrant SemanticProvider Integration
状态：BLOCKED_BY_PR56_OWNER_ACCEPTANCE
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

## 3. 当前 PR #56 范围

### 已实现

- 统一页面使用说明；
- 首页新手流程；
- 全局“怎么使用”抽屉；
- `AI 助手与记忆导入`页面；
- Codex、Claude Code、WorkBuddy 安全扫描；
- ChatGPT Export 一键提交；
- Codex Report 一键提交；
- 导入任务复用现有 Capture / Extraction Queue；
- 永久记忆默认人工审核；
- Assistant Hub Python/API/Desktop Smoke；
- 快速上手、模块文档、代码地图和测试报告。

### 当前真实能力

| 工具 | 扫描 | 导入 | 自动同步 |
|---|---:|---:|---:|
| ChatGPT | 手动导出 | ZIP/JSON 可用 | 未实现 |
| Codex | 可检测 | Report JSON 可用 | 正式 Connector 待配置/扩展 |
| Claude Code | 可检测 | Adapter 待开发 | 未实现 |
| WorkBuddy | 安装检测 | Adapter 待开发 | 未实现 |

“检测到”不得显示为“已连接”。Claude Code 与 WorkBuddy 当前不会读取对话正文。

### 安全边界

- 扫描只读取允许路径和文件元数据；
- 不读取浏览器登录态、Token、Cookie 或密码；
- 不跟随符号链接；
- 不返回真实绝对路径；
- 不修改第三方 AI 配置；
- 不自动写入 Core Memory；
- 永久记忆必须由主人审核。

## 4. 产品与代码主线

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
- `second_brain/` 不接收新的正式产品能力；
- Obsidian CLI 正式实现位于 `src/obsidian/`；
- MCP 默认使用 stdio，可选 HTTP 使用 8767；
- 8765 仅为迁移期兼容 API。

## 5. 数据权威

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

## 6. 当前安全边界

- Auto Review 仅 OFF/SHADOW，ACTIVE 继续拒绝；
- 不自动批准、拒绝、删除或覆盖正式记忆；
- 不自动删除或重建生产 Qdrant Collection；
- 不自动下载大型模型；
- 默认只绑定 `127.0.0.1`；
- Desktop 不直连数据库、Qdrant、Ollama 或兼容 API；
- Windows 打包版尚不宣称自动更新或代码签名；
- AI 助手发现不得读取未知第三方数据库或账号凭据。

## 7. 当前风险与阻塞

```text
P0 Windows lifecycle defects: closed by PR #53
PR #56 automated validation: running
PR #56 owner-machine onboarding acceptance: pending
Claude Code content adapter: not implemented
WorkBuddy content adapter: not implemented
Automatic third-party AI sync: not implemented
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible
```

当前 `bge-m3` / Qdrant 统一语义主线仍由 Issue #57 管理，不在 PR #56 中顺手扩展。

## 8. 下一步

```text
锁定 PR #56 最终代码树
→ tests / P0 Windows Gate / Windows Release 全部成功
→ 生成唯一 Windows 验收安装包
→ Owner 按新用户视角完成扫描、导入、进度和审核流程
→ 根据真实理解障碍调整 UI
→ Owner 明确 PASS 后合并 PR #56
→ 从最新 master 启动 Issue #57
```

PR #56 未通过 Owner 真机验收前，不得宣布 UI 已完成，也不得开始 Qdrant 后端主线。
