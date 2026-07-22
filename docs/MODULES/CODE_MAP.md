# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-22  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Formal Head（正式提交）: `325ad6e4a5f9d2c21bc4441039f32a28292b0f1d`  
> P2-08 / P2-09 / P2-10A Status: `MERGED_AND_VALIDATED`

## 1. 仓库职责

```text
src/
= 长期平台主线

second_brain/
= Compatibility / Migration Runtime

desktop/lingji-control/
= 唯一正式 Desktop UI
```

规则：

- 新正式能力进入 `src/`。
- `second_brain/` 只保留兼容和迁移行为。
- Desktop 只访问认证的8766 API。
- Desktop 不直连 SQLite、Qdrant、Ollama、8765 或8767。
- Obsidian CLI正式实现位于 `src/obsidian/`。

## 2. 数据权威与派生层

```text
Obsidian Vault + Git
= 永久知识权威

storage/raw
= 原始输入归档

src/storage/state_db.py
= 任务、Extraction Queue、Runtime State、Audit Event

src/retrieval/memory_db.py
= 可重建 Lexical/Metadata Index

src/sources/read_model.py
= 可重建 Structured Read Model

src/retrieval/qdrant_provider.py
= 可重建 Semantic Index Provider
```

## 3. Workspace、配置与端口

```text
src/config.py::Settings
src/runtime/workspace.py::WorkspaceResolver
src/control/runtime_settings.py::RuntimeSettingsStore
src/control/settings_governance.py::OwnerSettingsRegistry
src/control/settings_catalog.py::CompleteOwnerSettingsRegistry
```

```text
8765 = second_brain Compatibility API
8766 = authenticated Local Control API
8767 = optional MCP Streamable HTTP
stdio = default MCP transport
```

正式启动入口：

```text
main.py
run_service.py
run_control_api.py
run_mcp_server.py
run_extraction_worker.py
```

关键配置：

```text
embed_model = bge-m3
fallback_embed_model = nomic-embed-text
auto_review_mode = OFF
auto_review_ai_enabled = False
control_api_port = 8766
```

## 4. P2-10A 设置治理架构

兼容持久化层：

```text
src/control/runtime_settings.py::RuntimeSettingsStore
```

职责：

- 读取和写入既有 `runtime_settings.json`。
- 基础类型与范围校验。
- 兼容现有调用方。
- 不作为 Desktop 分组、推荐和风险的最终合同。

治理层：

```text
src/control/settings_governance.py::OwnerSettingsRegistry
```

职责：

- 使用验证后的 Settings 对象作为可对应字段的默认值来源。
- 补全推荐值、推荐原因、修改时机。
- 补全性能、存储、费用、隐私影响。
- 提供风险级别与确认要求。
- 提供 Provider 可用性和不可用原因。
- 生成变更预览。
- 执行跨字段校验。
- 阻止未经确认的高风险提交。
- 将高风险确认写入既有 Audit Event。

完整目录：

```text
src/control/settings_catalog.py::CompleteOwnerSettingsRegistry
```

当前额外收录：

```text
auto_review_mode
auto_review_ai_enabled
auto_review_timeout_seconds
```

Auto Review模式只允许OFF与SHADOW。ACTIVE不进入目录；错误ACTIVE环境值回落OFF。

正式服务：

```text
src/control/governed_service.py::GovernedLocalControlService
```

职责：

- 替换正式8766启动器中的普通LocalControlService。
- 将完整Registry共享给Obsidian与Model Inventory。
- 将支持的运行值同步到当前Settings对象。
- 使用轻量Provider能力检测。
- 加载设置页时不执行外部Obsidian CLI探测。

## 5. 设置 API

```text
src/control/settings_api.py::register_settings_governance_routes
```

既有接口：

```text
GET  /api/settings
PATCH /api/settings
POST /api/settings/reset
```

新增认证接口：

```text
POST /api/settings/preview
POST /api/settings/commit
```

正式Desktop变更链：

```text
Draft dirty values
-> preview
-> normalize and cross-validate
-> return impacts and risk
-> explicit confirmation when required
-> commit
-> existing runtime_settings.json
-> existing audit event stream
```

高风险确认短语：

```text
CONFIRM_HIGH_RISK_SETTINGS
```

该短语不是密钥，不能替代 `X-LingJi-Token`。

## 6. Desktop 设置代码

```text
desktop/lingji-control/src/pages/settingsTypes.ts
= 后端设置合同类型

desktop/lingji-control/src/pages/settingsApi.ts
= Snapshot / Preview / Commit / Reset客户端

desktop/lingji-control/src/pages/useSettingsController.ts
= 草稿、dirty计算、预览、确认、提交、重置和离开保护

desktop/lingji-control/src/pages/SettingsPage.tsx
= 搜索、筛选、动态分组和操作编排

desktop/lingji-control/src/components/settings/SettingField.tsx
= 单个设置字段显示与编辑
```

前端禁止复制：

- 后端默认值。
- 分组标签。
- 推荐值和推荐原因。
- 风险规则。
- 影响说明。
- 能力可用性。

当前交互合同：

- 全局搜索。
- 只显示已修改。
- 只看高风险。
- 只看不可用。
- 单项恢复默认。
- 分组恢复默认。
- 只提交dirty values。
- 页面离开前提示未保存草稿。
- 手动重新加载前确认。
- 重置部分设置时保留其他未保存草稿。

## 7. Runtime Truth 与硬件

```text
src/hardware/models.py
src/hardware/detectors.py
src/hardware/system_detectors.py
src/hardware/service.py::HardwareCapabilityService
src/control/service.py::LocalControlService.brain_status
```

```text
Static hardware facts
= GPU名称、ID、总显存、驱动/CUDA能力

Dynamic telemetry
= 利用率、温度、已用/空闲显存、采集时间、stale/error
```

未知动态值必须使用 `null` / `unavailable`，不得自动变成0。

## 8. Embedding、Qdrant 与检索

```text
src/model_center/embedding.py::OllamaEmbeddingProvider
src/model_center/inventory.py::LocalModelInventoryService
src/retrieval/qdrant_provider.py::QdrantSemanticProvider
src/retrieval/hybrid.py::HybridRetriever
src/gateway/memory_statistics.py::MemoryStatisticsService
src/gateway/memory.py::MemoryGateway
src/gateway/bootstrap.py::build_memory_gateway
```

```text
Lexical / Metadata
+ Semantic
+ RRF Hybrid
```

Qdrant Collection维度不匹配时：

```text
rebuild_required = true
write = blocked
collection auto-delete/rebuild = forbidden
lexical retrieval = remains available
```

## 9. Capture、Extraction 与幂等

Capture：

```text
src/capture/models.py
src/capture/policy.py
src/capture/deduplication.py::CaptureDeduplicator
src/capture/manual.py
src/capture/service.py::CaptureService
```

Extraction：

```text
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
Capture Input
-> CaptureService
-> ExtractionPipeline.enqueue
-> SQLite extraction_jobs
-> Lease / Heartbeat / Retry
-> Adapter.extract
-> Raw Snapshot
-> VaultExtractionSink
-> StructuredReadModelSink
-> MemoryIndexCoordinator
-> MemoryGateway
```

Canonical Identity：

```text
schema_version
source_type
adapter name/version
input identity
payload
effective options
```

文件使用内容SHA-256；目录使用稳定Manifest；Payload/Options使用canonical JSON。

## 10. MCP 提交与队列

```text
src/mcp_server.py
src/mcp/extraction_submission.py
src/mcp/project_context_tools.py
```

关键工具：

```text
submit_codex_work_report
capture_web_source
enqueue_chatgpt_export
extraction_job_status
extraction_queue_status
process_extraction_jobs
```

默认流程：

```text
MCP request
-> validation
-> pipeline.enqueue
-> durable SQLite job
-> worker or process_job
```

`process_now=True` 不得绕过Queue。

## 11. Structured Read Model 与 Memory Inspector

```text
src/sources/read_model.py::SourceReadModel
src/sources/service.py::SourceQueryService
src/sources/service.py::ViewerContext
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/memory_inspector.py::build_memory_inspector
```

```text
Source
-> Conversation
-> Message
-> Memory
-> Chunk
-> Vector
```

## 12. Memory Review 与生命周期

```text
src/project_memory/review_service.py::MemoryReviewService
src/project_memory/lifecycle.py::MemoryLifecycleService
src/project_memory/runtime.py
```

```text
MemoryReviewService
= 主人审核入口

MemoryLifecycleService
= 唯一正式写入器
```

approve/reject/archive/create等变更必须继续走现有owner-confirmed路径。

## 13. Auto Review Deterministic Core

```text
src/auto_review/models.py
src/auto_review/interfaces.py
src/auto_review/security.py
src/auto_review/risk.py
src/auto_review/duplicate.py
src/auto_review/evidence.py
src/auto_review/project.py
src/auto_review/link.py
src/auto_review/evaluator.py::DeterministicAutoReviewEvaluator
src/auto_review/audit.py
src/auto_review/service.py::ShadowAutoReviewService
```

```text
OFF
SHADOW
ACTIVE  # 当前实现拒绝
```

输出动作：

```text
would_auto_approve
would_append_evidence
would_auto_reject_noise
requires_owner_review
blocked
```

所有决策必须包含 `mutation_performed = false`。

## 14. Auto Review Local AI 与 API

```text
src/auto_review/local_ai.py::LocalOllamaReviewer
src/auto_review/application.py::AutoReviewApplicationService
src/control/auto_review_api.py::register_auto_review_routes
```

限制：

- 只允许loopback Ollama。
- 严格JSON。
- AI只增加风险。
- AI不改变确定性动作。
- AI不执行生命周期操作。
- 不请求或存储私有思维链。

8766 SHADOW API：

```text
GET  /api/auto-review/status
GET  /api/auto-review/decisions
GET  /api/auto-review/decisions/{decision_id}
GET  /api/auto-review/metrics
POST /api/auto-review/evaluate/{subject_id}
POST /api/auto-review/feedback
POST /api/auto-review/audit/verify
```

不存在approve、reject、delete、execute或ACTIVE启用接口。

## 15. Local Control API

```text
src/control/api.py::create_control_app
src/control/service.py::LocalControlService
src/control/governed_service.py::GovernedLocalControlService
src/control/settings_api.py::register_settings_governance_routes
src/control/capture_api.py::register_capture_routes
src/control/auto_review_api.py::register_auto_review_routes
src/control/p2_07_api.py::register_p2_07_routes
run_control_api.py
```

所有Desktop请求继续使用 `X-LingJi-Token`。

## 16. Desktop Shell 与 Polling

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/DesktopUX.css
```

```text
desktop/lingji-control/src/hooks/usePollingResource.ts
desktop/lingji-control/src/contracts/resourceState.ts
desktop/lingji-control/src/contracts/brainStatus.ts
```

Polling合同：

```text
enabled
interval
manual refresh
pause/resume
AbortController
no overlap
failure backoff
hidden-window pause
stale state
last success/attempt timestamps
preserve previous data
```

五组导航：

```text
home
memory
ingestion
runtime
operations
```

## 17. Desktop 关键页面

```text
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/pages/BrainStatusPage.tsx
desktop/lingji-control/src/pages/CodexWorkspacePage.tsx
desktop/lingji-control/src/pages/MemoryReviewPage.tsx
desktop/lingji-control/src/pages/AutoReviewPage.tsx
desktop/lingji-control/src/pages/MemoryInspectorLoopPage.tsx
desktop/lingji-control/src/pages/CaptureCenterPage.tsx
desktop/lingji-control/src/pages/VectorCenterPage.tsx
desktop/lingji-control/src/pages/SystemComputePage.tsx
desktop/lingji-control/src/pages/ModelsPage.tsx
desktop/lingji-control/src/pages/JobsPage.tsx
desktop/lingji-control/src/pages/SettingsPage.tsx
desktop/lingji-control/src/pages/ObsidianLoopPage.tsx
```

## 18. Obsidian 正式实现

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

## 19. 构建与验证

```text
requirements-test.txt
constraints/python-3.12-windows.txt
scripts/validate_clean_install.py
.github/workflows/tests.yml
.github/workflows/p0-windows-gate.yml
```

P2-10A关键测试：

```text
tests/test_settings_governance.py
tests/test_settings_governance_api.py
desktop/lingji-control/scripts/settings-governance-smoke.mjs
desktop/lingji-control/scripts/ui-modular-smoke.mjs
desktop/lingji-control/scripts/hardware-smoke.mjs
```

最终验证：

```text
formal P2-10A merge: 325ad6e4a5f9d2c21bc4441039f32a28292b0f1d
tests workflow #709: SUCCESS
P0 Windows Gate #102: SUCCESS
Python 3.11 / 3.12: SUCCESS
Windows full tests: SUCCESS
14-script Desktop smoke: SUCCESS
React/Vite build: SUCCESS
Tauri Rust check: SUCCESS
```

## 20. 文档索引

```text
docs/MODULES/P2_10A_SETTINGS_GOVERNANCE_CORE.md
docs/TEST_REPORTS/P2_10A_SETTINGS_GOVERNANCE_TEST_REPORT.md
docs/MODULES/P2_09A_RUNTIME_TRUTH.md
docs/MODULES/P2_09B_CANONICAL_IDEMPOTENCY.md
docs/MODULES/P2_09C_DESKTOP_DATA_LAYER.md
docs/MODULES/P2_09D_DESKTOP_UX_AUTO_REVIEW.md
docs/MODULES/P2_08A_AUTO_REVIEW_CORE.md
docs/MODULES/P2_08B_LOCAL_AI_REVIEWER.md
docs/MODULES/P2_08B_SHADOW_API.md
```

## 21. 当前状态

```text
P0 - P2-09:
MERGED_AND_VALIDATED

P2-10A Settings Governance Core:
MERGED_AND_CI_VALIDATED

Issue #11:
CLOSED_COMPLETED

下一开发阶段:
P2-10B Desktop UI / Information Architecture Refinement
```
