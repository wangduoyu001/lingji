# CODE_MAP.md — LingJi 代码地图

> Updated: 2026-08-22  
> Scope: code entry points, ownership and focused validation only  
> Architecture: `docs/ARCHITECTURE.md`  
> Current status and development order: `docs/PROJECT_STATUS.md`  
> Full test evidence: `docs/TEST_REPORTS/`

本文件只回答三件事：代码在哪里、谁负责什么、修改后先跑什么。阶段状态、提交 SHA、CI 编号和历史测试结果不在此重复维护。

## 1. 仓库所有权

```text
src/
= 长期平台主线

second_brain/
= 兼容、迁移与验收来源，不新增主产品能力

desktop/lingji-control/
= 唯一正式 Desktop UI
```

稳定架构边界以 `docs/ARCHITECTURE.md` 为准。

## 2. 正式运行入口

```text
main.py
= PEMISCore 核心入口

run_service.py
= 长期服务、Extraction Worker 与系统状态刷新

run_control_api.py
= 开发/本地认证 8766 Local Control API

run_packaged_control_api.py
= Windows 打包 Sidecar 入口

run_mcp_server.py
= MCP 入口

run_extraction_worker.py
= 独立 Extraction Worker 入口
```

旧入口：

```text
start_lingji.py
start_lingji.bat
```

旧入口只启动兼容 Core 链路，不得替代正式 8766/Sidecar 生命周期。

相关验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area control
.\scripts\validate.ps1 -Mode focused -Area sidecar
```

## 3. Workspace、配置与状态

```text
src/config.py::Settings
src/runtime/workspace.py::WorkspaceResolver
src/control/runtime_settings.py::RuntimeSettingsStore
src/control/settings_governance.py::OwnerSettingsRegistry
src/control/settings_catalog.py::CompleteOwnerSettingsRegistry
src/storage/state_db.py
```

```text
lingji_state.db
= 任务、队列、运行状态与审计事件
```

重点测试：

```text
tests/test_settings_governance.py
tests/test_settings_governance_api.py
tests/test_runtime_truth.py
```

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area control
```

## 4. 记忆、检索与向量

```text
src/retrieval/memory_db.py
= 可重建 Lexical/Metadata Index

src/retrieval/qdrant_provider.py::QdrantSemanticProvider
= 可重建 Semantic Index Provider

src/retrieval/hybrid.py::HybridRetriever
= Lexical + Semantic + RRF

src/model_center/embedding.py::OllamaEmbeddingProvider
src/model_center/inventory.py::LocalModelInventoryService
src/gateway/memory.py::MemoryGateway
src/gateway/bootstrap.py::build_memory_gateway
src/gateway/memory_statistics.py::MemoryStatisticsService
src/gateway/memory_inspector.py::MemoryInspectorFacade
```

Qdrant 失败时 Lexical 检索继续工作；维度不匹配只标记 `rebuild_required`，不得自动删除生产 Collection。

重点测试：

```text
tests/test_memory_capability_contract.py
tests/test_memory_inspector_api.py
tests/test_memory_retrieval.py
tests/test_qdrant_semantic_provider.py
```

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area retrieval
```

Desktop Inspector 变化额外运行：

```powershell
cd desktop/lingji-control
npm run test:inspector
```

## 5. 来源、Capture 与 Extraction

```text
src/sources/read_model.py::SourceReadModel
src/sources/service.py::SourceQueryService

src/capture/models.py
src/capture/policy.py
src/capture/deduplication.py::CaptureDeduplicator
src/capture/manual.py
src/capture/service.py::CaptureService

src/extraction/models.py
src/extraction/registry.py
src/extraction/bootstrap.py
src/extraction/idempotency.py
src/extraction/pipeline.py::ExtractionPipeline
src/extraction/queue.py::SQLiteExtractionQueue
src/extraction/worker.py
src/extraction/sink.py
src/extraction/structured_sink.py
```

正式数据处理链：

```text
Capture Input
-> CaptureService
-> ExtractionPipeline.enqueue
-> SQLite extraction_jobs
-> Adapter.extract
-> Raw Snapshot
-> VaultExtractionSink / StructuredReadModelSink
-> MemoryIndexCoordinator
-> MemoryGateway
```

重点测试：

```text
tests/test_capture_api.py
tests/test_capture_control.py
tests/test_capture_service.py
tests/test_extraction_idempotency.py
tests/test_mcp_extraction_submission.py
desktop/lingji-control/scripts/capture-center-smoke.mjs
```

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area capture
```

## 6. Work Fact 主人事实链

这是 2026-08-22 起 Home / Work / Attention / Capture / Memory UI 的唯一工作语义来源。

### 6.1 Domain 与 persistence

```text
src/work/models.py
= WorkItem / ExecutionEvent / Outcome / NextAction / PendingAction

src/work/store.py::WorkStore
= Work fact SQLite persistence

src/work/capture_bridge.py::CaptureWorkBridge
= Capture / extraction 向 Work fact 转换

src/work/projector.py::WorkProjector
= Desktop/read API 的工作事实投影
```

### 6.2 Control 层

```text
src/control/work_routes.py
= 目标正式 /api/work/* route helper

src/control/work_service.py::WorkControlService
= work read-model adapter

src/control/service.py::LocalControlService
= 正式 8766 service boundary

src/control/api.py::create_control_app
= 正式路由注册入口
```

### 6.3 Desktop 合同与页面

```text
desktop/lingji-control/src/contracts/workFact.ts
= Desktop Work Fact DTO

desktop/lingji-control/src/components/CurrentWorkPanel.tsx
= Home 当前工作投影

desktop/lingji-control/src/pages/ActivityPage.tsx
= Work/Activity 当前事实展示

desktop/lingji-control/src/pages/AttentionPage.tsx
= PendingAction 投影
```

### 6.4 当前必须先修的合同缺口

截至 2026-08-22，以上代码已经存在但**不能视为闭环完成**：

```text
CaptureWorkBridge.save_work
!= WorkStore.create_work

WorkProjector 需要 list_work/list_pending/list_events
但 WorkStore 当前未提供

LocalControlService 当前未正式暴露 current_work/pending_actions/work_timeline

create_control_app 当前未完成 work_routes 注册

Python work dataclass 字段/状态
!= desktop workFact.ts 字段/状态
```

详细开发顺序与 UI 门禁见 `docs/PROJECT_STATUS.md` 的 WF-0 / UI-1 ... UI-8。

### 6.5 测试缺口

当前 `tests/` 没有专门覆盖完整 Work Fact 链的测试。下一次实现变更必须补：

```text
tests/test_work_store.py
tests/test_work_projector.py
tests/test_work_control_api.py
tests/test_capture_work_bridge.py

desktop/lingji-control/scripts/work-fact-smoke.mjs
```

在这些门禁存在并通过前，不把 `/api/work/*` 视为正式 Desktop contract。

建议局部验收：

```powershell
python -m pytest -q --tb=short -k "work or capture_work"
.\scripts\validate.ps1 -Mode focused -Area control
.\scripts\validate.ps1 -Mode focused -Area capture
.\scripts\validate.ps1 -Mode focused -Area desktop
```

## 7. 记忆审核与 Auto Review

```text
src/project_memory/review_service.py::MemoryReviewService
= 主人审核入口

src/project_memory/lifecycle.py::MemoryLifecycleService
= 正式生命周期写入器

src/auto_review/evaluator.py::DeterministicAutoReviewEvaluator
src/auto_review/service.py::ShadowAutoReviewService
src/auto_review/local_ai.py::LocalOllamaReviewer
src/auto_review/application.py::AutoReviewApplicationService
src/auto_review/audit.py
```

Auto Review 只允许 OFF/SHADOW；ACTIVE 在实现层拒绝。所有 SHADOW 决策必须保持 `mutation_performed = false`。

重点测试：

```text
tests/test_auto_review_core.py
tests/test_auto_review_ai_api.py
desktop/lingji-control/scripts/memory-review-smoke.mjs
desktop/lingji-control/scripts/auto-review-shadow-smoke.mjs
```

## 8. Local Control API 与 MCP

```text
src/control/api.py::create_control_app
src/control/service.py::LocalControlService
src/control/governed_service.py::GovernedLocalControlService
src/control/settings_api.py::register_settings_governance_routes
src/control/capture_api.py::register_capture_routes
src/control/auto_review_api.py::register_auto_review_routes
src/control/memory_inspector.py::build_memory_inspector

src/mcp_server.py
src/mcp/extraction_submission.py
src/mcp/project_context_tools.py
```

端口与认证：

```text
8766 = authenticated Local Control API / Tauri gateway
8767 = optional MCP HTTP
stdio = default local MCP transport
8765 = compatibility API only
```

Desktop 只使用认证的 8766，不直连 SQLite、Qdrant、Ollama 或兼容 API。

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area control
```

## 9. Desktop 与 Windows Sidecar

React 主入口：

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/components/RuntimeBoundary.tsx
```

主人核心页面：

```text
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/pages/ActivityPage.tsx
desktop/lingji-control/src/pages/AttentionPage.tsx
desktop/lingji-control/src/pages/DiagnosticsPage.tsx
```

共享状态与轮询：

```text
desktop/lingji-control/src/hooks/usePollingResource.ts
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/contracts/resourceState.ts
desktop/lingji-control/src/contracts/brainStatus.ts
desktop/lingji-control/src/contracts/workFact.ts
```

Tauri/Sidecar：

```text
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/src-tauri/src/runtime_manager.rs
desktop/lingji-control/src-tauri/tauri.sidecar.conf.json
desktop/lingji-control/src-tauri/windows/sidecar-hooks.nsh
scripts/build_windows_sidecar.ps1
requirements-sidecar-build.txt
```

生命周期合同：

```text
Tauri Desktop
-> Rust RuntimeManager
-> packaged lingji-core.exe
-> authenticated 127.0.0.1:8766
```

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area desktop
.\scripts\validate.ps1 -Mode focused -Area sidecar
```

只有安装包、Sidecar 或发布链路变化时运行：

```powershell
.\scripts\validate.ps1 -Mode release
```

## 10. Obsidian

正式实现：

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

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area obsidian
```

## 11. 构建、测试与 CI 入口

```text
scripts/validate.ps1
= 本地 focused / full / release 统一入口

requirements-test.txt
requirements-sidecar-build.txt
constraints/python-3.12-windows.txt
scripts/validate_clean_install.py

desktop/lingji-control/package.json
desktop/lingji-control/scripts/run-smoke-suite.mjs
desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs
desktop/lingji-control/scripts/windows-release-smoke.mjs

.github/workflows/tests.yml
.github/workflows/p0-windows-gate.yml
.github/workflows/windows-desktop-release.yml
```

使用规则：

```text
开发中       -> focused
合并前最终树 -> full，一次
正式发布     -> release
```

成功时只读取 `output/validation/.../summary.json` 或 `summary.md`；失败时再读取对应日志。历史通过结果只记录在 `docs/TEST_REPORTS/`，当前结论只记录在 `docs/PROJECT_STATUS.md`。