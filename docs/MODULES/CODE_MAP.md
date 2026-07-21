# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> P0 Validation Branch（P0 验证分支）: `work/p0-engineering-hygiene`  
> P0 Verified Code Commit（P0 已验证代码提交）: `08b507c2855e05a1d971cb2bcae5c8d2fea578eb`  
> P0 Status（P0 状态）: `READY_FOR_FORMAL_MERGE`

## 1. 仓库职责

```text
src/
= 长期平台主线

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）
```

规则：

- 新的正式产品能力必须进入 `src/`。
- `second_brain/` 只允许兼容、迁移和待退役行为。
- Desktop 不得直连 SQLite、Qdrant、Ollama 或 Compatibility API。

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

## 3. Workspace 与路径合同

正式入口：

```text
src/config.py::Settings
src/runtime/workspace.py::WorkspaceResolver
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

P0 规则：

- 未配置备份目录时使用 `<storage_path>/backups`。
- 不允许机器专属固定盘符或用户名目录。
- Production 和 Acceptance 必须物理隔离。
- 生产系统盘保护由 `src/runtime/workspace.py` 持有。
- `tests/fixtures/workspace_paths.py` 仅允许显式测试临时根绕过系统盘限制。

## 4. 端口和进程边界

```text
8765 = second_brain Compatibility API
8766 = authenticated Local Control API
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
```

正式启动入口：

```text
main.py
run_service.py
run_control_api.py
run_mcp_server.py
run_extraction_worker.py
```

行为合同测试：

```text
tests/test_startup_contracts.py
```

测试不再逐字比较启动文件源码。

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
-> Memory Index Coordinator
-> HybridRetriever
-> MemoryGateway
-> MemoryInspectorFacade
-> authenticated 8766 API
-> Desktop UI
```

## 6. Capture Foundation

正式入口：

```text
src/capture/models.py
src/capture/policy.py
src/capture/deduplication.py
src/capture/service.py
```

现有能力：

- 文本、网页、文件、媒体入口合同。
- LOW_POWER、NORMAL、DEEP_CAPTURE、PAUSED。
- 两阶段去重。
- Metadata 敏感字段检查。
- `process_later=True` 排队合同。

下一阶段 P2-05 不创建第二套队列或数据库。

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

队列数据存储：

```text
lingji_state.db::extraction_jobs
```

状态：

```text
queued
running
retrying
completed
failed
cancelled
```

## 8. Structured Read Model

正式入口：

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

支持：

- Stable ID。
- 幂等 Upsert。
- Privacy / Project / Agent Scope。
- 权限继承与显式覆盖。
- Message 级 Memory Link。
- Schema Version 校验。

## 9. Memory Gateway 与检索

正式入口：

```text
src/gateway/bootstrap.py::build_memory_gateway
src/gateway/memory.py::MemoryGateway
src/retrieval/memory_db.py
src/retrieval/qdrant_provider.py::QdrantSemanticProvider
src/retrieval/hybrid.py::HybridRetriever
```

检索层：

```text
Lexical / Metadata
+ Semantic
+ RRF Hybrid
```

Qdrant 测试默认使用 in-memory 合同，不要求外部生产服务。

## 10. Memory Inspector

正式后端：

```text
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/memory_inspector.py::build_memory_inspector
src/control/api.py::create_control_app
```

正式前端：

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

## 11. Local Control API

正式入口：

```text
src/control/api.py::create_control_app
src/control/service.py::LocalControlService
src/control/runtime_settings.py::RuntimeSettingsStore
```

基础接口：

```text
/api/health
/api/overview
/api/brain/status
/api/jobs
/api/settings
/api/memory/inspector/*
```

所有 Desktop 请求使用 `X-LingJi-Token`。

Brain Status API 合同测试：

```text
tests/test_brain_status_e2e.py
```

该测试使用确定性注入服务，不启动真实端口、GPU 探测或本地模型服务。

## 12. Obsidian CLI 兼容层

当前位置：

```text
second_brain/obsidian_cli.py
```

当前职责：

- CLI 可执行文件发现。
- Vault 路径和名称发现。
- 兼容命令包装。

发现顺序：

```text
OBSIDIAN_CLI_PATH
-> PATH
-> platform location
-> not_found
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

迁移计划：

```text
docs/MODULES/OBSIDIAN_CLI_MIGRATION_PLAN.md
```

## 13. Desktop UI

正式目录：

```text
desktop/lingji-control/
```

关键入口：

```text
src/App.tsx
src/api.ts
src/navigation.ts
src/types.ts
src/pages/JobsPage.tsx
src/pages/MemoryInspectorPage.tsx
src-tauri/
```

构建门禁：

```text
npm ci
npm run test:smoke
npm run build
```

## 14. P0 依赖与测试基础

依赖文件：

```text
requirements.txt
requirements-ui.txt
requirements-media.txt
requirements-mcp.txt
requirements-test.txt
constraints/python-3.13-linux.txt
constraints/python-3.12-windows.txt
```

验证工具：

```text
scripts/validate_clean_install.py
.github/workflows/p0-windows-gate.yml
```

最终 P0 门禁：

```text
Windows Python 3.12 install: PASS
pip check: PASS
clean-install validator: PASS
compileall: PASS
full pytest: 359 passed / 11 skipped / 0 failed
Desktop smoke: PASS
Desktop build: PASS
```

## 15. P2-05 文件所有权

规划文档：

```text
docs/MODULES/P2_05_MANUAL_CAPTURE_CENTER_PLAN.md
docs/MODULES/P2_05_PARALLEL_OWNERSHIP.md
```

并行边界：

```text
Engineer 1:
src/control/
src/extraction/queue.py

Engineer 2:
src/capture/
必要的 Adapter 映射

Engineer 3:
desktop/lingji-control/

Integration Engineer:
共享文档、冲突解决、集成测试
```

## 16. 当前状态

```text
P0 Engineering Hygiene:
READY_FOR_FORMAL_MERGE

P2-03 / P2-03B / P2-03C / P2-04:
MERGED_AND_VALIDATED

P2-05:
PLANNED_BLOCKED_UNTIL_P0_MERGE
```
