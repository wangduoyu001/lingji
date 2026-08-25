# Phase 1 Automatic Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Mac-first, owner-authorized automatic second brain that discovers supported AI records, captures immutable evidence, resumes safely after crashes, projects truthful current memory, and exposes one Work Fact chain to RAG, MCP and Desktop.

**Architecture:** Extend the existing `src/extraction`, `src/storage/state_db.py`, `src/retrieval`, `src/gateway/memory_gateway.py`, `src/control/api.py`, `src/work` and `desktop/lingji-control` boundaries. Authorized sources are registered in persistent SQLite, copied through a stat-before/copy/stat-after snapshot into the existing raw archive, parsed by approved adapters, and indexed through the existing lexical/Qdrant pipeline. Obsidian Vault + Git remains formal-knowledge authority; all automatic projections are rebuildable.

**Tech Stack:** Python 3.12; existing SQLite state/extraction queue/FTS5/Qdrant/MemoryGateway; FastAPI authenticated `127.0.0.1:8766`; MCP stdio; React/Tauri Desktop; `watchfiles==1.2.0` in Task 4; pytest and existing Desktop smoke scripts. macOS M5 is validated before Windows parity.

## Global Constraints

- One Chinese owner-authorization onboarding creates an immutable allowlist of source kinds and roots. `authorize`, `revoke`, `scan`, `pause` and `retry` are explicit operations with persistent status and real Work Fact evidence.
- ChatGPT accepts official export ZIP/JSON only; Codex transcripts require schema detection and fail closed; Claude Desktop opaque internal storage is never scraped and reports `unsupported` or `consent_required` without an official export; generic AI History Inbox accepts only owner-selected JSON, JSONL or Markdown files.
- Never read cookies, tokens, credentials, browser profiles, private application databases, opaque application storage or other processes; never inject into processes, write application directories, scan whole disks or upload data over the network.
- Snapshot integrity is stat-before/copy/stat-after. Changed files retry, unchanged source sentinels are recorded, raw payloads are content-addressed, jobs have checkpoint/resume tokens, leases, retries and crash recovery; duplicate scanning must produce zero duplicate raw objects and zero duplicate extraction jobs.
- Task 4 uses `watchfiles==1.2.0`, 5 秒防抖, 15 分钟核对, 每日完整性 verification, persistent scheduler start/stop and recovery. Incremental changes enter the existing queue within 30 秒. Task 0 adds no dependency.
- Obsidian ordinary notes are excluded by default; only `_LingJi/Memory Inbox`, `_LingJi/Memory Library` or `lingji_memory: true` are eligible, and `lingji_memory: false` always wins. Migration may clean only LingJi-managed derived indexes/copies, never real Vault notes.
- All authorized chats enter immutable raw evidence and rebuildable retrieval. Low-risk, high-confidence, conflict-free derived current memory may auto-activate at confidence `>= 0.90`; Core, identity, high-risk and formal permanent knowledge require explicit owner confirmation.
- `superseded`, `invalidated` and `archived` records remain auditable but current retrieval excludes them in lexical DB, Qdrant payload filtering, hybrid post-filter, Core list, ContextPack, MemoryGateway and MCP. Every path supports `current`, explicit `as_of`, explicit `history` and `why` evidence modes.
- Do not add Mem0, OpenMemory, Letta, Zep/Graphiti or LlamaIndex as dependencies, second databases, retrievers, APIs, queues, UIs or telemetry/cloud control planes; borrow only recorded patterns with license/provenance review.
- ContextPack is capped at 12,000 characters and carries source/conversation/message/memory citations. Evaluation gates are `quality_score >= 90%`, `source_accuracy >= 95%`, `false_positive_rate <= 5%`, real Codex MCP success `>= 95%`, duplicate formal content `0`, Production pollution `0`, owner-review chain `100%`, and reboot recovery `100%`.
- macOS M5 release and owner acceptance happen before Windows. Task 10 keeps the real UI open for owner observation; it does not turn reboot or owner checks into pytest/validate claims and does not activate the IDLE local task. The main agent creates a later ACTIVE task only after product code and artifacts are ready.
- Opportunity Center remains frozen until Phase 1 is PASS. Every task has exact files, typed interfaces, a focused test command, expected failure/pass, and an independent commit/review unit.

---

### Task 1: Persistent Source Registry, Chinese Authorization and Scan Control API

**Files:**
- Create: `src/automatic_memory/__init__.py`
- Create: `src/automatic_memory/models.py`
- Create: `src/automatic_memory/source_registry.py`
- Create: `src/control/automatic_memory_api.py`
- Modify: `src/control/api.py`
- Modify: `src/control/service.py`
- Test: `tests/test_automatic_memory_source_registry.py`
- Test: `tests/test_automatic_memory_control_api.py`

**Interfaces:**
- `AuthorizationScope(grant_id: str, source_kinds: tuple[str, ...], roots: tuple[str, ...], granted_at: datetime, expires_at: datetime | None, owner_confirmed: bool)`.
- `SourceRecord(source_id: str, kind: str, root: str, status: str, capability: str, policy_version: str)`.
- `ScanRun(scan_id: str, source_id: str, status: str, cursor: str | None, progress: int, total: int | None, last_error: str | None, recovery_token: str | None)`.
- `SourceRegistry.register(scope: AuthorizationScope, kind: str, root: str) -> SourceRecord`, `revoke(source_id: str) -> SourceRecord`, `start_scan(source_id: str) -> ScanRun`, `pause_scan(scan_id: str) -> ScanRun`, `retry_scan(scan_id: str) -> ScanRun`, and `get_scan(scan_id: str) -> ScanRun`.
- `register_automatic_memory_routes(app: Any, control: LocalControlService, secured: list[Any]) -> None` registers authenticated `POST /api/automatic-memory/authorize`, `POST /revoke`, `POST /scan`, `POST /pause`, `POST /retry`, `GET /sources` and `GET /scans/{scan_id}` on the existing 8766 app.

- [ ] **Step 1: Add registry/API contract tests for one Chinese onboarding authorization, exact-root denial, source persistence, scan cursor/progress/error/recovery and 401/valid-token behavior.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py`; expect FAIL because the registry and route registration are absent.**
- [ ] **Step 3: Implement SQLite-backed registry methods in the existing `StateDatabase` boundary and register routes through `create_control_app`; every response returns real status, never a fabricated completed/zero state.**
- [ ] **Step 4: Run the two focused files; expect PASS and verify `git diff` contains no product-independent database or unprotected 8766 route.**
- [ ] **Step 5: Commit `git add src/automatic_memory src/control/automatic_memory_api.py src/control/api.py src/control/service.py tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py && git commit -m "feat: persist automatic memory source authorization"`.**

### Task 2: Consistent Snapshot, Idempotency, Checkpoint and Resume

**Files:**
- Create: `src/automatic_memory/snapshot.py`
- Create: `src/automatic_memory/checkpoint.py`
- Modify: `src/extraction/idempotency.py`
- Modify: `src/extraction/sink.py`
- Modify: `src/extraction/queue.py`
- Test: `tests/test_automatic_memory_snapshot.py`
- Test: `tests/test_automatic_memory_resume.py`

**Interfaces:**
- `FileStat(size: int, mtime_ns: int, inode: int | None)` records the source sentinel used by a consistent copy.
- `SnapshotResult(source_id: str, relative_path: str, raw_id: str, sha256: str, stat_before: FileStat, stat_after: FileStat, stable: bool, attempt: int)`.
- `ConsistentSnapshot.capture(source_id: str, path: Path, max_attempts: int = 3) -> SnapshotResult` performs stat-before/copy/stat-after and retries when size or mtime changes.
- `ResumeToken(scan_id: str, cursor: str, source_sentinel: str, lease_id: str, attempt: int)` and `CheckpointStore.save(token: ResumeToken) -> None`, `CheckpointStore.load(scan_id: str) -> ResumeToken | None`.
- `SnapshotJobRunner.run(scan_id: str, crash_at: Literal["none", "30%", "70%", "after-lease"]) -> ScanRun` releases leases, resumes from the token and never duplicates a raw object or queue job.

- [ ] **Step 1: Write tests for stable snapshots, changed-file retry, unchanged source sentinel, content-addressed raw identity, leases, retry counts, crash at 30%/70%, resume and zero duplicate scans.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`; expect FAIL because the consistency and checkpoint contracts do not exist.**
- [ ] **Step 3: Implement the stat-before/copy/stat-after protocol over the existing `VaultExtractionSink`, idempotency helpers and `SQLiteExtractionQueue`; persist cursor, error, progress and recovery token in `StateDatabase`.**
- [ ] **Step 4: Run both focused files; expect PASS, including crash recovery and source-sentinel assertions.**
- [ ] **Step 5: Commit `git add src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/idempotency.py src/extraction/sink.py src/extraction/queue.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py && git commit -m "feat: make automatic memory snapshots resumable"`.**

### Task 3: macOS Source Adapters and Generic AI History Inbox

**Files:**
- Modify: `src/extraction/adapters/chatgpt.py`
- Modify: `src/extraction/adapters/codex.py`
- Modify: `src/extraction/registry.py`
- Create: `src/extraction/adapters/generic_ai_history.py`
- Create: `src/extraction/adapters/claude_desktop.py`
- Test: `tests/test_automatic_memory_adapters.py`
- Test fixture: `tests/fixtures/automatic_memory/generic_ai_history.json`
- Test fixture: `tests/fixtures/automatic_memory/generic_ai_history.jsonl`
- Test fixture: `tests/fixtures/automatic_memory/generic_ai_history.md`

**Interfaces:**
- All adapters implement the existing `src.extraction.base.ExtractionAdapter.extract(request: ExtractionRequest) -> ExtractionBatch`.
- `DetectionResult(source_kind: str, schema: str | None, supported: bool, reason: str)`, `SchemaDetection(schema_name: str | None, schema_version: str | None, supported: bool, reason: str)` and `CapabilityStatus(source_kind: str, status: Literal["supported", "unsupported", "consent_required"], detail: str)` are defined in `src/extraction/adapters/generic_ai_history.py` and shared by the adapters.
- `ChatGPTExportAdapter` accepts only official export ZIP/JSON structures and preserves conversation/message IDs.
- `CodexTranscriptAdapter.detect_schema(path: Path) -> SchemaDetection` returns `supported=False` for unknown or malformed schemas and never guesses.
- `GenericAIHistoryAdapter` accepts owner-selected JSON, JSONL and Markdown History Inbox files only, with `detect(path) -> DetectionResult` and deterministic `external_id` values.
- `ClaudeDesktopAdapter.capability(scope: AuthorizationScope) -> CapabilityStatus` returns exactly `supported`, `unsupported` or `consent_required` and never opens opaque application storage.
- `AdapterRegistry.resolve(source_kind: str, path: Path) -> ExtractionAdapter` is the existing registry entry extended to select only approved adapters.

- [ ] **Step 1: Add fixtures and tests for official ChatGPT export parsing, Codex supported/unknown schema fail-closed, Claude unsupported/consent states, and generic JSON/JSONL/Markdown records.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_adapters.py`; expect FAIL before the generic and Claude adapters and schema contract exist.**
- [ ] **Step 3: Extend the existing adapters and registry without private DB, browser-profile, process or network access; route every result through Task 2 snapshots and the existing extraction queue.**
- [ ] **Step 4: Run the focused adapter file; expect PASS with unknown Codex input producing an auditable failure and no parsed messages.**
- [ ] **Step 5: Commit `git add src/extraction/adapters src/extraction/registry.py tests/test_automatic_memory_adapters.py tests/fixtures/automatic_memory && git commit -m "feat: add fail-closed automatic memory adapters"`.**

### Task 4: watchfiles Watcher, Persistent Scheduler and Reconciliation

**Files:**
- Create: `src/automatic_memory/watcher.py`
- Create: `src/automatic_memory/scheduler.py`
- Modify: `src/scheduler/cron.py`
- Modify: `src/config.py`
- Modify: `requirements.txt` (add `watchfiles==1.2.0` only here)
- Test: `tests/test_automatic_memory_scheduler.py`
- Test: `tests/test_automatic_memory_watcher.py`

**Interfaces:**
- Consumes `SourceRecord`, `ScanRun`, `SnapshotJobRunner` and the Task 3 adapter registry.
- `AutomaticMemoryWatcher.start(source_id: str, debounce_seconds: int = 5) -> None`, `.stop() -> None`, `.pause() -> None`, `.resume() -> None`.
- `AutomaticMemoryScheduler.start() -> None`, `.stop() -> None`, `.status() -> tuple[ScanRun, ...]` persists jobs through the existing `CronScheduler`/`StateDatabase` and schedules incremental scans, 900-second reconciliation and daily integrity.
- `ReconciliationReport(discovered: int, queued: int, unchanged: int, errors: tuple[str, ...], complete: bool)`.

- [ ] **Step 1: Write tests for five-second debounce, queue admission within 30 seconds, persistent scheduler start/stop, pause/resume, 15-minute reconciliation, daily integrity, restart recovery and no duplicate callback.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_watcher.py`; expect FAIL before lifecycle wiring exists.**
- [ ] **Step 3: Add the pinned MIT dependency after recording provenance, implement watcher callbacks into Task 2, and register persistent jobs with the existing scheduler rather than creating a second scheduler.**
- [ ] **Step 4: Run both focused files; expect PASS with watcher silence still followed by reconciliation and daily completeness.**
- [ ] **Step 5: Commit `git add src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/config.py requirements.txt tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_watcher.py && git commit -m "feat: schedule automatic memory reconciliation"`.**

### Task 5: Obsidian Isolation, Migration Manifest and Rollback

**Files:**
- Create: `src/obsidian/memory_scope.py`
- Create: `src/obsidian/memory_migration.py`
- Modify: `src/obsidian/discovery.py`
- Modify: `src/obsidian/service.py`
- Test: `tests/test_obsidian_memory_scope.py`
- Test: `tests/test_obsidian_memory_migration.py`

**Interfaces:**
- `ObsidianMemoryDecision(path: Path, eligible: bool, reason: str, explicit_flag: bool)` and `ObsidianMemoryScope.decide(path: Path, frontmatter: Mapping[str, object]) -> ObsidianMemoryDecision`.
- `ManifestEntry(path: str, before_hash: str, managed: bool, action: Literal["retain", "remove-derived", "restore-derived"])` and `MigrationResult(manifest_hash: str, state: Literal["planned", "applied", "rolled_back"], removed_derived: tuple[str, ...])` are defined in `src/obsidian/memory_migration.py`.
- `MigrationManifest(entries: tuple[ManifestEntry, ...], vault_hash: str, generated_at: datetime)` and `ObsidianMemoryMigration.plan(vault_root: Path, dry_run: bool = True) -> MigrationManifest`.
- `ObsidianMemoryMigration.apply(manifest: MigrationManifest, owner_confirmed: bool) -> MigrationResult` cleans only LingJi-managed derived indexes/copies; `.rollback(result: MigrationResult) -> MigrationResult` restores managed derived state only.

- [ ] **Step 1: Test `_LingJi/Memory Inbox`, `_LingJi/Memory Library`, `lingji_memory: true`, `false` precedence, dry-run manifest, migration state, rollback, unchanged ordinary-note hashes and rejection of real Vault delete/move.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py`; expect FAIL before scope/migration contracts exist.**
- [ ] **Step 3: Implement bounded eligibility and managed-derived cleanup through existing `ObsidianService`; require dry-run and owner confirmation, preserve ordinary Vault bytes and never write application directories.**
- [ ] **Step 4: Run both focused files; expect PASS with rollback and hash invariants.**
- [ ] **Step 5: Commit `git add src/obsidian/memory_scope.py src/obsidian/memory_migration.py src/obsidian/discovery.py src/obsidian/service.py tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py && git commit -m "feat: isolate and migrate Obsidian memory scope"`.**

### Task 6: Derived Current-Memory Promotion and Owner Review Boundary

**Files:**
- Create: `src/automatic_memory/derived_memory.py`
- Modify: `src/auto_review/application.py`
- Modify: `src/memory/lifecycle.py`
- Modify: `src/retrieval/memory_db.py`
- Test: `tests/test_automatic_memory_derived_promotion.py`

**Interfaces:**
- `DerivedMemoryCandidate(candidate_id: str, source_ids: tuple[str, ...], title: str, content: str, confidence: float, risk: str, conflict_ids: tuple[str, ...], owner_required: bool)`.
- `PromotionDecision(candidate_id: str, status: Literal["active", "needs_review", "rejected"], reason: str, rebuild_key: str)`.
- `DerivedMemoryPromoter.evaluate(candidate: DerivedMemoryCandidate) -> PromotionDecision` auto-activates only low-risk, confidence `>= 0.90`, conflict-free candidates; Core/identity/high-risk/formal candidates remain owner-gated.

- [ ] **Step 1: Test threshold, conflict, risk, owner approval, rejection, rebuild and `mutation_performed` behavior through existing OFF/SHADOW auto-review paths.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_derived_promotion.py`; expect FAIL before the promoter exists.**
- [ ] **Step 3: Implement a rebuildable projection linked to raw/provenance IDs; do not write Core or formal Obsidian content during automatic activation.**
- [ ] **Step 4: Run the focused file; expect PASS with owner review required for protected classes.**
- [ ] **Step 5: Commit `git add src/automatic_memory/derived_memory.py src/auto_review/application.py src/memory/lifecycle.py src/retrieval/memory_db.py tests/test_automatic_memory_derived_promotion.py && git commit -m "feat: gate derived automatic memory promotion"`.**

### Task 7: Temporal Current Filter Across Every Retrieval Path

**Files:**
- Create: `src/retrieval/temporal_filter.py`
- Modify: `src/retrieval/memory_db.py` (lexical/current Core list)
- Modify: `src/retrieval/qdrant_provider.py` (payload current/as_of filter)
- Modify: `src/retrieval/hybrid.py` (hybrid post-filter and why evidence)
- Modify: `src/retrieval/context_pack.py` (existing ContextPack current/as_of/history/why)
- Modify: `src/gateway/memory_gateway.py` (MemoryGateway mode contract)
- Modify: `src/mcp_server.py` (MCP mode and citation contract)
- Modify: `src/project_memory/context_service.py` (project ContextPack current mode)
- Test: `tests/test_temporal_current_filter.py`
- Test: `tests/test_temporal_retrieval_paths.py`

**Interfaces:**
- `TemporalFact(memory_id: str, valid_from: datetime | None, valid_to: datetime | None, lifecycle: Literal["active", "superseded", "invalidated", "archived"], replacement_id: str | None)`.
- `TemporalQuery(mode: Literal["current", "as_of", "history", "why"], as_of: datetime | None = None)`, `CurrentMemoryFilter.matches(fact: TemporalFact, query: TemporalQuery) -> bool` and `CurrentMemoryFilter.explain(fact, query) -> dict[str, object]`.
- `MemoryDatabase.search(..., temporal: TemporalQuery)`, Qdrant payload filter receives the same `TemporalQuery`, `HybridRetriever` applies the same post-filter, and Core list/ContextPack/MemoryGateway/MCP expose the same mode and `why` evidence.

- [ ] **Step 1: Write tests proving current excludes superseded/invalidated/archived in lexical SQL, Qdrant payload, hybrid post-filter, Core list, existing `src/retrieval/context_pack.py`, `MemoryGateway` and MCP; explicit `as_of`, `history` and `why` retain replacement evidence.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_temporal_current_filter.py tests/test_temporal_retrieval_paths.py`; expect FAIL before all-path wiring exists.**
- [ ] **Step 3: Implement one shared predicate and pass it through each existing path; never derive temporal truth independently in UI or an adapter.**
- [ ] **Step 4: Run both focused files plus `tests/test_memory_retrieval.py` and `tests/test_permanent_memory_gateway.py`; expect PASS with lexical degradation still available.**
- [ ] **Step 5: Commit `git add src/retrieval/temporal_filter.py src/retrieval/memory_db.py src/retrieval/qdrant_provider.py src/retrieval/hybrid.py src/retrieval/context_pack.py src/gateway/memory_gateway.py src/mcp_server.py src/project_memory/context_service.py tests/test_temporal_current_filter.py tests/test_temporal_retrieval_paths.py && git commit -m "feat: enforce temporal current retrieval"`.**

### Task 8: Automatic-Memory Onboarding, Work Fact, Python/TypeScript DTO and 8766 Desktop Contract

**Files:**
- Modify: `src/control/automatic_memory_api.py`
- Modify: `src/control/service.py`
- Modify: `src/control/work_routes.py`
- Modify: `src/work/models.py`
- Modify: `src/work/store.py`
- Modify: `src/work/projector.py`
- Modify: `desktop/lingji-control/src/contracts/workFact.ts`
- Modify: `desktop/lingji-control/src/pages/OverviewPage.tsx`
- Modify: `desktop/lingji-control/src/pages/ActivityPage.tsx`
- Modify: `desktop/lingji-control/src/pages/AttentionPage.tsx`
- Test: `tests/test_automatic_memory_work_fact.py`
- Test: `tests/test_automatic_memory_8766_contract.py`
- Test: `desktop/lingji-control/scripts/automatic-memory-smoke.mjs`
- Modify: `desktop/lingji-control/package.json` (register `test:automatic-memory`)

**Interfaces:**
- `AutomaticMemoryWorkFact(work_id: str, source_id: str, scan_id: str, stage: str, outcome: str, next_actor: Literal["system", "owner", "unsupported"], pending_action_id: str | None, evidence_ids: tuple[str, ...])` is the Python/TypeScript DTO shared by WorkStore, projector and Desktop.
- `LocalControlService.automatic_memory_authorize/revoke/scan/pause/retry` delegate to Task 1 registry and create/update the same Work Fact ID; `create_control_app` serves them only behind the existing 8766 token dependency.
- The onboarding sequence is one Chinese authorization followed by real `authorize -> discover -> scan -> pause/retry -> outcome` events; no endpoint may return success without a persisted Work Fact and evidence IDs.

- [ ] **Step 1: Write API and Desktop smoke tests for first-run onboarding, authorize/revoke/scan/pause/retry, token rejection, Python/TS DTO parity, same IDs across Overview/Activity/Attention and truthful empty/error/unsupported states.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_8766_contract.py`; expect FAIL because formal routes and shared DTO wiring remain incomplete.**
- [ ] **Step 3: Extend Task 1 routes and the existing WorkStore/projector; register `test:automatic-memory` in the real `desktop/lingji-control/package.json` and make the smoke script exercise 8766, not mocked page state.**
- [ ] **Step 4: Run Python focused tests and `cd desktop/lingji-control && npm run test:automatic-memory`; expect PASS with no direct SQLite/Qdrant access from Desktop.**
- [ ] **Step 5: Commit `git add src/control/automatic_memory_api.py src/control/service.py src/control/work_routes.py src/work/models.py src/work/store.py src/work/projector.py desktop/lingji-control/src/contracts/workFact.ts desktop/lingji-control/src/pages/OverviewPage.tsx desktop/lingji-control/src/pages/ActivityPage.tsx desktop/lingji-control/src/pages/AttentionPage.tsx desktop/lingji-control/scripts/automatic-memory-smoke.mjs desktop/lingji-control/package.json tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_8766_contract.py && git commit -m "feat: expose automatic memory work facts"`.**

### Task 9: Unified RAG, ContextPack and Quality Evaluation (two review units)

#### Task 9A: RAG and Existing ContextPack

**Files:**
- Modify: `src/retrieval/context_pack.py` (extend the existing builder; do not create `src/automatic_memory/context_pack.py`)
- Modify: `src/gateway/memory_gateway.py`
- Modify: `src/mcp_server.py`
- Test: `tests/test_automatic_memory_context_pack.py`
- Test: `tests/test_automatic_memory_mcp.py`

**Interfaces:**
- Extend existing `ContextPackRequest` with `temporal: TemporalQuery = TemporalQuery(mode="current")`, preserving `max_chars: int = 12000`.
- Existing `ContextPackBuilder.build(request: ContextPackRequest) -> dict[str, Any]` returns bounded sections with source/conversation/message/memory citations and temporal `why` evidence.
- Existing `MemoryGateway.build_context_pack(...)` and MCP `build_context_pack` pass the same temporal query and authorization scope; no parallel gateway or ContextPack implementation is introduced.

- [ ] **Step 1: Test 12,000-character truncation, raw/source/conversation/message citations, current/as_of/history/why, privacy/project/Agent Scope and MCP parity.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_context_pack.py tests/test_automatic_memory_mcp.py`; expect FAIL until temporal and provenance fields are threaded through the existing builder.**
- [ ] **Step 3: Extend `src/retrieval/context_pack.py`, `src/gateway/memory_gateway.py` and `src/mcp_server.py` only; use the existing HybridRetriever/MemoryGateway and keep lexical fallback truthful.**
- [ ] **Step 4: Run the focused files plus `tests/test_permanent_memory_gateway.py`; expect PASS.**
- [ ] **Step 5: Commit `git add src/retrieval/context_pack.py src/gateway/memory_gateway.py src/mcp_server.py tests/test_automatic_memory_context_pack.py tests/test_automatic_memory_mcp.py && git commit -m "feat: cite automatic memory context packs"`.**

#### Task 9B: 100 问质量评测 and Acceptance Gate

**Files:**
- Create: `src/automatic_memory/evaluation.py`
- Create: `tests/evaluation/test_automatic_memory_quality.py`
- Create: `tests/evaluation/fixtures/automatic_memory_quality.jsonl`
- Test: `tests/test_automatic_memory_acceptance_gate.py`

**Interfaces:**
- `EvaluationReport(quality_score: float, source_accuracy: float, false_positive_rate: float, mcp_success_rate: float, duplicate_formal_content: int, production_pollution: int, owner_review_success: float, reboot_recovery: float, answered_questions: int)`.
- `AutomaticMemoryAcceptanceGate.evaluate(report: EvaluationReport) -> Literal["PASS", "FAIL", "BLOCKED"]` enforces all global thresholds and requires `answered_questions == 100` for the quality suite.

- [ ] **Step 1: Write a 100 问评测 fixture covering exact facts, cross-document comparison, source verification and negative boundaries; test every threshold and failure state.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py`; expect FAIL before evaluator/gate files exist.**
- [ ] **Step 3: Implement scoring and gate logic in `src/automatic_memory/evaluation.py`; keep RAG mechanics in 9A and never report an unexecuted real-client call as success.**
- [ ] **Step 4: Run the evaluation focused tests; expect PASS for synthetic fixtures and explicit BLOCKED for missing owner/Mac evidence.**
- [ ] **Step 5: Commit `git add src/automatic_memory/evaluation.py tests/evaluation tests/test_automatic_memory_acceptance_gate.py && git commit -m "test: evaluate automatic memory quality"`.**

### Task 10: macOS M5 Release and Owner Acceptance Preparation/Execution

**Files:**
- Create: `src/automatic_memory/mac_acceptance.py`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`
- Modify: `scripts/validate.ps1` (Mac release/focused entry only; no reboot claim)
- Test: `desktop/lingji-control/scripts/macos-release-smoke.mjs`
- Test: `tests/test_automatic_memory_macos_gate.py`

**Interfaces:**
- `MacAcceptanceIdentity(product_commit: str, artifact_name: str, artifact_id: str, zip_sha256: str, installer_sha256: str)`.
- `MacAcceptanceGate.evaluate(identity: MacAcceptanceIdentity, evaluation: EvaluationReport, owner_observation: Literal["PASS", "FAIL", "NOT_TESTED"]) -> Literal["PASS", "FAIL", "BLOCKED"]`.

- [ ] **Step 1: Add tests for exact product/artifact identity, owner-only observations, Production/Acceptance isolation, no black window, and no false reboot automation claim.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_macos_gate.py`; expect FAIL before the gate contract exists.**
- [ ] **Step 3: Prepare and run macOS M5 focused/full/release and same-SHA artifact smoke; perform real UI traversal, three Core restart rounds and owner observation with the UI left open. Do not edit `LOCAL_EXECUTION_TASK.md`, do not create an ACTIVE task and do not claim reboot/owner checks are pytest/validate results.**
- [ ] **Step 4: Record PASS/FAIL/BLOCKED evidence and cleanup requirements in the acceptance authority; wait for owner confirmation before closing the UI or declaring Phase 1 PASS.**
- [ ] **Step 5: Commit acceptance-gate/document changes with `git add src/automatic_memory/mac_acceptance.py docs/ACCEPTANCE scripts/validate.ps1 desktop/lingji-control/scripts/macos-release-smoke.mjs tests/test_automatic_memory_macos_gate.py && git commit -m "test: gate automatic memory on macos"`.**

### Task 11: Independent Windows Parity After macOS PASS

**Files:**
- Create: `src/automatic_memory/windows_parity.py`
- Create: `tests/test_automatic_memory_windows_parity.py`
- Test: `desktop/lingji-control/scripts/windows-release-smoke.mjs`
- Modify: `scripts/validate.ps1`
- Modify: `scripts/build_windows_sidecar.ps1`
- Modify: `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`

**Interfaces:**
- `WindowsParityReport(api_semantics_equal: bool, dto_semantics_equal: bool, power_shell_51_compatible: bool, data_root_outside_c: bool, artifact_sha256: str, mac_gate_commit: str)`.
- `WindowsParityGate.evaluate(report: WindowsParityReport, mac_result: Literal["PASS", "FAIL", "BLOCKED"]) -> Literal["PASS", "FAIL", "BLOCKED"]` refuses to run parity acceptance unless macOS result is `PASS`.

- [ ] **Step 1: Write PowerShell 5.1 syntax and behavior tests for the same 8766 API/DTO semantics, non-C-drive runtime paths, exact-instance lifecycle and no silent writes.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_windows_parity.py`; expect FAIL before the parity gate exists.**
- [ ] **Step 3: Run Windows focused/full/release and same-SHA artifact checks only after Task 10 records macOS PASS; use `windows-release-smoke.mjs` and do not alter owner data or create a second source of truth.**
- [ ] **Step 4: Verify PowerShell 5.1, same API/data semantics, Production/Acceptance isolation, non-C-drive paths and artifact hash; report BLOCKED if macOS evidence or owner confirmation is absent.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/windows_parity.py tests/test_automatic_memory_windows_parity.py desktop/lingji-control/scripts/windows-release-smoke.mjs scripts/validate.ps1 scripts/build_windows_sidecar.ps1 docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md && git commit -m "test: verify automatic memory windows parity"`.**

## Self-Review Checklist

- [ ] **Spec coverage:** Tasks 1–2 cover registry, authorization, scan status, consistent snapshots, idempotency, checkpoint, lease, retry and crash resume; Task 3 covers ChatGPT/Codex/Claude/generic JSON/JSONL/Markdown; Task 4 covers watcher/scheduler lifecycle and reconciliation; Task 5 covers Obsidian isolation/migration/rollback; Task 6 covers derived promotion; Task 7 covers every temporal retrieval path; Task 8 covers onboarding, Work Fact, DTOs, 8766 and Desktop; Task 9 separates RAG from 100-question evaluation; Task 10 is Mac M5 release/owner acceptance; Task 11 is Windows parity.
- [ ] **Placeholder scan:** Search this plan for forbidden placeholder markers and vague future-work wording; none may remain.
- [ ] **Forward-dependency scan:** Task 1 defines source/scan contracts before Task 2; Task 2 defines snapshot/checkpoint before Task 3 adapters and Task 4 watcher; Task 3 defines adapter registry before Task 4; Task 7 defines temporal query before Task 9; Task 8 defines Work Fact before Desktop smoke; Task 9 defines EvaluationReport before Tasks 10–11.
- [ ] **Path scan:** Existing `src/gateway/memory_gateway.py`, `src/retrieval/context_pack.py`, `src/control/api.py`, `src/scheduler/cron.py`, `src/extraction/*`, `src/obsidian/*`, `src/work/*` are used; no `src/gateway/memory.py` or parallel `src/automatic_memory/context_pack.py` is introduced.
- [ ] **Contract scan:** Every task has exact Files, typed Interfaces, failing and passing commands and a commit command; `desktop/lingji-control/package.json` registers `test:automatic-memory`; Task 10 does not activate the IDLE local task.
