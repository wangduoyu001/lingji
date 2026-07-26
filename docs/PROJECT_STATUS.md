# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-07-26
> Target formal branch: `master`
> Latest validated source head: `96084c49ada2adb33d2202690d3d7b98e5b695ca`
> Mainline convergence branch: `work/master-mainline-convergence`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 的第二大脑主线、Windows 打包 Sidecar、Observation-first Desktop UI 和两轮仓库治理已经完成代码与 CI 验证。当前唯一进行中的治理任务是将正式代码历史正常合入 GitHub 默认分支 `master`，结束双主线状态。

```text
PR #47  P2-11B Packaged Runtime Sidecar Manager    MERGED_AND_VALIDATED
PR #48  P2-12A Observation-first Desktop UI        MERGED_AND_VALIDATED
PR #49  Repository Governance Cleanup              MERGED_AND_VALIDATED
PR #50  Context Routing and Local Validation       MERGED_AND_VALIDATED
```

关键提交：

```text
PR #47: 6720d0cd76c8ff9e9bc38ef2df52793c0ab0f4c5
PR #48: 7e53fc29fb308b73031b39f9a2a000122653674f
PR #49: 62cc55ac6e71ad14a1756c404beabf6ccb08d74e
PR #50: 96084c49ada2adb33d2202690d3d7b98e5b695ca
```

## 2. 仓库治理状态

状态：`VALIDATED_MAINLINE_CONVERGENCE_IN_PROGRESS`

已完成：

- `docs/ARCHITECTURE.md` 是唯一当前架构权威。
- `docs/PROJECT_STATUS.md` 只维护当前状态、风险、阻塞与下一步。
- `docs/MODULES/CODE_MAP.md` 只维护代码入口、所有权和局部验收。
- `AGENTS.md` 是开发者与 AI 的最小执行入口。
- `scripts/validate.ps1` 提供 focused/full/release 本机验收入口。
- Desktop smoke 与 build 不再隐式重复执行。
- 历史阶段文档保留为证据，不覆盖当前权威。
- 过期 `.codex/context/`、PySide6/8765 和旧项目启动说明已从当前入口移除。
- 新增根 `README.md` 作为唯一 GitHub 落地页，不复制详细架构或测试历史。

PR #50 验证：

```text
tests workflow #753: SUCCESS
P0 Windows Gate #122: SUCCESS
Windows PowerShell 5.1 entry: SUCCESS
Python 3.11 / 3.12 / Windows: SUCCESS
Desktop smoke / build: SUCCESS
Tauri Rust: SUCCESS
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
- 8765 仅为迁移期兼容 API。

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

## 5. 当前安全边界

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
Default branch convergence: in progress
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible until migration parity and rollback conditions pass
Legacy startup entry removal: deferred until reference and compatibility evidence is complete
Historical acceptance report deletion: deferred because reports remain evidence
```

## 7. 下一步

```text
将 work/master-mainline-convergence 正常合入 master
-> 更新 Windows/P0 workflow 的 PR 目标为 master
-> 在最终 master 树运行完整 CI 与 Windows release gate
-> 将 feature/second-brain-memory 快进到最终 master 提交，停止作为开发主线
-> 冻结稳定基线
-> 再选择下一项正式产品开发任务
```
