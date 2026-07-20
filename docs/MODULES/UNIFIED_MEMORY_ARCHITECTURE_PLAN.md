# LingJi Unified Memory Architecture Plan

Status: Authoritative convergence plan
Updated: 2026-07-20
Branch: `feature/second-brain-memory`
Evidence:

- `docs/TECH_RESEARCH/SRC_SECOND_BRAIN_CAPABILITY_AUDIT.md`
- `src/gateway/bootstrap.py`
- `src/retrieval/memory_db.py`
- `src/retrieval/hybrid.py`
- `second_brain/vector_store.py`
- `second_brain/embedding.py`

## 1. Product Goal

LingJi is one private second brain for the owner and one shared memory system for all approved AI clients.

The final product must provide:

- one permanent-memory authority
- one ingestion pipeline
- one retrieval and context gateway
- one primary desktop UI
- one task, status and audit system
- one model and vector configuration center
- multiple AI clients with explicit privacy and tool permissions

Repository directories are implementation details. They must not become separate products.

## 2. Verified Current State

### 2.1 `src/` strengths

`src/` already provides the stronger long-term platform foundation:

- Obsidian single Vault and Git-traceable permanent memory
- rebuildable `lingji_memory.db`
- FTS5, BM25, trigram and short Chinese substring fallback
- metadata, project, tag, time, privacy and Agent Scope filters
- Core Memory, owner-reviewed candidates and lifecycle controls
- Context Pack, citations and memory revision
- AI profiles and permission-aware MemoryGateway
- MCP, unified extraction queue, retries, leases and idempotency
- Local Control API, Tauri UI, model center, GPU, media, backup, skills, scheduler and opportunity services

Current limitation: `src/gateway/bootstrap.py` builds `HybridRetriever` with `semantic_provider=None`. The semantic channel exists as an interface but is not connected.

### 2.2 `second_brain/` strengths

`second_brain/` remains a working compatibility runtime with capabilities not yet fully replaced in `src/`:

- real Qdrant embedded, in-memory and remote modes
- Ollama embedding primary/fallback execution
- structured source, conversation and message records
- memory version, relation and conflict tables
- production and acceptance workspace isolation
- read and acceptance API flows
- PySide6 acceptance and diagnostic UI

It must not be deleted before these capabilities are migrated and verified.

## 3. Final Authority Model

The final system uses one clear data authority model:

```text
Permanent memory and formal knowledge text
= Obsidian Vault + Git history

Original imported material
= configurable storage/raw archive

Runtime jobs, events and processing state
= lingji_state.db

Rebuildable lexical and metadata index
= lingji_memory.db

Rebuildable semantic index
= Qdrant

Rebuildable conversation/message query model
= derived source index generated from raw or Vault documents
```

Rules:

1. No SQLite `memories` table may remain a second permanent-memory authority.
2. AI-generated permanent-memory candidates require owner approval before promotion.
3. Qdrant and `lingji_memory.db` may be deleted and rebuilt from authoritative sources.
4. Runtime events and task state are records of execution, not permanent-memory text.
5. Structured conversation/message tables are query and audit indexes, not owner identity truth.

## 4. Final Runtime Architecture

```text
Input Sources
  -> src/extraction adapters and persistent queue
  -> raw snapshot and privacy scan
  -> Vault source documents / memory candidates
  -> owner review for permanent memories
  -> incremental index synchronization

Obsidian Vault + Git
  -> lingji_memory.db (FTS5/BM25/metadata)
  -> Qdrant SemanticProvider (semantic chunks)
  -> Unified HybridRetriever (RRF + metadata weighting)
  -> Unified MemoryGateway
       -> Context Pack
       -> citations
       -> privacy and Agent Scope
       -> MCP
       -> Local Control API
       -> internal jobs

Tauri Desktop
  -> authenticated Local Control API :8766
  -> unified read/write services under owner controls
```

## 5. Port and Process Contract

Target port map:

```text
8766 = Local Control API and the only Tauri backend gateway
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport for Codex and compatible clients
```

Transition rule:

- the existing `second_brain` FastAPI on `8765` is compatibility-only
- the current `src` default MCP port of `8765` is a confirmed conflict when HTTP transport is enabled
- code must be changed and tested before documentation may claim the conflict is resolved
- Tauri must never call `8765` directly

## 6. Retrieval Integration Design

Do not replace the mature `src` retrieval pipeline.

Implement a Qdrant adapter that satisfies `src.retrieval.hybrid.SemanticProvider`:

```text
FTS5 / BM25 / Chinese fallback
+
Qdrant semantic channel
+
metadata, privacy, time and Agent Scope filters
+
RRF and existing boosts
=
final unified retrieval
```

Required semantic provider behavior:

- stable `memory_id` and `chunk_id`
- incremental upsert and delete
- full rebuild
- collection health and count by payload kind
- production/acceptance collection isolation
- dimension mismatch detection
- fallback to lexical retrieval when unavailable
- trace data without duplicating ranking logic
- no raw vector exposure by default

The useful implementation patterns in `second_brain/vector_store.py` and `second_brain/embedding.py` should be adapted, not copied into a second retrieval stack.

## 7. Structured Source Migration

Preserve the audit value of:

- source
- conversation
- message
- role
- ordinal
- timestamp
- model
- attachment reference
- import provenance

Target design:

- rebuildable from raw snapshots or Vault source documents
- linked to canonical source IDs
- privacy-filtered
- full message text expanded only on explicit request
- never treated as permanent memory automatically

## 8. Memory Lifecycle, Relations and Conflicts

The final lifecycle is owner-controlled:

```text
captured source
-> extracted candidate
-> pending owner review
-> promoted permanent memory
-> active/core
-> superseded or archived with history retained
```

Relations and conflict detection become unified read models based on:

- Vault Frontmatter and links
- Git/file revision history
- state and audit events
- deterministic derived indexes

Conflict detection may create a review candidate. It must never silently rewrite Core Memory.

## 9. Workspace Isolation

Production and acceptance must isolate all mutable and derived resources:

- Vault or acceptance fixture Vault
- raw archive
- `lingji_state.db`
- `lingji_memory.db`
- Qdrant collection/path
- logs
- generated assets
- runtime settings

A request header alone is not sufficient if both workspaces share physical storage.

## 10. Single UI Contract

The only primary UI is:

`desktop/lingji-control/`

`second_brain/desktop/` is frozen for acceptance, compatibility and emergency diagnosis.

The Tauri UI must expose:

- overview and truthful service health
- memory inspector
- knowledge and Obsidian state
- source and conversation audit
- tasks and structured progress
- vector center
- model, CPU and GPU state
- AI clients, permissions and MCP state
- opportunity center
- storage, backup and restore
- settings
- logs and diagnostics

Every visible value must come from a backend read model. The UI must not fabricate zero counts, success, GPU use or vector readiness.

## 11. Memory Inspector Final Design

Memory Inspector must read the unified `src` MemoryGateway and its derived read models.

It must not use `second_brain.sqlite3` as the final memory truth.

Required capabilities:

- memory list, filters and detail
- source and citation lines
- lifecycle and owner-review state
- relations, revisions and conflict candidates
- per-memory and per-chunk vector existence
- current retrieval trace
- lexical/semantic channels
- RRF/ranking explanation
- project, privacy, time and Agent Scope decisions
- embedding model and Qdrant status
- consistent counts with Brain Status and MCP

Development dependency: Qdrant must first be connected to the `src` semantic provider, or Inspector must clearly label semantic data as unavailable. It may not temporarily make the compatibility database the new authority.

## 12. Migration Phases

### Phase 0: Freeze divergence

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only receives migration blockers, compatibility reads and migration tests
- document the current `8765` conflict

### Phase 1: Unified semantic provider

- adapt Qdrant and Ollama embedding into `src`
- add runtime/model-center configuration
- add health, counts and per-item existence
- preserve lexical fallback
- isolate production and acceptance

### Phase 2: Structured source read model

- migrate source/conversation/message query capability
- make it rebuildable
- add privacy and provenance contracts

### Phase 3: Relations, conflicts and Inspector

- build relation/version/conflict read models
- connect Brain Status and Inspector to one statistic source
- implement Tauri Memory Inspector through `8766`

### Phase 4: Dual-read verification

Compare the same fixtures and real read-only samples:

- source and conversation counts
- candidate and permanent-memory counts
- lexical and semantic results
- citations
- privacy and Agent Scope
- vector point coverage
- relations and conflicts
- production/acceptance isolation

Every difference requires an explanation. Total-count equality alone is insufficient.

### Phase 5: Retire compatibility runtime

Only after parity and rollback requirements pass:

1. stop `second_brain` auto-start
2. stop compatibility writes
3. preserve a read-only migration window
4. export and verify old data
5. archive or remove the runtime and PySide6 product path

Never directly delete the directory or database first.

## 13. Required Contract Tests

- stable memory/chunk IDs from the same Vault input
- lexical and semantic results both include citations
- Qdrant outage preserves lexical retrieval
- remote AI cannot read restricted memory
- active/core memory and Qdrant points remain consistent
- superseded memory is excluded from current context
- source/conversation/message index rebuilds from authoritative input
- production and acceptance are physically isolated
- Brain Status, Inspector and MCP statistics agree
- Tauri uses only the Local Control API
- one input cannot be written by both ingestion systems
- all formal capabilities still work with compatibility runtime disabled

## 14. Definition of Done

LingJi is converged only when:

- the owner opens one desktop application
- every approved AI reads memory through one MemoryGateway
- permanent memory has one owner-editable authority
- lexical and semantic retrieval use one ranking pipeline
- every important task, setting, model and vector state is visible
- compatibility runtime can be disabled without losing formal capability
- migration has tested rollback and data export
