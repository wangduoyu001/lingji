# PROJECT_STATUS.md — LingJi Project Status

> Updated: 2026-07-20
> Branch: `feature/second-brain-memory`
> Architecture authority: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
> Execution roadmap: `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`
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

## 5. P0-02 Port Contract Status

Repository implementation has landed.

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Implemented:

- `src/config.py` now defaults MCP HTTP to `8767`
- compatibility API port is explicitly represented as `8765`
- `src/runtime/ports.py` validates the three-service port contract
- `run_mcp_server.py` checks HTTP port availability before startup
- authenticated `GET /api/mcp/status` exposes configuration truth
- `GET /api/settings` includes the read-only MCP runtime contract
- Tauri remains on `8766` only
- tests cover defaults, overrides, collisions, occupied ports and Tauri gateway boundaries

Validation state:

- dependency-light isolated port-contract tests: passed
- full repository pytest: not run in this repository-edit task
- real Windows MCP/Control/compatibility simultaneous binding: pending
- Tauri real runtime smoke: pending

Report:

- `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`

P0-02 must remain marked `awaiting local validation` until the real-machine tests pass.

## 6. Current Critical Gaps

### P0 architecture blockers

1. `src/gateway/bootstrap.py` still passes `semantic_provider=None`.
2. WorkspaceContext and physical production/acceptance path resolution are not implemented.
3. The directory-independent Memory Capability Contract is not implemented.
4. Two memory authorities and two ingestion paths still exist in current runtime code.
5. Tauri Brain Status is not yet guaranteed to use the same real memory/vector statistics as MCP and the future Inspector.
6. Production/acceptance isolation has not yet been unified across Vault, raw data, SQLite, Qdrant, logs and settings.
7. `src/control/runtime_settings.py` does not yet expose editable memory, vector, workspace or MCP setting definitions.
8. `src/config.py` still contains a developer-specific absolute backup default and no Qdrant fields.

The previous default `8765` MCP/compatibility conflict has been corrected in repository code, subject to local validation.

## 7. Development Freeze Rules

Effective immediately:

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only for migration blockers, compatibility reads, export and parity tests
- no direct Tauri calls to `8765` or `8767`
- no deletion of compatibility data before export, parity and rollback validation

## 8. Next Development Sequence

### Phase 0: Runtime contracts

Current next task:

```text
P0-03 WorkspaceContext and Memory Capability Contract
```

Required work:

- define production/acceptance physical resource paths
- add `WorkspaceContext` and resolver contracts
- create a directory-independent Memory Capability Contract test skeleton
- keep the contract lexical-only until Phase 1 connects semantic retrieval

Do not start Qdrant integration before P0-03 establishes the workspace boundary.

### Phase 1: Unified semantic provider

- add a unified EmbeddingProvider under Model Center
- adapt `second_brain` Qdrant behavior into `src` SemanticProvider contracts
- connect `build_memory_gateway()`
- add incremental upsert/delete, rebuild, health and counts
- preserve lexical fallback and the existing RRF pipeline
- isolate production and acceptance
- expose real vector/model state to Local Control API

### Phase 2: Unified source read model

- migrate rebuildable source/conversation/message queries
- preserve role, ordinal, timestamp, model, attachments and provenance
- add privacy filtering and explicit body expansion

### Phase 3: Memory Inspector and Vector Center

- build on the unified `src` MemoryGateway
- use Local Control API `8766`
- show canonical memory, citations, retrieval trace and vector existence
- make Brain Status, Inspector and MCP statistics agree

### Phase 4: Relations, conflicts, workspace and UI migration

- migrate revision, relation and conflict read models
- finish production/acceptance physical isolation
- migrate previous local/PySide UI capability according to the roadmap matrix
- keep only Tauri as the primary product

### Phase 5: Dual-read verification and retirement

- compare common fixtures and read-only real samples
- export compatibility data
- test with legacy runtime disabled
- stop legacy auto-start and writes
- preserve read-only compatibility window
- archive or remove only after rollback requirements pass

## 9. Test Status

P0-02 changed runtime configuration, startup validation, control API, tests and documentation.

Completed in this task:

- pure Python syntax validation for the new runtime contract and control API source
- isolated contract suite with five passing tests
- GitHub remote diff verification

Not completed in this task:

- full repository pytest
- optional MCP dependency integration
- real Windows port binding
- real Tauri smoke/Playwright validation
- CI status, because GitHub has not returned a workflow status for these commits

No database, schema, dependency, Qdrant data or user runtime data was modified.

## 10. Current Development Gate

P0-03 may be planned and implemented at repository level now, but Phase 1 Qdrant work should not begin until:

1. P0-02 real-machine port validation passes.
2. WorkspaceContext exists.
3. The lexical-only Memory Capability Contract skeleton runs.
4. Any local failures are recorded in the P0-02 report instead of being hidden.
