# Task 6S Source Authority and Evidence Versions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make current structured evidence query-time safe against the existing StateDB authority and retain immutable content-hash versions in the existing rebuildable memory index.

**Architecture:** Inject one resolver into the existing Hybrid/Gateway/ContextPack composition. The resolver batch-reads the existing AutomaticMemory SourceRegistry/StateDatabase and fail-closes automatic structured evidence when the authority is unknown, unavailable, locked, revoked, or expired; history/as_of remain temporal reads subject to existing viewer/project filters. Extend the existing `memory_documents` projection with deterministic `(source, conversation, message, content_hash)` identities and validity/supersession fields, preserving old rows instead of adding a store or table.

**Tech Stack:** Python, SQLite, existing `StateDatabase`, `SourceReadModel`, `MemoryDatabase`/FTS, `HybridRetriever`, `MemoryGateway`, `ContextPackBuilder`, pytest.

## Global Constraints

- StateDB AutomaticMemory SourceRegistry/StateDatabase is the only authorization authority.
- `lingji_memory.db` and `memory_documents` remain rebuildable projections; no new DB, API, retriever, queue, or permanent-memory source.
- Current automatic structured evidence must fail closed; ordinary Obsidian/non-automatic memory is unaffected.
- History/as_of preserve old evidence versions without bypassing privacy, project, agent, or viewer safety.
- Automatic imports never write Obsidian/Core/candidates and never call promotion.
- Tests use temporary roots only; no live 8766/8767, Artifact, Production, Vault, or owner data.

### Task 1: Query-time source authority guard

**Files:**
- Create: `src/retrieval/source_authority.py`
- Modify: `src/retrieval/hybrid.py`
- Modify: `src/gateway/bootstrap.py`
- Modify: `src/gateway/memory_gateway.py`
- Test: `tests/test_task6s_source_authority_versions.py`

- [ ] Write failing tests for natural expiry, projection failure, revoke-vs-upsert, StateDB unavailable/locked, unknown source, and ordinary memory pass-through.
- [ ] Run the focused test file and verify the expected authorization failures.
- [ ] Implement a batch resolver over existing StateDB source rows, inject it through packaged gateway composition, and filter only automatic structured evidence for current/why queries with truthful diagnostics.
- [ ] Run the focused source-authority tests to green.

### Task 2: Immutable evidence versions and replay

**Files:**
- Modify: `src/retrieval/memory_db.py`
- Modify: `src/extraction/structured_sink.py`
- Modify: `src/sources/read_model.py` only if needed to preserve authority metadata
- Test: `tests/test_task6s_source_authority_versions.py`

- [ ] Add real pipeline tests for v1→v2 current/history/as_of, same-byte replay, cross-source identity, and sequential raw replay rebuild.
- [ ] Run the version tests before implementation and verify stale history/version failures.
- [ ] Materialize one document per logical identity plus content hash; archive prior active rows atomically with `valid_to`, `superseded_by`, `supersedes`, and reason metadata; do not delete archived structured evidence during sync.
- [ ] Run focused version tests to green and verify Qdrant failure retains lexical evidence through the same Gateway path.

### Task 3: Regression, documentation, and evidence

**Files:**
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Modify: `docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`
- Create: `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6s-report.md`

- [ ] Run Task6L regressions, Task2/3 lifecycle+ingestion, packaged lexical helper, promotion quarantine, compile, diff, sync, and handoff gates.
- [ ] Record RED/GREEN, regression counts, four prior Important closures, residual Task6 blockers, and no-live-data boundaries.
- [ ] Commit product/tests separately from docs/evidence and report both SHAs to the root agent for fresh independent review.
