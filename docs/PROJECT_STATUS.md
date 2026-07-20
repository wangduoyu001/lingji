# PROJECT_STATUS.md — LingJi Project Status

> Updated: 2026-07-20
> Branch: `feature/second-brain-memory`
> Architecture authority: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
> Audit: `docs/TECH_RESEARCH/SRC_SECOND_BRAIN_CAPABILITY_AUDIT.md`

## 1. Current Product Direction

LingJi is converging into one private second brain and one shared memory system for all approved AI clients.

```text
src/
= long-term platform mainline

second_brain/
= compatibility, migration and acceptance runtime

desktop/lingji-control/
= only primary desktop UI
```

The project must not continue as two independently expanding memory products.

## 2. Data Authority Decision

```text
Obsidian Vault + Git
= permanent memory and formal knowledge text

configurable raw archive
= original imported material

lingji_state.db
= runtime jobs and audit events

lingji_memory.db
= rebuildable lexical and metadata index

Qdrant
= rebuildable semantic index
```

`second_brain.sqlite3` remains available during migration and verification, but it is not the final long-term memory authority.

## 3. Verified Mainline Capabilities

`src/` currently provides:

- Obsidian single-Vault memory model
- rebuildable `lingji_memory.db`
- FTS5, BM25, trigram and Chinese fallback retrieval
- project, tag, privacy, time and Agent Scope filtering
- Core Memory and owner-reviewed candidates
- Context Pack, citations and memory revision
- multi-AI profiles and MemoryGateway
- MCP and AI context adapters
- unified extraction queue, idempotency, leases, retries and raw snapshots
- Local Control API and Tauri UI
- hardware/GPU, model, media, backup, storage, skills, scheduler and opportunity services

## 4. Verified Compatibility Capabilities

`second_brain/` still provides capabilities that must be migrated before retirement:

- working Qdrant vector search
- Ollama embedding primary/fallback behavior
- structured sources, conversations and messages
- memory versions, relations and conflicts
- production/acceptance isolation patterns
- compatibility API and PySide6 acceptance flows

## 5. Current Critical Gaps

### P0 architecture blockers

1. `src/gateway/bootstrap.py` still passes `semantic_provider=None`.
2. `second_brain` FastAPI and `src` MCP HTTP both default to `8765`.
3. Two memory authorities and two ingestion paths still exist in current runtime code.
4. Tauri Brain Status is not yet guaranteed to use the same real memory/vector statistics as MCP and the future Inspector.
5. Production/acceptance isolation has not yet been unified across Vault, raw data, SQLite, Qdrant, logs and settings.

### Documentation status

The stale dual-system documentation has been corrected. Current documents now distinguish:

- verified implementation
- target architecture
- compatibility behavior
- unresolved migration work

## 6. Target Port Map

```text
8766 = Local Control API and Tauri gateway
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
```

This is a target contract. The code change and tests are still pending.

## 7. Development Freeze Rules

Effective immediately:

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only for migration blockers, compatibility reads, export and parity tests
- no direct Tauri calls to `8765`
- no deletion of compatibility data before export, parity and rollback validation

## 8. Next Development Sequence

### Phase 1: Unified semantic provider

- adapt `second_brain` Qdrant and embedding behavior into `src.retrieval.hybrid.SemanticProvider`
- connect `build_memory_gateway()`
- add incremental upsert/delete, rebuild, health and counts
- preserve lexical fallback
- isolate production and acceptance
- expose vector/model state to Local Control API

### Phase 2: Unified source read model

- migrate rebuildable source/conversation/message queries
- preserve role, ordinal, timestamp, model, attachments and provenance
- add privacy filtering

### Phase 3: Memory Inspector and Vector Center

- build on the unified `src` MemoryGateway
- use Local Control API `8766`
- show canonical memory, citations, retrieval trace and vector existence
- make Brain Status, Inspector and MCP statistics agree

### Phase 4: Relations, conflicts and UI migration

- migrate revision, relation and conflict read models
- audit previous local/PySide UI capability parity
- keep only Tauri as the primary product

### Phase 5: Dual-read verification and retirement

- compare common fixtures and read-only real samples
- export compatibility data
- test with legacy runtime disabled
- stop legacy auto-start and writes
- preserve read-only compatibility window
- archive or remove only after rollback requirements pass

## 9. Documentation Corrections Completed

Updated or created:

- `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/AI_CONTEXT.md`
- `docs/MEMORY_SYSTEM.md`
- `docs/VECTOR_DATABASE.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/MODULES/MEMORY_INSPECTOR_IMPLEMENTATION_PLAN.md`
- `docs/MODULES/UNIFIED_DESKTOP_UI_PLAN.md`
- `docs/DEVELOPMENT_RULES.md`
- `docs/TECH_RESEARCH/MEMORY_INSPECTOR_CODE_ANALYSIS.md`

## 10. Test Status

This convergence task changed documentation only.

- no functional code was changed
- no database or dependency was changed
- no local runtime test was executed for this documentation task
- existing historical test reports remain historical evidence, not proof of the new target architecture

The next code phase must create a dedicated Markdown implementation/test report after Qdrant SemanticProvider integration.
