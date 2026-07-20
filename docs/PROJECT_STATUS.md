# PROJECT_STATUS.md — LingJi Project Status

> Updated: 2026-07-20
> Branch: `feature/second-brain-memory`
> Architecture authority: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
> Execution roadmap: `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`

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

The repository must not continue as two independently expanding memory products.

## 2. Data Authority

```text
Obsidian Vault + Git
= permanent memory and formal knowledge text

configurable raw archive
= original imported material

lingji_state.db
= runtime jobs, queue and audit events

lingji_memory.db
= rebuildable lexical and metadata index

Qdrant
= rebuildable semantic index
```

`second_brain.sqlite3` remains compatibility data during migration. It is not the long-term memory authority.

## 3. Verified Mainline Capabilities

`src/` currently provides:

- Obsidian single-Vault memory model
- rebuildable `lingji_memory.db`
- FTS5, BM25, trigram and Chinese short-term fallback retrieval
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
- compatibility API and PySide6 acceptance flows

No new formal product capability should be added there.

## 5. P0-02 Port Contract

Repository implementation has landed:

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Implemented:

- `src/runtime/ports.py` validates the three-service contract
- `run_mcp_server.py` checks HTTP port availability before startup
- authenticated `GET /api/mcp/status` exposes configuration truth
- Tauri remains on `8766` only

Validation still pending:

- real Windows simultaneous binding
- full repository pytest
- Tauri real runtime smoke

Report: `docs/TEST_REPORTS/P0_02_PORT_CONTRACT_TEST_REPORT.md`

## 6. P0-03 Workspace And Capability Contract

Repository implementation has landed.

Implemented:

- one frozen `WorkspaceContext`
- one `WorkspaceResolver`
- production and acceptance physical path contracts
- explicit override, environment, Settings and safe-default precedence
- isolated Vault, raw, state DB, memory DB, Qdrant path/collection, logs, cache, runtime settings, queue DB, backups, derived files, temp and reports
- explicit rejection of unknown workspaces, path aliases, containment and Windows `C:` paths
- remote Qdrant URL sharing with mandatory collection isolation
- explicit `WorkspaceContext` seam in `build_memory_gateway()`
- directory-independent lexical Memory Capability Contract adapter
- lexical contracts for stable IDs, retrieval, citations, filters, Core Memory, Context Pack and workspace isolation

Validation state:

- isolated workspace contract suite: `8 passed`
- Python syntax validation: passed
- lexical Memory Capability Contract against full repository checkout: pending
- related memory regressions: pending
- full repository pytest: pending

No database schema, dependency, Qdrant client, collection, real Vault or user data was changed.

Report: `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`

## 7. Current Critical Gaps

1. `src/gateway/bootstrap.py` still passes `semantic_provider=None`.
2. The new workspace contract is not yet mandatory for every runtime service.
3. Runtime Settings does not yet expose editable memory, vector, workspace or MCP groups.
4. Two memory authorities and two ingestion paths still exist during migration.
5. Tauri Brain Status is not yet guaranteed to use the same real memory/vector statistics as MCP and the future Inspector.
6. `LocalControlService.brain_status()` may still report false zero memory/vector counts.
7. The inherited `src/config.py` backup default remains developer-specific and requires a separate safe migration task.
8. P0-02 and P0-03 full local validation remain pending.

## 8. Development Freeze Rules

Effective immediately:

- new memory features only in `src/`
- new ingestion only in `src/extraction/`
- new primary UI only in Tauri
- `second_brain/` only for migration blockers, compatibility reads, export and parity tests
- no direct Tauri calls to `8765` or `8767`
- no deletion of compatibility data before export, parity and rollback validation

## 9. Next Development Sequence

### Current gate

P0-03 repository code exists, but Phase 1 is not fully cleared until:

1. P0-02 real-machine port validation passes.
2. `tests/test_memory_capability_contract.py` runs against a complete checkout.
3. related memory regressions run.
4. failures, if any, are recorded without weakening tests.

### Phase 1: Unified semantic provider

After the gate:

- add a unified Embedding Provider under Model Center
- adapt Qdrant behavior into `src` SemanticProvider contracts
- add incremental upsert/delete, rebuild, health and counts
- preserve lexical fallback and the existing RRF pipeline
- consume `WorkspaceContext` for collection/path isolation
- expose real vector/model state to Local Control API

Do not start Memory Inspector before the semantic and statistics foundations exist.

### Later phases

- Phase 2: structured source/conversation/message read model
- Phase 3: shared statistics, retrieval trace, Memory Inspector and Vector Center
- Phase 4: revisions, relations, conflicts and UI parity
- Phase 5: dual-read verification, stop legacy writes, read-only window and retirement

## 10. Current Test Status

P0-03 execution evidence available in this repository-edit task:

```text
python -m pytest tests/test_workspace_contract.py -q
8 passed, 1 inherited Pydantic warning
```

The new Python files also passed `py_compile`.

Not executed here:

- `tests/test_memory_capability_contract.py`
- related memory regressions
- full `tests/` suite
- real Windows path/symlink behavior
- real process and Tauri validation

The GitHub branch had no workflow run available, and the connector does not provide a complete local worktree. These items remain pending rather than being mislabeled as passed.

## 11. Implementation Commits

```text
7242e6a7d105b8fe7ba35a7020ab735d7798a4b5
feat(runtime): add isolated workspace context

337203032c575f2f8a4654bcae530cc97711b25e
test(memory): add lexical capability contract
```
