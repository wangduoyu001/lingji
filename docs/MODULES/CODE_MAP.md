# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> P0 Status（P0 状态）: `MERGED_AND_VALIDATED`  
> P2-05 Validated Integration Tree（P2-05 已验证集成树）: `1bf95b8d16a9daea52b60518f0e920a0c0bd50db`  
> P2-05 Formal Merge Commit（P2-05 正式合并提交）: `c77e78c0f71339264d54fc083dbc5cfabcfaa173`  
> P2-05 Status（P2-05 状态）: `MERGED_AND_VALIDATED`  
> P2-06 Validated Head（P2-06 已验证提交）: `6dfa31148585e2cb78c83af52b752550962820c9`  
> P2-06 Formal Merge Commit（P2-06 正式合并提交）: `5ce10ed8be98784f57e8723ffc27e40e3abaffbc`  
> P2-06 Status（P2-06 状态）: `MERGED_AND_VALIDATED`

## 1. 仓库职责

```text
src/
= 长期平台主线

second_brain/
= Compatibility/Migration Runtime

desktop/lingji-control/
= 唯一正式 Desktop UI
```

规则：

- 新的正式产品能力进入 `src/`。
- `second_brain/` 只保留兼容、迁移和待退役行为。
- Desktop 只通过认证的 8766 Local Control API 访问后端。
- Desktop 不得直连 SQLite、Qdrant、Ollama、8765 或 8767。
- Obsidian CLI 正式实现位于 `src/obsidian/`；旧模块只转发。

## 2. 数据权威与派生层

```text
Obsidian Vault + Git
= 永久知识权威

storage/raw
= 原始输入归档

src/storage/state_db.py
= 任务、队列、Runtime State、Audit Event

src/retrieval/memory_db.py
= 可重建 Lexical/Metadata Index

src/sources/read_model.py
= 可重建 Structured Read Model

src/retrieval/qdrant_provider.py
= 可重建 Semantic Index Provider
```

## 3. Workspace、路径与设置

```text
src/config.py::Settings
src/runtime/workspace.py::WorkspaceResolver
src/control/runtime_settings.py::RuntimeSettingsStore
```

未配置备份目录时使用 `<storage_path>/backups`。Production、Acceptance 和测试临时根使用不同路径合同。

Obsidian Runtime Settings：

```text
obsidian_cli_enabled
obsidian_cli_path
obsidian_vault_path
obsidian_vault_name
obsidian_cli_timeout_seconds
obsidian_cli_dry_run
```

当前 Workspace Vault 始终优先于兼容回退路径。

## 4. 端口和启动入口

```text
8765 = second_brain Compatibility API
8766 = authenticated Local Control API
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
```

```text
main.py
run_service.py
run_control_api.py
run_mcp_server.py
run_extraction_worker.py
```

启动合同测试：`tests/test_startup_contracts.py`。

## 5. 统一采集与记忆链路

```text
Capture Input
-> src/capture/service.py::CaptureService
-> src/extraction/pipeline.py::ExtractionPipeline
-> Raw Snapshot
-> Adapter.extract()
-> VaultExtractionSink
-> StructuredReadModelSink
-> SourceReadModel
-> MemoryIndexCoordinator
-> HybridRetriever
-> MemoryGateway
-> MemoryInspectorFacade
-> authenticated 8766 API
-> Desktop UI
```

## 6. Capture Foundation 与手动输入

```text
src/capture/models.py
src/capture/policy.py
src/capture/deduplication.py
src/capture/manual.py
src/capture/service.py
```

正式手动方法：

```text
manual_text
manual_web
manual_file
manual_media
manual_chatgpt_export
manual_codex_report
local_control_share  # compatibility
```

能力：

- LOW_POWER、NORMAL、DEEP_CAPTURE、PAUSED。
- 两阶段去重。
- Metadata 敏感字段和保留字段保护。
- `process_later=True` 强制排队。
- ChatGPT、Codex、Web 和 Media 映射到现有 Adapter Registry。
- Office 文档和未知二进制稳定拒绝。
- 手机、浏览器、剪贴板和文件夹入口标记为 disabled/deferred。

## 7. Extraction 与队列

```text
src/extraction/models.py
src/extraction/registry.py
src/extraction/bootstrap.py
src/extraction/pipeline.py
src/extraction/queue.py::SQLiteExtractionQueue
src/extraction/worker.py
src/extraction/structured_sink.py
src/extraction/errors.py::safe_extraction_error
```

队列数据：`lingji_state.db::extraction_jobs`。

```text
queued
running
retrying
completed
failed
cancelled
```

队列操作：

```text
cancel(job_id)
retry(job_id)
list_page(status, source_type, q, limit, offset)
count(...)
```

没有新增任务表、数据库或第二套队列。

## 8. Structured Read Model

```text
src/sources/read_model.py::SourceReadModel
src/sources/service.py::SourceQueryService
src/sources/service.py::ViewerContext
```

```text
Source
-> Conversation
-> Message
-> Memory
-> Chunk
-> Vector
```

支持 Stable ID、幂等 Upsert、权限继承、显式覆盖、Message 级 Memory Link 和 Schema Version 校验。

## 9. Memory Gateway 与检索

```text
src/gateway/bootstrap.py::build_memory_gateway
src/gateway/memory.py::MemoryGateway
src/retrieval/memory_db.py
src/retrieval/qdrant_provider.py::QdrantSemanticProvider
src/retrieval/hybrid.py::HybridRetriever
```

```text
Lexical / Metadata
+ Semantic
+ RRF Hybrid
```

## 10. Memory Inspector

后端：

```text
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/memory_inspector.py::build_memory_inspector
src/control/api.py::create_control_app
```

前端：

```text
desktop/lingji-control/src/pages/MemoryInspectorPage.tsx
```

## 11. Local Control API 与 Capture Control

```text
src/control/api.py::create_control_app
src/control/capture_api.py::register_capture_routes
src/control/capture.py::CaptureControlService
src/control/service.py::LocalControlService
src/control/runtime_settings.py::RuntimeSettingsStore
```

Capture API：

```text
POST /api/capture/text
POST /api/capture/web
POST /api/capture/file
POST /api/capture/media
GET  /api/capture/status
GET  /api/capture/capabilities
GET  /api/capture/jobs
GET  /api/capture/jobs/{job_id}
POST /api/capture/jobs/{job_id}/retry
POST /api/capture/jobs/{job_id}/cancel
POST /api/capture/pause
POST /api/capture/resume
```

`POST /api/share` 是兼容别名。所有 Desktop 请求使用 `X-LingJi-Token`。

CaptureJob DTO 只暴露脱敏字段、稳定错误摘要、basename 和结构化结果引用。

## 12. Obsidian 正式包与兼容层

正式入口：

```text
src/obsidian/models.py
src/obsidian/discovery.py
src/obsidian/config.py
src/obsidian/client.py::ObsidianCliClient
src/obsidian/service.py::ObsidianService
src/obsidian/management.py
src/obsidian/system_ui.py
```

兼容入口：

```text
second_brain/obsidian_cli.py
= deprecated facade -> src.obsidian
```

CLI 发现顺序：

```text
Runtime Settings explicit path
-> OBSIDIAN_CLI_PATH
-> PATH
-> platform-standard location
-> not_found
```

Vault 顺序：

```text
Current Workspace Vault
-> Runtime Settings fallback
-> OBSIDIAN_VAULT_PATH
-> SECOND_BRAIN_OBSIDIAN_DIR compatibility fallback
-> configuration_required
```

正式命令面：

```text
version / help
vault info / vault list
search / read
create / append
files / file count
tags / tasks
daily read / append / path
```

安全合同：

- 不使用 Shell 字符串。
- 拒绝绝对路径、盘符路径、NUL 和 `..`。
- create/append 执行写后读取验证。
- 支持 Dry Run。
- 普通状态 DTO 不返回原始绝对路径、正文或 Token。

8766 API：

```text
GET  /api/obsidian/status
POST /api/obsidian/validate
POST /api/obsidian/refresh
```

## 13. Desktop UI

壳层与路由：

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/types.ts
```

P2-05 Capture Center：

```text
desktop/lingji-control/src/pages/CaptureCenterPage.tsx
desktop/lingji-control/src/pages/captureCenterApi.ts
desktop/lingji-control/src/pages/captureCenterContract.ts
desktop/lingji-control/src/pages/captureCenterTypes.ts
desktop/lingji-control/scripts/capture-center-smoke.mjs
```

P2-06 Obsidian：

```text
desktop/lingji-control/src/pages/ObsidianPage.tsx
desktop/lingji-control/scripts/obsidian-smoke.mjs
```

Tauri：

```text
desktop/lingji-control/src-tauri/Cargo.toml
desktop/lingji-control/src-tauri/Cargo.lock
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/src-tauri/capabilities/default.json
```

文件选择使用官方 Tauri 2 Dialog Plugin 和 `dialog:default`，不申请广泛文件系统权限。Desktop 不直接执行 Obsidian CLI。

## 14. 构建与验证

```text
requirements-test.txt
constraints/python-3.12-windows.txt
scripts/validate_clean_install.py
.github/workflows/p0-windows-gate.yml
```

P2-05 最终验证：

```text
Windows full pytest: 398 passed / 11 skipped / 0 failed
npm ci: PASS
npm run test:capture: PASS
npm run test:smoke: PASS
npm run build: PASS
cargo check: PASS
formal PR tests: SUCCESS
formal PR P0 Windows Gate: SUCCESS
```

P2-06 最终验证：

```text
Linux full pytest: 405 passed / 11 skipped / 0 failed / 2 warnings / 10.31s
Windows full pytest: 405 passed / 11 skipped / 0 failed / 2 warnings / 71.77s
npm ci: PASS
npm run test:obsidian: PASS
npm run test:smoke: PASS
npm run build: PASS
cargo check: PASS
formal PR tests: SUCCESS
formal PR P0 Windows Gate: SUCCESS
```

## 15. P2-05 合并记录

```text
P2-05B merge: f01e3b2cc49065cda69f1c8909933dd0c530e4ff
P2-05A merge: 46a0c5276252734c121f0cad7a56cf3a4a7c4bdc
P2-05C merge: fab0ba1b816c1228b8cfb3618aa04b5e2f2c4c3d
Validated tree: 1bf95b8d16a9daea52b60518f0e920a0c0bd50db
Formal merge: c77e78c0f71339264d54fc083dbc5cfabcfaa173
```

```text
docs/MODULES/P2_05_INTEGRATED_IMPLEMENTATION.md
docs/TEST_REPORTS/P2_05_INTEGRATED_VALIDATION_REPORT.md
```

## 16. P2-06 合并记录

```text
Validated implementation: 4b0ad577eb396030ee6baa5c3bb217e990385475
Validated final head: 6dfa31148585e2cb78c83af52b752550962820c9
Formal merge: 5ce10ed8be98784f57e8723ffc27e40e3abaffbc
```

```text
docs/MODULES/OBSIDIAN_CLI_MIGRATION_PLAN.md
docs/MODULES/P2_06_OBSIDIAN_CLI_MIGRATION_IMPLEMENTATION.md
docs/TEST_REPORTS/P2_06_OBSIDIAN_CLI_MIGRATION_TEST_REPORT.md
```

## 17. 当前状态

```text
P0 Engineering Hygiene:
MERGED_AND_VALIDATED

P2-03 / P2-03B / P2-03C / P2-04:
MERGED_AND_VALIDATED

P2-05 Manual Capture Center:
MERGED_AND_VALIDATED

P2-06 Obsidian CLI Formal Migration:
MERGED_AND_VALIDATED
```
