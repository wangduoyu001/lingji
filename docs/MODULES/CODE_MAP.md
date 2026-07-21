# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> P0 Status（P0 状态）: `MERGED_AND_VALIDATED`  
> P2-05 Validated Integration Tree（P2-05 已验证集成树）: `1bf95b8d16a9daea52b60518f0e920a0c0bd50db`  
> P2-05 Status（P2-05 状态）: `READY_FOR_FORMAL_MERGE`

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

关键路径：

```text
vault_path
storage_path
raw_path
state_db_path
memory_db_path
queue_db_path
backup_path
runtime_settings_path
qdrant_path / qdrant_url / qdrant_collection
```

未配置备份目录时使用 `<storage_path>/backups`。Production、Acceptance 和测试临时根使用不同路径合同。

## 4. 端口和启动入口

```text
8765 = second_brain Compatibility API
8766 = authenticated Local Control API
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
```

启动入口：

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

正式入口：

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

正式入口：

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

状态：

```text
queued
running
retrying
completed
failed
cancelled
```

P2-05 队列操作：

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

实体关系：

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

Qdrant 单元测试使用 in-memory 合同，不要求生产 Qdrant Server。

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

API：

```text
GET /api/memory/inspector/status
GET /api/memory/inspector/sources
GET /api/memory/inspector/conversations
GET /api/memory/inspector/messages
GET /api/memory/inspector/memories
```

## 11. Local Control API 与 Capture Control

正式入口：

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

## 12. Obsidian CLI 兼容层

当前位置：

```text
second_brain/obsidian_cli.py
```

发现顺序：

```text
OBSIDIAN_CLI_PATH
-> PATH
-> platform location
-> not_found
```

Vault 名称：

```text
OBSIDIAN_VAULT_NAME
-> Windows/POSIX Vault 目录名
-> 兼容默认值
```

正式迁移目标：

```text
src/obsidian/
  config.py
  discovery.py
  models.py
  client.py
  service.py
```

## 13. Desktop UI

正式目录：`desktop/lingji-control/`。

壳层与路由：

```text
src/App.tsx
src/AppPages.tsx
src/navigation.ts
src/types.ts
```

P2-05 Capture Center：

```text
src/pages/CaptureCenterPage.tsx
src/pages/captureCenterApi.ts
src/pages/captureCenterContract.ts
src/pages/captureCenterTypes.ts
scripts/capture-center-smoke.mjs
```

Tauri：

```text
src-tauri/Cargo.toml
src-tauri/Cargo.lock
src-tauri/src/main.rs
src-tauri/capabilities/default.json
```

文件选择使用官方 Tauri 2 Dialog Plugin 和 `dialog:default`，不申请广泛文件系统权限。

构建门禁：

```text
npm ci
npm run test:capture
npm run test:smoke
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

## 14. 依赖与验证基础

```text
requirements.txt
requirements-ui.txt
requirements-media.txt
requirements-mcp.txt
requirements-test.txt
constraints/python-3.13-linux.txt
constraints/python-3.12-windows.txt
scripts/validate_clean_install.py
.github/workflows/p0-windows-gate.yml
```

## 15. P2-05 集成验证

```text
P2-05B merge: f01e3b2cc49065cda69f1c8909933dd0c530e4ff
P2-05A merge: 46a0c5276252734c121f0cad7a56cf3a4a7c4bdc
P2-05C merge: fab0ba1b816c1228b8cfb3618aa04b5e2f2c4c3d
Validated tree: 1bf95b8d16a9daea52b60518f0e920a0c0bd50db
```

```text
Windows full pytest: 398 passed / 11 skipped / 0 failed
Capture smoke: PASS
Desktop smoke: PASS
Desktop build: PASS
Cargo check: PASS
```

实施与测试报告：

```text
docs/MODULES/P2_05_INTEGRATED_IMPLEMENTATION.md
docs/TEST_REPORTS/P2_05_INTEGRATED_VALIDATION_REPORT.md
```

## 16. 当前状态

```text
P0 Engineering Hygiene:
MERGED_AND_VALIDATED

P2-03 / P2-03B / P2-03C / P2-04:
MERGED_AND_VALIDATED

P2-05 Manual Capture Center:
READY_FOR_FORMAL_MERGE
```
