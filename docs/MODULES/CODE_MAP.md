# CODE_MAP.md — LingJi 代码地图

> Updated: 2026-08-25
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
= 已定义但尚未接入 create_control_app 的 /api/work/* route helper

src/control/work_api.py
= 未装配的 /v1/work 草稿入口；不是正式认证 8766 API

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

### 6.4 当前合同状态与必须先修的缺口

截至 `ced1128e...`，已经进入 `master` 但尚未执行要求测试的部分：

```text
CaptureWorkBridge -> WorkStore.create_work
WorkStore -> list_work / list_events / list_pending
WorkStore -> WorkProjector -> WorkControlService
```

不能因此视为闭环完成，当前阻塞仍包括：

```text
create_control_app
!= 尚未 register_work_routes

LocalControlService
!= 尚未共享 WorkControlService / WorkStore

WorkControlService response
= {items} / {events}

Desktop pages expect
= {work, events} / {pending_actions}

Python model
= work_id / event_type / dict detail / description / resolved

TypeScript contract
= id / event / string detail / summary / reason

Outcome / NextAction
!= 尚无完整 Store read / API / Desktop projection
```

`src/control/work_api.py` 还包含一个未装配的 `/v1/work` 草稿，并且默认构造路径与当前 `WorkProjector` 构造合同不一致。它不得被当作正式 API 已存在的证据。

详细开发顺序与 UI 门禁见 `docs/PROJECT_STATUS.md` 的 SB-0 至 SB-8。

### 6.5 已有合同测试与仍缺门禁

已存在、但仓库报告尚未记录实际本机执行结果：

```text
tests/test_work_store.py
tests/test_capture_work_bridge.py
tests/test_work_control_service.py
tests/test_work_control_api.py
```

其中 `test_work_control_api.py` 当前只覆盖 `WorkControlService` 的返回结构，没有创建 FastAPI app，也没有证明路由注册和鉴权。

仍缺：

```text
tests/test_work_projector.py
正式 create_control_app /api/work/* 路由与鉴权测试
Outcome / NextAction / failure / restart 后读取测试
Python ↔ TypeScript response contract 测试
desktop/lingji-control/scripts/work-fact-smoke.mjs
Capture -> Work -> Outcome -> Memory/PendingAction/Failure 端到端测试
```

在这些门禁存在并实际通过前，不把 `/api/work/*` 视为正式 Desktop contract。

建议局部验收：

```powershell
python -m pytest -q --tb=short -k "work or capture_work"
.\scripts\validate.ps1 -Mode focused -Area control
.\scripts\validate.ps1 -Mode focused -Area capture
.\scripts\validate.ps1 -Mode focused -Area desktop
```

## Automatic Memory（Phase 1 ownership and Task 3 implementation）

本节登记 Phase 1 入口及其当前状态。Task 3 已在本分支实现并通过 focused/regression tests；其余未标记为已实现的条目仍是计划边界。

```text
Task 1:
src/automatic_memory/models.py
src/automatic_memory/source_registry.py
src/control/automatic_memory_api.py
src/control/api.py
src/control/service.py
= persistent source authorization, scan run/progress/error/recovery and authenticated 8766 routes

Task 2:
src/automatic_memory/runtime.py
run_control_api.py
src/control/service.py
src/control/api.py
src/control/automatic_memory_api.py
= packaged worker/scheduler/watcher/checkpoint composition, exact-instance lifecycle and authenticated runtime status; snapshot admission reuses the existing checkpoint/queue path and terminal consumer remains Task 3
Focused tests: `tests/test_automatic_memory_runtime.py`, `tests/test_packaged_control_api.py`, `tests/test_automatic_memory_scheduler.py`; Desktop smoke: `desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs`

Task 3:
src/automatic_memory/discovery.py
src/automatic_memory/path_policy.py
src/automatic_memory/checkpoint.py
src/automatic_memory/runtime.py
src/extraction/queue.py
src/extraction/pipeline.py
src/control/automatic_memory_api.py
src/extraction/adapters/chatgpt.py
src/extraction/adapters/codex.py
src/extraction/adapters/generic_ai_history.py
src/extraction/adapters/claude_desktop.py
src/extraction/registry.py
= authorized metadata-only discovery and bounded allowlisted enumeration; existing adapters/registry consume internal snapshot jobs into structured source/conversation/message rows; terminal Work Fact lifecycle and authenticated 8766 discovery/scan/progress/recovery reads/actions. Repair Round 1 additionally enforces terminal invalid-job handling, bounded Obsidian frontmatter reads, separator-aware sensitive filenames, inserted/reused scan counts, runtime-backed scan dispatch, source/terminal Work Fact consistency, and no Vault document publishing for automatic chat snapshots. Final Repair Round 2 adds BOM/CRLF-safe bounded frontmatter, automatic Generic AI source identity namespacing, and truthful resumed-scan Work Fact totals.
Focused tests: `tests/test_automatic_memory_discovery.py`, `tests/test_automatic_memory_runtime_flow.py`, `tests/test_automatic_memory_work_fact.py`, `tests/test_automatic_memory_obsidian.py`, `tests/test_automatic_memory_control_api.py`, `tests/test_automatic_memory_repair_round1.py`, `tests/test_automatic_memory_repair_round2.py`

Task 4:
src/automatic_memory/watcher.py
src/automatic_memory/scheduler.py
src/scheduler/cron.py
src/config.py
= watchfiles debounce, persistent scheduler lifecycle, 15-minute reconciliation and daily integrity
desktop/lingji-control/src/pages/MemorySourcesPage.tsx
desktop/lingji-control/src/pages/memorySourcesApi.ts
desktop/lingji-control/src/pages/memorySourcesTypes.ts
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/pages/OverviewPage.tsx
= first-run Chinese source discovery/authorization/scan status projection using the authenticated Task 3 endpoints; one-time onboarding and Home source/activity/memory summary. UI smoke: `cd desktop/lingji-control && npm run test:memory-sources`; rendered harness: `npm run test:e2e:memory`.
Repair coverage additionally lives in `desktop/lingji-control/src/hooks/useMemorySourcesOnboarding.ts`, `desktop/lingji-control/scripts/automatic-memory-sources-repair-smoke.mjs`, and the authenticated rendered harness; run `npm run test:memory-sources-repair` for the focused review regressions.
Task 4C adds only the Home `本次更新`/`本次跳过` fact projections and neutral unknown queue/count rendering in `desktop/lingji-control/src/pages/OverviewPage.tsx` plus the existing rendered/static smoke assertions; no backend contract or second UI state source is introduced.

Task 5:
src/obsidian/memory_scope.py
src/obsidian/memory_migration.py
src/obsidian/discovery.py
src/obsidian/service.py
= bounded memory scope, dry-run manifest, managed-derived migration and rollback (implemented; focused-tested)

Task 6:
src/auto_review/promotion.py::AutoMemoryPromotionService
src/auto_review/application.py::AutoReviewApplicationService
src/memory/lifecycle.py
src/retrieval/memory_db.py
= rebuildable derived promotion and owner/Core boundary

Task 7:
src/retrieval/temporal.py
src/retrieval/memory_db.py
src/retrieval/qdrant_provider.py
src/retrieval/hybrid.py
src/retrieval/context_pack.py
src/gateway/memory_gateway.py
src/mcp_server.py
src/project_memory/context_service.py
= one current/as_of/history/why predicate across every retrieval path

Task 8:
src/work/models.py
src/work/store.py
src/work/projector.py
desktop/lingji-control/src/contracts/workFact.ts
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/pages/ActivityPage.tsx
desktop/lingji-control/src/pages/AttentionPage.tsx
desktop/lingji-control/scripts/automatic-memory-smoke.mjs
desktop/lingji-control/package.json
= real Work Fact, Python/TypeScript DTO and 8766-backed Desktop onboarding

Task 9:
src/retrieval/context_pack.py
src/gateway/memory_gateway.py
src/mcp_server.py
src/automatic_memory/evaluation.py
= existing RAG/ContextPack/MCP extension and frozen 100-question evaluator

src/automatic_memory/quality_gate.py::AcceptanceRoots / run_quality_gate
= thin Task 4R reset orchestration over existing contracts; temporary Acceptance
  roots only (resolved OS-temp ancestry, exact lease token and owner), no
  Production/Vault settings access, nullable unmeasured evidence that never
  enters `EvaluationReport`, and `NOT_EVALUATED` before 4R2 readiness.
  `publish_quality_envelope` is the only repository report writer;
  `run_100k_benchmark` is blocked until 4R2.

Focused validation:

```powershell
python -m pytest -q tests/evaluation/test_task4_reset_runner.py tests/test_task4_reset_validation_guard.py
```

Tasks 10–11:
scripts/validate.ps1
desktop/lingji-control/scripts/macos-release-smoke.mjs
desktop/lingji-control/scripts/windows-release-smoke.mjs
scripts/build_windows_sidecar.ps1
= macOS M5 owner acceptance first, then independent Windows parity
```

Planned focused tests are named in the implementation plan and map to these exact paths. Task 4 owns the future `watchfiles==1.2.0` dependency; Task 0 does not alter dependency files. The existing `src/retrieval/context_pack.py` and `src/gateway/memory_gateway.py` are extended in place; no `src/automatic_memory/context_pack.py` or `src/gateway/memory.py` is planned.

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
