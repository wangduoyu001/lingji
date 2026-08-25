# Phase 1 Automatic Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an owner-authorized, local-first automatic second brain that discovers supported AI records, preserves raw evidence and provenance, maintains rebuildable current-memory projections, and exposes truthful Desktop/RAG/MCP results.

**Architecture:** Keep `src/` as the only product mainline and extend its existing Capture, Extraction, Work Fact, SQLite, lexical, Qdrant, MemoryGateway, ContextPack and MCP boundaries. Authorized roots produce immutable raw snapshots and append-only provenance events; parsers and temporal projections are rebuildable, while Obsidian Vault + Git remains the authority for formal permanent knowledge. The Desktop reads one shared Work/Memory fact chain through authenticated `127.0.0.1:8766`.

**Tech Stack:** Python 3.12; existing SQLite state, raw archive, FTS5/BM25 and Qdrant retrieval; FastAPI Local Control API; MCP stdio; React/Tauri Desktop; `watchfiles==1.2.0` in Task 4 only; pytest focused tests; macOS M5 before Windows release validation.

## Global Constraints

- One Chinese owner authorization grants only explicit allowlisted source roots and source kinds; supported AI records are discovered and continuously ingested only inside that scope.
- ChatGPT accepts official export archives only; Codex transcripts require schema detection and fail closed; Claude Desktop opaque internal storage is never scraped and must report `unsupported` or `consent_required` when no official export is available.
- Never read cookies, tokens, credentials, browser profiles, private application databases, opaque application storage or other processes; never inject into processes, write application directories, scan whole disks or upload data over the network.
- Obsidian ordinary notes are excluded by default; only `_LingJi/Memory Inbox`, `_LingJi/Memory Library` or frontmatter `lingji_memory: true` are eligible, and `lingji_memory: false` always wins.
- Every authorized chat enters immutable raw evidence and rebuildable retrieval; low-risk, high-confidence, conflict-free derived current memory may auto-activate as a rebuildable projection, while Core, identity, high-risk and formal permanent knowledge require explicit owner confirmation.
- Current retrieval is the default. `superseded`, `invalidated` and `archived` records remain auditable but are excluded from lexical, Qdrant, hybrid, Core, ContextPack and MCP current-mode results.
- Task 4 uses `watchfiles==1.2.0` as the preferred watcher: 5 秒防抖、15 分钟核对、每日完整性验证；watcher silence is never authoritative. Task 0 adds no dependency.
- Do not add Mem0, OpenMemory, Letta, Zep/Graphiti or LlamaIndex as dependencies, second databases, retrievers, APIs, queues or UIs; only reuse documented patterns.
- Incremental changes enter the extraction queue within 30 秒; ContextPack is capped at 12,000 characters; automatic derived-memory activation requires confidence `>= 0.90` and no conflict.
- Evaluation gates are `quality_score >= 90%`, `source_accuracy >= 95%`, `false_positive_rate <= 5%`, real Codex MCP success `>= 95%`, duplicate formal content `0`, Production pollution `0`, owner-review chain success `100%`, and post-reboot recovery `100%`.
- macOS M5 is the first real-machine target. Windows work starts only after macOS evidence is complete. Opportunity Center remains frozen until Phase 1 is PASS.
- Each task has its own focused tests and commit. No task may claim a future interface is already implemented; each implementation must update the relevant acceptance entry before product validation.

---

### Task 1: Authorization Scope and Privacy Policy

**Files:**
- Create: `src/automatic_memory/__init__.py`
- Create: `src/automatic_memory/models.py`
- Create: `src/automatic_memory/policy.py`
- Test: `tests/test_automatic_memory_policy.py`

**Interfaces:**
- Produces `AuthorizationScope(grant_id: str, source_kinds: tuple[str, ...], roots: tuple[str, ...], granted_at: datetime, expires_at: datetime | None, owner_confirmed: bool)`.
- Produces `PolicyDecision(allowed: bool, reason: str, requires_owner_confirmation: bool)`.
- Produces `AuthorizationPolicy.evaluate(scope: AuthorizationScope, candidate_root: str, source_kind: str) -> PolicyDecision`.

- [ ] **Step 1: Write policy tests for one-time Chinese authorization, exact roots, expiry and forbidden source access.**

```python
def test_authorized_root_is_allowed_but_sibling_root_is_denied():
    scope = AuthorizationScope("g-1", ("chatgpt_export",), ("/vault/authorized",), now, None, True)
    assert AuthorizationPolicy().evaluate(scope, "/vault/authorized/export.zip", "chatgpt_export").allowed
    assert not AuthorizationPolicy().evaluate(scope, "/vault/private/export.zip", "chatgpt_export").allowed
```

- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_policy.py`; expect FAIL because the policy module is absent.**
- [ ] **Step 3: Implement immutable scope validation with normalized allowlist roots, owner-confirmation checks, expiry checks and explicit denial reasons; reject cookie, token, credential, browser-profile, private-database, process and network-upload source kinds.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_policy.py`; expect all policy tests PASS.**
- [ ] **Step 5: Commit with `git add src/automatic_memory tests/test_automatic_memory_policy.py && git commit -m "feat: add automatic memory authorization policy"`.**

### Task 2: Authorized Source Discovery and Capability Matrix

**Files:**
- Create: `src/automatic_memory/discovery.py`
- Create: `src/automatic_memory/source_catalog.py`
- Test: `tests/test_automatic_memory_discovery.py`

**Interfaces:**
- Consumes `AuthorizationScope` and `PolicyDecision` from Task 1.
- Produces `SourceDescriptor(source_id: str, source_kind: str, root: str, capability: str, status: str, reason: str)`.
- Produces `SourceDiscovery.discover(scope: AuthorizationScope) -> tuple[SourceDescriptor, ...]`.

- [ ] **Step 1: Write discovery tests proving only allowlisted roots are enumerated, no full-disk traversal occurs, and unsupported Claude storage is reported without opening it.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_discovery.py`; expect FAIL on missing discovery implementation.**
- [ ] **Step 3: Implement bounded root enumeration using Task 1 policy decisions; return `supported`, `unsupported` or `consent_required` descriptors and never inspect opaque application directories.**
- [ ] **Step 4: Run the focused discovery test; expect PASS and assert all observed paths are descendants of authorized roots.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/discovery.py src/automatic_memory/source_catalog.py tests/test_automatic_memory_discovery.py && git commit -m "feat: discover authorized memory sources"`.**

### Task 3: Official ChatGPT Export Adapter

**Files:**
- Create: `src/automatic_memory/adapters/__init__.py`
- Create: `src/automatic_memory/adapters/chatgpt_export.py`
- Create: `src/automatic_memory/records.py`
- Test: `tests/test_chatgpt_export_adapter.py`
- Test fixture: `tests/fixtures/automatic_memory/chatgpt_official_export.zip`

**Interfaces:**
- Produces `DetectionResult(source_kind: str, schema: str, supported: bool, reason: str)`.
- Produces `ConversationRecord(conversation_id: str, title: str, messages: tuple[MessageRecord, ...], source_id: str)` and `MessageRecord(message_id: str, role: str, text: str, created_at: datetime | None)`.
- Produces `ChatGPTExportAdapter.detect(path: Path) -> DetectionResult` and `ChatGPTExportAdapter.parse(path: Path) -> tuple[ConversationRecord, ...]`.

- [ ] **Step 1: Add a minimal official-export fixture and tests for conversation/message identity, UTF-8 text, malformed ZIP rejection and duplicate message handling.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_chatgpt_export_adapter.py`; expect FAIL before the adapter exists.**
- [ ] **Step 3: Implement ZIP-only detection, schema validation, deterministic IDs and bounded extraction; reject browser exports and unknown structures without reading their content.**
- [ ] **Step 4: Run the adapter tests; expect PASS with no network calls and no writes outside the test workspace.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/adapters src/automatic_memory/records.py tests/test_chatgpt_export_adapter.py tests/fixtures/automatic_memory/chatgpt_official_export.zip && git commit -m "feat: ingest official ChatGPT exports"`.**

### Task 4: File Watcher, Debounce and Reconciliation

**Files:**
- Create: `src/automatic_memory/watcher.py`
- Create: `src/automatic_memory/reconciliation.py`
- Modify: `requirements.txt` (add `watchfiles==1.2.0` only in this task)
- Test: `tests/test_automatic_memory_watcher.py`
- Test: `tests/test_automatic_memory_reconciliation.py`

**Interfaces:**
- Consumes `AuthorizationScope` and `SourceDescriptor` from Tasks 1 and 2.
- Requires the queue bridge contract `RawArchive.put(payload: bytes, source_id: str) -> RawObject` and `QueueBridge.enqueue(raw: RawObject, provenance: ProvenanceEvent) -> str`; Task 7 owns their implementation.
- Produces `IncrementalWatcher.run(scope: AuthorizationScope, debounce_seconds: int = 5) -> Iterator[Path]`.
- Produces `Reconciler.reconcile(scope: AuthorizationScope, interval_seconds: int = 900) -> ReconciliationReport`.
- Produces `ReconciliationReport(discovered: int, queued: int, unchanged: int, errors: tuple[str, ...], complete: bool)`.

- [ ] **Step 1: Write deterministic tests for five-second debounce, 30-second queue admission, fifteen-minute reconciliation and daily completeness checks.**
- [ ] **Step 2: Run both watcher tests; expect FAIL before the watcher and manifest implementation exists.**
- [ ] **Step 3: Add the pinned `watchfiles==1.2.0` dependency after recording its MIT license and provenance; implement event filtering, debounce, manifest hashing and idempotent queue admission.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_reconciliation.py`; expect PASS and verify watcher silence cannot suppress reconciliation.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/watcher.py src/automatic_memory/reconciliation.py requirements.txt tests/test_automatic_memory_watcher.py tests/test_automatic_memory_reconciliation.py && git commit -m "feat: watch authorized sources with reconciliation"`.**

### Task 5: Schema-Detected Codex Transcript Adapter

**Files:**
- Create: `src/automatic_memory/adapters/codex_transcript.py`
- Create: `src/automatic_memory/adapters/schema_detection.py`
- Test: `tests/test_codex_transcript_adapter.py`
- Test fixture: `tests/fixtures/automatic_memory/codex_supported_transcript.jsonl`
- Test fixture: `tests/fixtures/automatic_memory/codex_unknown_transcript.jsonl`

**Interfaces:**
- Produces `SchemaDetection(schema_name: str | None, schema_version: str | None, supported: bool, reason: str)`.
- Produces `CodexTranscriptAdapter.detect(path: Path) -> SchemaDetection` and `CodexTranscriptAdapter.parse(path: Path) -> tuple[ConversationRecord, ...]`.

- [ ] **Step 1: Write tests for the supported transcript schema, unknown schema fail-closed behavior, malformed records and stable session/message IDs.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_codex_transcript_adapter.py`; expect FAIL before schema detection exists.**
- [ ] **Step 3: Implement explicit schema fingerprints, version checks and fail-closed parsing; preserve raw lines as evidence and never inspect unrelated application databases.**
- [ ] **Step 4: Run the adapter tests; expect PASS with unknown fixtures producing `supported=False` and no parsed messages.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/adapters/codex_transcript.py src/automatic_memory/adapters/schema_detection.py tests/test_codex_transcript_adapter.py tests/fixtures/automatic_memory/codex_* && git commit -m "feat: fail closed on unsupported Codex transcripts"`.**

### Task 6: Claude Desktop Unsupported and Consent Boundary

**Files:**
- Create: `src/automatic_memory/adapters/claude_desktop.py`
- Create: `src/automatic_memory/adapters/capabilities.py`
- Test: `tests/test_claude_desktop_boundary.py`

**Interfaces:**
- Produces `CapabilityStatus(source_kind: str, status: str, detail: str)` where status is exactly `supported`, `unsupported` or `consent_required`.
- Produces `ClaudeDesktopAdapter.inspect(scope: AuthorizationScope) -> CapabilityStatus`.
- Produces `ConnectorBoundary.assert_no_opaque_storage_access(path: Path) -> None`.

- [ ] **Step 1: Write tests proving no Claude private database, browser profile or process is opened; official export availability maps to `supported`, otherwise `unsupported` or `consent_required`.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_claude_desktop_boundary.py`; expect FAIL before the boundary adapter exists.**
- [ ] **Step 3: Implement capability inspection from explicit owner-provided export paths only; return a truthful unsupported/consent state for opaque storage.**
- [ ] **Step 4: Run the boundary tests; expect PASS and inspect the test audit log for zero opaque-path reads.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/adapters/claude_desktop.py src/automatic_memory/adapters/capabilities.py tests/test_claude_desktop_boundary.py && git commit -m "feat: enforce Claude desktop consent boundary"`.**

### Task 7: Raw Evidence Archive, Provenance Ledger and Queue Bridge

**Files:**
- Create: `src/automatic_memory/raw_archive.py`
- Create: `src/automatic_memory/provenance.py`
- Create: `src/automatic_memory/queue_bridge.py`
- Test: `tests/test_automatic_memory_provenance.py`
- Test: `tests/test_automatic_memory_queue_bridge.py`

**Interfaces:**
- Produces `RawObject(raw_id: str, sha256: str, path: Path, source_id: str, captured_at: datetime)` from `RawArchive.put(payload: bytes, source_id: str) -> RawObject`.
- Produces `ProvenanceEvent(event_id: str, prev_event_hash: str | None, event_hash: str, raw_id: str, parser: str, parser_version: str, policy_version: str, source_schema: str)` from `ProvenanceLedger.append(event_without_hash: dict[str, object]) -> ProvenanceEvent`.
- Produces `QueueBridge.enqueue(raw: RawObject, provenance: ProvenanceEvent) -> str` with a deterministic idempotency key.

- [ ] **Step 1: Write tests for content-addressed raw storage, append-only hash chaining, parser/config provenance, idempotency and retry/error records.**
- [ ] **Step 2: Run both focused files; expect FAIL before archive, ledger and queue bridge exist.**
- [ ] **Step 3: Implement immutable raw writes under configured `storage/raw`, append-only events in `lingji_state.db`, and bridge records into the existing extraction queue; reject duplicate payloads without duplicate work.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_provenance.py tests/test_automatic_memory_queue_bridge.py`; expect PASS and verify no production/Vault writes.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/raw_archive.py src/automatic_memory/provenance.py src/automatic_memory/queue_bridge.py tests/test_automatic_memory_provenance.py tests/test_automatic_memory_queue_bridge.py && git commit -m "feat: archive automatic memory evidence with provenance"`.**

### Task 8: Obsidian Memory Scope and Formal-Knowledge Boundary

**Files:**
- Create: `src/obsidian/memory_scope.py`
- Modify: `src/obsidian/discovery.py`
- Test: `tests/test_obsidian_memory_scope.py`
- Test fixture: `tests/fixtures/automatic_memory/obsidian_scope/`

**Interfaces:**
- Produces `ObsidianMemoryDecision(path: Path, eligible: bool, reason: str, explicit_flag: bool)`.
- Produces `ObsidianMemoryScope.decide(path: Path, frontmatter: Mapping[str, object]) -> ObsidianMemoryDecision`.
- Produces `ObsidianMemoryScope.iter_allowed(vault_root: Path) -> Iterator[Path]`.

- [ ] **Step 1: Write tests for `_LingJi/Memory Inbox`, `_LingJi/Memory Library`, `lingji_memory: true`, default exclusion and `lingji_memory: false` precedence.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_obsidian_memory_scope.py`; expect FAIL before the scope implementation exists.**
- [ ] **Step 3: Implement bounded path matching and frontmatter precedence; keep ordinary/formal notes readable by Obsidian but excluded from automatic memory ingestion unless explicitly opted in.**
- [ ] **Step 4: Run the focused test; expect PASS and assert no write, move, delete or silent distillation into Core Memory.**
- [ ] **Step 5: Commit with `git add src/obsidian/memory_scope.py src/obsidian/discovery.py tests/test_obsidian_memory_scope.py tests/fixtures/automatic_memory/obsidian_scope && git commit -m "feat: gate Obsidian automatic memory scope"`.**

### Task 9: Temporal Validity and Derived Current-Memory Projection

**Files:**
- Create: `src/automatic_memory/temporal.py`
- Create: `src/automatic_memory/current_projection.py`
- Modify: `src/retrieval/hybrid.py`
- Test: `tests/test_automatic_memory_temporal.py`
- Test: `tests/test_current_memory_projection.py`

**Interfaces:**
- Produces `TemporalFact(memory_id: str, valid_from: datetime, valid_to: datetime | None, invalidated_at: datetime | None, replacement_id: str | None, lifecycle: str)`.
- Produces `ProjectionDecision(activated: bool, reason: str, candidate_id: str)` and `CurrentMemoryProjection.activate(candidate_id: str, confidence: float, conflict_ids: tuple[str, ...]) -> ProjectionDecision`.
- Produces `CurrentMemoryFilter.is_current(fact: TemporalFact, at: datetime) -> bool` and applies the same predicate to lexical, Qdrant, hybrid, Core, ContextPack and MCP reads.

- [ ] **Step 1: Write tests for valid facts, supersession, invalidation, archival retention, conflict rejection and the `confidence >= 0.90` threshold.**
- [ ] **Step 2: Run both focused files; expect FAIL before temporal fields and the shared current filter exist.**
- [ ] **Step 3: Implement validity windows and replacement links in rebuildable projections; preserve raw evidence and owner-review records, and keep Core/identity/high-risk/formal knowledge owner-gated.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_temporal.py tests/test_current_memory_projection.py tests/test_memory_retrieval.py`; expect PASS with historical records excluded from current mode.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/temporal.py src/automatic_memory/current_projection.py src/retrieval/hybrid.py tests/test_automatic_memory_temporal.py tests/test_current_memory_projection.py && git commit -m "feat: add temporal current memory projection"`.**

### Task 10: Unified RAG, ContextPack, MCP and Desktop Observability

**Files:**
- Create: `src/automatic_memory/context_pack.py`
- Modify: `src/gateway/memory.py`
- Modify: `src/mcp_server.py`
- Modify: `src/work/projector.py`
- Modify: `desktop/lingji-control/src/contracts/workFact.ts`
- Modify: `desktop/lingji-control/src/pages/OverviewPage.tsx`
- Modify: `desktop/lingji-control/src/pages/ActivityPage.tsx`
- Modify: `desktop/lingji-control/src/pages/AttentionPage.tsx`
- Test: `tests/test_automatic_memory_context_pack.py`
- Test: `tests/test_automatic_memory_work_projection.py`
- Test: `desktop/lingji-control/scripts/automatic-memory-smoke.mjs`

**Interfaces:**
- Consumes `ConversationRecord`, `RawObject`, `ProvenanceEvent`, `TemporalFact`, `CurrentMemoryFilter` and existing `MemoryGateway`/`WorkProjector` contracts.
- Produces `ContextPack(text: str, citations: tuple[dict[str, str], ...], truncated: bool)` and `ContextPackBuilder.build(query: str, scope: AuthorizationScope, max_chars: int = 12000) -> ContextPack` with citations for raw, conversation, message, memory and work IDs.
- Produces `AutomaticMemoryWorkView(work_id: str, stage: str, outcome: str, next_actor: str, pending_action_id: str | None, evidence_ids: tuple[str, ...])` through the existing authenticated 8766 read path.

- [ ] **Step 1: Write tests that one imported chat appears as raw evidence, searchable content, cited ContextPack content and one truthful Work Fact across Home/Work/Attention/Memory; assert current-mode filtering and 12,000-character cap.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_context_pack.py tests/test_automatic_memory_work_projection.py`; expect FAIL until the shared projection is wired.**
- [ ] **Step 3: Implement ContextPack citation assembly through `MemoryGateway`, MCP access through the same gateway, and Desktop projections through the existing WorkStore/projector; no page may synthesize work or pending state locally.**
- [ ] **Step 4: Run Python focused tests and `cd desktop/lingji-control && npm run test:automatic-memory-smoke`; expect PASS with unavailable/degraded states truthful and no direct SQLite/Qdrant/Desktop bypass.**
- [ ] **Step 5: Commit with `git add src/automatic_memory/context_pack.py src/gateway/memory.py src/mcp_server.py src/work/projector.py desktop/lingji-control/src/contracts/workFact.ts desktop/lingji-control/src/pages/OverviewPage.tsx desktop/lingji-control/src/pages/ActivityPage.tsx desktop/lingji-control/src/pages/AttentionPage.tsx tests/test_automatic_memory_context_pack.py tests/test_automatic_memory_work_projection.py desktop/lingji-control/scripts/automatic-memory-smoke.mjs && git commit -m "feat: expose automatic memory evidence across RAG and desktop"`.**

### Task 11: Evaluation, Mac-First Acceptance and Release Gate

**Files:**
- Create: `tests/evaluation/test_automatic_memory_quality.py`
- Create: `tests/evaluation/fixtures/automatic_memory_quality.jsonl`
- Modify: `scripts/validate.ps1`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`
- Test: `tests/test_automatic_memory_acceptance_contract.py`

**Interfaces:**
- Produces `EvaluationReport(quality_score: float, source_accuracy: float, false_positive_rate: float, mcp_success_rate: float, duplicate_formal_content: int, production_pollution: int, owner_review_success: float, reboot_recovery: float)`.
- Produces `AutomaticMemoryAcceptanceGate.evaluate(report: EvaluationReport) -> Literal["PASS", "FAIL", "BLOCKED"]` using the global thresholds in this plan.

- [ ] **Step 1: Write deterministic evaluation tests for all thresholds, unsupported-client outcomes, production/acceptance isolation, owner approval and reboot recovery.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_contract.py`; expect FAIL before the evaluation gate exists.**
- [ ] **Step 3: Implement fixture scoring and the acceptance gate; add focused/full/release sequencing, three Core restart rounds, one macOS M5 reboot and owner-only UI observations without activating the IDLE local task.**
- [ ] **Step 4: Run `./scripts/validate.ps1 -Mode focused -Area automatic-memory` on macOS M5, then run `./scripts/validate.ps1 -Mode full` once on the final tree; expect all automatic thresholds PASS or an explicit BLOCKED/FAIL report.**
- [ ] **Step 5: Create the same-SHA macOS artifact first, complete owner confirmation and cleanup, then begin Windows validation; only after Phase 1 PASS may Opportunity Center leave frozen status. Commit with `git add tests/evaluation scripts/validate.ps1 docs/ACCEPTANCE && git commit -m "test: gate automatic memory phase 1"`.**

## Self-Review Checklist

- [ ] **Spec coverage:** Tasks 1-2 cover one-time authorization, discovery and non-interference; Tasks 3, 5 and 6 cover ChatGPT, Codex and Claude boundaries; Task 4 covers watchfiles, debounce, reconciliation and completeness; Task 7 covers raw evidence, provenance and queue timing; Task 8 covers Obsidian; Task 9 covers derived memory and temporal current retrieval; Task 10 covers RAG, ContextPack, MCP and Desktop truth; Task 11 covers evaluation, Mac-first acceptance and release.
- [ ] **Placeholder scan:** Search this plan for forbidden placeholder markers and vague future-work wording; none may remain before implementation begins.
- [ ] **Type consistency:** `AuthorizationScope`, `ConversationRecord`, `RawObject`, `ProvenanceEvent`, `TemporalFact`, `CurrentMemoryFilter`, `ContextPackBuilder` and `AutomaticMemoryWorkView` are defined before downstream tasks consume them; every downstream method includes parameter and return types.
- [ ] **Boundary review:** No planned adapter reads cookies, credentials, browser profiles, private databases, process memory or opaque Claude storage; no planned task adds a second memory authority or changes the IDLE local task.
- [ ] **Validation review:** Every task has a failing-test command, passing-test command, exact files and a commit command; Task 11 contains the numeric acceptance thresholds and macOS-first order.
