# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-07-26
> Formal and default branch: `master`
> Validated code baseline: `ea93e21de0dfc622167dbf8f0cf3094f5c6f9b20`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 的第二大脑主线、Windows 打包 Sidecar、Observation-first Desktop UI、仓库治理、上下文路由和默认分支收口均已完成代码与 CI 验证。

GitHub 默认分支与唯一正式开发主线现在均为：

```text
master
```

```text
PR #47  P2-11B Packaged Runtime Sidecar Manager    MERGED_AND_VALIDATED
PR #48  P2-12A Observation-first Desktop UI        MERGED_AND_VALIDATED
PR #49  Repository Governance Cleanup              MERGED_AND_VALIDATED
PR #50  Context Routing and Local Validation       MERGED_AND_VALIDATED
PR #51  Mainline History Convergence               MERGED_AND_VALIDATED
PR #52  Master CI and Validation Finalization      MERGED_AND_VALIDATED
```

关键提交：

```text
PR #47: 6720d0cd76c8ff9e9bc38ef2df52793c0ab0f4c5
PR #48: 7e53fc29fb308b73031b39f9a2a000122653674f
PR #49: 62cc55ac6e71ad14a1756c404beabf6ccb08d74e
PR #50: 96084c49ada2adb33d2202690d3d7b98e5b695ca
PR #51: fdb2467a61b0596200f2836cf8c04d68efb6c992
PR #52: ea93e21de0dfc622167dbf8f0cf3094f5c6f9b20
```

## 2. 仓库治理状态

状态：`MERGED_AND_VALIDATED`

已完成：

- `master` 成为 GitHub 默认分支和唯一正式开发主线。
- `feature/second-brain-memory` 的完整历史通过正常 merge commit 接入 `master`，没有压成单个巨型 squash 提交。
- `docs/ARCHITECTURE.md` 是唯一当前架构权威。
- `docs/PROJECT_STATUS.md` 只维护当前状态、风险、阻塞与下一步。
- `docs/MODULES/CODE_MAP.md` 只维护代码入口、所有权和局部验收。
- `AGENTS.md` 是开发者与 AI 的最小执行入口。
- 根 `README.md` 是唯一 GitHub 落地页。
- `scripts/validate.ps1` 提供 focused/full/release 本机验收入口。
- `full` 覆盖 clean-install、Python、Desktop、Rust、Obsidian、浏览器扩展和 MCP。
- `release` 构建 Windows Sidecar/Tauri/NSIS，并整理校验和、元数据、安装说明和 Sidecar manifest。
- P0 Windows Gate 与 Windows release workflow 已改为针对 `master` PR。
- Desktop smoke 与 build 不再隐式重复执行。
- 六份过期 `.codex/context/` 自动上下文已删除。
- PySide6、8765、旧项目并行启动和机器专属配置不再作为当前操作说明。
- 历史阶段文档和验收报告保留为追溯证据，但不覆盖当前权威。

最终验证：

```text
PR #51 tests workflow #755: SUCCESS
PR #52 tests workflow #757: SUCCESS
PR #52 P0 Windows Gate #123: SUCCESS
PR #52 Windows Desktop Release Baseline #12: SUCCESS
Windows PowerShell 5.1 entry: SUCCESS
Python 3.11 / 3.12 / Windows: SUCCESS
Clean-install / compileall: SUCCESS
Desktop smoke / build: SUCCESS
Tauri Rust: SUCCESS
Packaged Sidecar build / authenticated ping / managed stop: SUCCESS
Tauri NSIS installer / checksums / metadata / artifact upload: SUCCESS
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
Default branch convergence: completed
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible until migration parity and rollback conditions pass
Legacy startup entry removal: deferred until reference and compatibility evidence is complete
Historical acceptance report deletion: deferred because reports remain evidence
Owner-machine reinstall/uninstall evidence remains release-specific and is not replaced by CI
```

## 7. 下一步

```text
以 master 的已验证代码基线冻结稳定版本
-> 不再继续无证据的仓库泛化清理
-> 只在出现明确故障、重复引用或兼容证据时处理剩余 P2 项
-> 从 master 创建后续产品功能分支
```
