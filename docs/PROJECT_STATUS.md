# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-07-26
> Formal branch: `feature/second-brain-memory`
> Formal head: `62cc55ac6e71ad14a1756c404beabf6ccb08d74e`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 的第二大脑主线、Windows 打包 Sidecar、Observation-first Desktop UI 与第一轮仓库治理清理已进入正式功能分支。

```text
PR #47  P2-11B Packaged Runtime Sidecar Manager   MERGED_AND_VALIDATED
PR #48  P2-12A Observation-first Desktop UI       MERGED_AND_VALIDATED
PR #49  Repository Governance Cleanup             MERGED_AND_VALIDATED
```

关键合并提交：

```text
PR #47: 6720d0cd76c8ff9e9bc38ef2df52793c0ab0f4c5
PR #48: 7e53fc29fb308b73031b39f9a2a000122653674f
PR #49: 62cc55ac6e71ad14a1756c404beabf6ccb08d74e
```

P2-11B/P2-12A 验收事实来源：

```text
docs/TEST_REPORTS/PR47_PR48_FINAL_ACCEPTANCE_REPORT.md
docs/TEST_REPORTS/P2_11B_LOCAL_WINDOWS_ACCEPTANCE_REPORT.md
docs/TEST_REPORTS/P2_11B_RUNTIME_SIDECAR_TEST_REPORT.md
docs/TEST_REPORTS/P2_12A_OBSERVATION_FIRST_DESKTOP_UI_TEST_REPORT.md
```

## 2. 仓库治理状态

状态：`MERGED_AND_VALIDATED`

已完成：

- `npm run build` 收敛为纯构建命令，Desktop smoke 由测试入口显式执行，避免同一门禁重复运行。
- Windows release workflow 保留显式 Desktop smoke、Sidecar 生命周期和 NSIS 产物验证。
- 删除历史 `work/p0-engineering-hygiene` 分支的过期 push 门禁，保留手动与 PR Windows Gate。
- `docs/ARCHITECTURE.md` 成为当前唯一架构权威。
- `docs/PROJECT_STATUS.md` 只维护当前状态、风险、阻塞和下一步。
- `docs/MODULES/CODE_MAP.md` 只维护代码入口与所有权。
- `docs/DEVELOPMENT_RULES.md` 明确最小定向读取、现有文档优先和唯一测试入口。
- 未新增长期文档、配置、依赖或平行业务实现。

验证结果：

```text
tests workflow #749: SUCCESS
P0 Windows Gate #120: SUCCESS
Windows Desktop Release Baseline #11: SUCCESS
Python 3.11 / 3.12 / Windows: SUCCESS
Desktop smoke / build: SUCCESS
Tauri Rust / packaged Sidecar / NSIS: SUCCESS
MCP / Obsidian plugin / browser capture: SUCCESS
```

## 3. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则：

- 新正式能力进入 `src/`。
- Desktop 只通过认证的 8766 Local Control API 访问后端。
- `second_brain/` 不接收新的正式产品能力。
- Obsidian CLI 正式实现位于 `src/obsidian/`。
- MCP 默认使用 stdio；可选 HTTP 使用 8767。

## 4. 数据权威

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

## 5. 已验证能力

```text
P0 Workspace / Port / Engineering Hygiene
P1 Unified Semantic Memory
P2 Vector Center / Structured Read Model / Capture / Inspector
P2 Obsidian CLI Formal Migration
P2 Codex-first Local Memory Loop
P2 Auto Review SHADOW
P2 Runtime/Desktop Reliability
P2 Owner-visible Settings Governance
P2 Windows Packaged Runtime Sidecar
P2 Observation-first Desktop UI
Repository Governance Cleanup
```

当前安全边界：

- Auto Review 仅 OFF/SHADOW，ACTIVE 继续拒绝。
- 不自动批准、拒绝、删除或覆盖正式记忆。
- 不自动删除或重建生产 Qdrant Collection。
- 不自动下载大型模型。
- 默认只绑定 `127.0.0.1`。
- Desktop 不直连数据库、Qdrant、Ollama 或兼容 API。
- Windows 打包版尚不宣称自动更新或代码签名。

## 6. 当前风险与阻塞

```text
P0 blocking defects: none recorded
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible until migration parity and rollback conditions pass
Legacy startup entry removal: deferred until reference and compatibility evidence is complete
Historical acceptance report deletion: deferred because reports remain evidence
```

## 7. 下一步

```text
冻结当前稳定基线
-> 不再继续仓库泛化清理
-> 只在出现明确证据时处理剩余 P2 项
-> 选择下一项正式产品开发任务
```
