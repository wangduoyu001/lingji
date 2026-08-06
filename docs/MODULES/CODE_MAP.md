# CODE_MAP.md — LingJi 代码地图

> Updated: 2026-07-29  
> Scope: code entry points, ownership and focused validation only  
> Architecture: `docs/ARCHITECTURE.md`  
> Current status: `docs/PROJECT_STATUS.md`  
> Full test evidence: `docs/TEST_REPORTS/`

本文件只回答三件事：代码在哪里、谁负责什么、修改后先跑什么。阶段状态、提交 SHA、CI 编号和历史测试结果不在此重复维护。

## 1. 仓库所有权

```text
src/
= 长期平台主线

second_brain/
= 兼容、迁移与验收来源

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
= Windows 打包 Runtime 入口
= 8766 Control + managed 8767 authenticated MCP child

run_mcp_server.py
= 开发环境 MCP 入口

run_extraction_worker.py
= 独立 Extraction Worker 入口
```

旧入口：

```text
start_lingji.py
start_lingji.bat
```

旧入口只启动原有 Core 链路，不得接入 Second Brain 服务或替代正式 8766/Sidecar 生命周期。

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

src/memory/vault_layout.py::VaultLayout.should_index
= 单一 Vault 的检索资格权威；生成的 Dashboard/Template 不进入正式记忆索引

src/model_center/embedding.py::OllamaEmbeddingProvider
src/model_center/inventory.py::LocalModelInventoryService
src/gateway/memory_gateway.py::MemoryGateway
src/gateway/bootstrap.py::build_memory_gateway
src/gateway/memory_statistics.py::MemoryStatisticsService
src/gateway/memory_inspector.py::MemoryInspectorFacade
```

Qdrant 失败时 Lexical 检索继续工作；维度不匹配只标记 `rebuild_required`，不得自动删除生产 Collection。服务可用但 Collection/向量为空时，空库事实优先于尚未验证的 Embedding 状态，必须报告 `empty / collection_empty`。
新 DataRoot 中自动生成的 `00-System/Permanent-Memory.md` 和 `00-System/Templates/**` 仅服务主人操作界面，不得计入文档、Core Memory、分块或向量；`00-System/Rules` 与正式知识路径继续按统一资格规则索引。

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area retrieval
python -m pytest -q tests/test_vault_layout.py tests/test_semantic_runtime_wiring.py tests/test_permanent_memory_gateway.py tests/test_vector_truth_contract.py
```

Desktop Inspector 变化额外运行：

```powershell
cd desktop/lingji-control
npm run test:inspector
```

## 5. 来源、Capture、AI 助手与 Extraction

```text
src/sources/read_model.py::SourceReadModel
src/sources/service.py::SourceQueryService

src/assistant_hub/discovery.py::AiAssistantDiscoveryService
= Codex / Claude Code / WorkBuddy 安全只读发现与能力分级

src/assistant_hub/connectors.py::AiMemoryConnectorService
= Codex / Claude Code / WorkBuddy MCP 配置预览、备份、设置、测试与回滚

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

正式链路：

```text
Assistant scan
-> authenticated 8766 metadata-only discovery

Assistant connector setup
-> preview
-> backup
-> apply
-> test
-> rollback

Capture Input / Assistant Import
-> CaptureService
-> ExtractionPipeline.enqueue
-> SQLite extraction_jobs
-> Adapter.extract
-> Raw Snapshot
-> VaultExtractionSink / StructuredReadModelSink
-> MemoryIndexCoordinator
-> MemoryGateway
-> Human Memory Review
```

AI 助手发现只检查固定候选路径和文件元数据，不读取对话正文，不跟随符号链接，不返回真实绝对路径。连接器只允许固定客户端、固定命令与固定配置目标；ChatGPT Export 与 Codex Report 继续复用正式 Capture 链路。

重点测试：

```text
tests/test_assistant_hub_discovery.py
tests/test_assistant_hub_api.py
tests/test_ai_memory_connectors.py
tests/test_extraction_idempotency.py
tests/test_mcp_extraction_submission.py
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs
desktop/lingji-control/scripts/capture-center-smoke.mjs
```

局部验收：

```powershell
python -m pytest -q tests/test_assistant_hub_discovery.py tests/test_assistant_hub_api.py tests/test_ai_memory_connectors.py
.\scripts\validate.ps1 -Mode focused -Area capture
cd desktop/lingji-control
node scripts/assistant-hub-smoke.mjs
node scripts/assistant-memory-connectors-smoke.mjs
```

## 6. 记忆审核与 Auto Review

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

局部验收：

```powershell
python -m pytest -q --tb=short -k "memory_review or memory_lifecycle or auto_review"
cd desktop/lingji-control
npm run test:memory-review
```

## 7. Local Control API 与 MCP

```text
src/control/api.py::create_control_app
src/control/service.py::LocalControlService
src/control/governed_service.py::GovernedLocalControlService
src/control/settings_api.py::register_settings_governance_routes
src/control/capture_api.py::register_capture_routes
= Capture API + Assistant Hub discovery + connector management routes
src/control/auto_review_api.py::register_auto_review_routes
src/control/memory_inspector.py::build_memory_inspector

src/mcp_server.py
= shared memory MCP tools
src/mcp_http.py
= loopback Bearer authentication + packaged Streamable HTTP ASGI app
src/mcp/extraction_submission.py
src/mcp/project_context_tools.py
```

端口与认证：

```text
8766 = authenticated Local Control API / Tauri gateway
8767 = packaged authenticated loopback MCP HTTP
stdio = development/compatibility MCP transport
8765 = compatibility API only
```

MCP 主工具：

```text
get_core_memory
search_memory
fetch_memory
build_context_pack
propose_memory
recent_changes
memory_health
```

`propose_memory` 只能生成候选，不能直接写 Core Memory。Desktop 只使用认证的 8766，不直连 SQLite、Qdrant、Ollama 或兼容 API。

局部验收：

```powershell
.\scripts\validate.ps1 -Mode focused -Area control
python -m pytest -q tests/test_mcp_http_auth.py tests/test_packaged_mcp_runtime.py
```

MCP 提交链路变化额外运行：

```powershell
python -m pytest -q --tb=short -k "mcp or extraction_submission or project_context"
```

## 8. Desktop 与 Windows Sidecar

React 主入口：

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/components/RuntimeBoundary.tsx
desktop/lingji-control/src/components/CurrentWorkPanel.tsx
```

新手引导与 AI 记忆入口：

```text
desktop/lingji-control/src/pages/AssistantHubPage.tsx
desktop/lingji-control/src/pages/AssistantHubPage.css
desktop/lingji-control/src/components/AssistantConnectorPanel.tsx
desktop/lingji-control/src/components/PageGuide.tsx
desktop/lingji-control/src/components/UsageGuideDrawer.tsx
desktop/lingji-control/src/pages/OverviewPage.tsx
```

Observation-first 页面：

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
```

Tauri/Sidecar：

```text
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/src-tauri/src/runtime_manager.rs
desktop/lingji-control/src-tauri/tauri.sidecar.conf.json
desktop/lingji-control/src-tauri/windows/sidecar-hooks.nsh
run_packaged_control_api.py
scripts/build_windows_sidecar.ps1
requirements-sidecar-build.txt
```

生命周期合同：

```text
Tauri Desktop
-> Rust RuntimeManager
-> packaged lingji-core.exe --service control
-> authenticated 127.0.0.1:8766
-> managed hidden lingji-core.exe --service mcp
-> authenticated 127.0.0.1:8767/mcp
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

## 9. Obsidian

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

## 10. 构建、测试与 CI 入口

```text
scripts/validate.ps1
= 本地 focused / full / release 统一入口

scripts/validation_git.ps1::Get-GitValue
= 验证摘要与本地发布元数据的精确 Git Commit / Branch 身份读取

requirements-test.txt
requirements-sidecar-build.txt
requirements-mcp.txt
constraints/python-3.12-windows.txt
scripts/validate_clean_install.py
tests/test_validation_git_identity.py

scripts/cleanup_acceptance_workspace.py
tests/test_cleanup_acceptance_workspace.py
= 精确 task-id/root/单层目标的本机验收清理；Windows 普通只读目录删除前解除只读属性，链接不跟随

desktop/lingji-control/package.json
desktop/lingji-control/scripts/run-smoke-suite.mjs
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs
desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs
desktop/lingji-control/scripts/windows-release-smoke.mjs

.github/workflows/tests.yml
.github/workflows/p0-windows-gate.yml
.github/workflows/windows-desktop-release.yml
```

使用规则：

```text
开发中      -> focused
合并前最终树 -> full，一次
正式发布    -> release
```

成功时只读取 `output/validation/.../summary.json` 或 `summary.md`；失败时再读取对应日志。具体历史通过结果只记录在 `docs/TEST_REPORTS/` 和 `docs/PROJECT_STATUS.md`。
