# CODE_MAP.md — LingJi 代码地图

> Updated（更新时间）: 2026-07-22  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Formal Head（正式提交）: `f955b7c8a9a28aa1351d02e5ef70be2551a565b2`  
> P2-08 / P2-09 Status: `MERGED_AND_VALIDATED`

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

- 新能力进入 `src/`。
- `second_brain/` 只保留兼容和迁移行为。
- Desktop 只访问认证的8766 API。
- Desktop 不直连 SQLite、Qdrant、Ollama、8765 或8767。
- Obsidian CLI 正式实现位于 `src/obsidian/`。

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

## 4. Runtime Truth 与硬件

```text
src/hardware/models.py
src/hardware/detectors.py
src/hardware/system_detectors.py
src/hardware/service.py::HardwareCapabilityService
src/control/service.py::LocalControlService.brain_status
```

数据边界：

```text
Static hardware facts
= GPU 名称、ID、总显存、驱动/CUDA能力

Dynamic telemetry
= 利用率、温度、已用/空闲显存、采集时间、stale/error
```

未知动态值必须使用 `null` / `unavailable`，不得自动变成0。

## 5. Embedding、Qdrant 与检索

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

Qdrant Collection 维度不匹配时：

```text
rebuild_required = true
write = blocked
collection auto-delete/rebuild = forbidden
lexical retrieval = remains available
```

## 6. Capture 与 Extraction

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
src/extraction/errors.py::safe_extraction_error
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

## 7. Canonical Idempotency

单一实现：

```text
src/extraction/idempotency.py
```

Identity Material：

```text
schema_version
source_type
adapter name/version
input identity
payload
effective options
```

规则：

- 文件使用流式 SHA-256 内容哈希。
- 目录使用排序后的相对路径 Manifest 和内容哈希。
- Payload/Options 使用 canonical UTF-8 JSON。
- Pipeline 和 Queue 只调用同一实现。
- `CaptureDeduplicator` 仍只负责短窗口提交去重。

## 8. MCP 提交与队列

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

`process_now=True` 不得绕过 Queue。

## 9. Structured Read Model 与 Memory Inspector

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

Desktop：

```text
desktop/lingji-control/src/pages/MemoryInspectorPage.tsx
```

## 10. Memory Review 与生命周期

```text
src/project_memory/review_service.py::MemoryReviewService
src/project_memory/lifecycle.py::MemoryLifecycleService
src/project_memory/runtime.py
```

权威合同：

```text
MemoryReviewService
= 主人审核入口

MemoryLifecycleService
= 唯一正式写入器
```

approve/reject/archive/create 等变更必须继续走现有 owner-confirmed 路径。

## 11. Auto Review Deterministic Core

正式包：

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

模式：

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

所有决策必须包含：

```text
risk_score
risk_level
reasons
reversible
mutation_performed = false
```

## 12. Auto Review Local AI 与 Application

```text
src/auto_review/local_ai.py::LocalOllamaReviewer
src/auto_review/application.py::AutoReviewApplicationService
src/control/auto_review_api.py::register_auto_review_routes
```

模型角色：

```text
auto_review_primary
auto_review_fallback
```

限制：

- 只允许 loopback Ollama。
- 严格 JSON。
- AI 只增加风险。
- AI 不改变确定性动作。
- AI 不执行生命周期操作。
- 不请求或存储私有思维链。

## 13. Auto Review 8766 API

```text
GET  /api/auto-review/status
GET  /api/auto-review/decisions
GET  /api/auto-review/decisions/{decision_id}
GET  /api/auto-review/metrics
POST /api/auto-review/evaluate/{subject_id}
POST /api/auto-review/feedback
POST /api/auto-review/audit/verify
```

不存在：

```text
/api/auto-review/approve
/api/auto-review/reject
/api/auto-review/delete
/api/auto-review/execute
/api/auto-review/active
```

## 14. Local Control API

```text
src/control/api.py::create_control_app
src/control/service.py::LocalControlService
src/control/runtime_settings.py::RuntimeSettingsStore
src/control/capture_api.py::register_capture_routes
src/control/auto_review_api.py::register_auto_review_routes
src/control/p2_07_api.py::register_p2_07_routes
run_control_api.py
```

所有 Desktop 请求继续使用 `X-LingJi-Token`。

## 15. Desktop Shell 与 Polling

壳层：

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/DesktopUX.css
```

统一数据层：

```text
desktop/lingji-control/src/hooks/usePollingResource.ts
desktop/lingji-control/src/contracts/resourceState.ts
desktop/lingji-control/src/contracts/brainStatus.ts
```

Polling 合同：

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

## 16. Desktop 关键页面

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
desktop/lingji-control/src/pages/ObsidianLoopPage.tsx
```

Auto Review 前端合同：

```text
desktop/lingji-control/src/pages/autoReviewTypes.ts
desktop/lingji-control/scripts/auto-review-shadow-smoke.mjs
```

## 17. Obsidian 正式实现

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

## 18. 构建与验证

```text
requirements-test.txt
constraints/python-3.12-windows.txt
scripts/validate_clean_install.py
.github/workflows/tests.yml
.github/workflows/p0-windows-gate.yml
```

关键测试：

```text
tests/test_runtime_truth.py
tests/test_extraction_idempotency.py
tests/test_mcp_extraction_submission.py
tests/test_auto_review_core.py
tests/test_auto_review_ai_api.py
tests/test_p2_08_p2_09_integration.py

desktop/lingji-control/scripts/polling-data-smoke.mjs
desktop/lingji-control/scripts/auto-review-shadow-smoke.mjs
desktop/lingji-control/scripts/run-smoke-suite.mjs
```

最终集成：

```text
formal feature implementation: 9efda7a9a976d20596dbdabda5741a5c54180954
formal documentation sync: f955b7c8a9a28aa1351d02e5ef70be2551a565b2
tests workflow #696: SUCCESS
P0 Windows Gate #94: SUCCESS
owner-confirmed local acceptance: COMPLETE
```

本机验收结论来自项目主人现场确认；没有附加原始日志时，不在代码地图中编造精确数值或命令输出。

## 19. 文档索引

```text
docs/MODULES/P2_09A_RUNTIME_TRUTH.md
docs/MODULES/P2_09B_CANONICAL_IDEMPOTENCY.md
docs/MODULES/P2_09C_DESKTOP_DATA_LAYER.md
docs/MODULES/P2_09D_DESKTOP_UX_AUTO_REVIEW.md
docs/MODULES/P2_08A_AUTO_REVIEW_CORE.md
docs/MODULES/P2_08B_LOCAL_AI_REVIEWER.md
docs/MODULES/P2_08B_SHADOW_API.md
docs/TECH_RESEARCH/P2_08_STANDALONE_TO_LINGJI_MAPPING.md
docs/TEST_REPORTS/P2_08_P2_09_INTEGRATION_TEST_REPORT.md
```

## 20. 当前状态

```text
P0 - P2-07:
MERGED_AND_VALIDATED

P2-08 Auto Review SHADOW:
MERGED_AND_VALIDATED

P2-09 Runtime/Desktop Reliability:
MERGED_AND_VALIDATED

Issue #23:
CLOSED_COMPLETED
```
