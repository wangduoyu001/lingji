# ARCHITECTURE.md — LingJi Unified Architecture

> Updated: 2026-07-21
> Status: Active architecture contract
> Formal branch: `feature/second-brain-memory`
> Authoritative plan: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Product Definition

LingJi is one local-first private second brain, one shared memory system for approved AI clients, and one desktop control center.

The repository contains compatibility code during migration, but it must not evolve into multiple long-term products.

## 2. Long-Term Ownership

```text
src/
= long-term platform mainline
= capture, extraction, memory gateway, retrieval, MCP, control API, tasks and operations

second_brain/
= compatibility and migration runtime only
= no new primary product features

desktop/lingji-control/
= only primary desktop UI

second_brain/desktop/
= compatibility, acceptance and emergency diagnosis only
```

New memory features, capture contracts, adapters and primary UI pages must be developed in `src/` and `desktop/lingji-control/`, not duplicated in `second_brain/`.

## 3. Data Authority

```text
Permanent memory and formal knowledge text
= Obsidian Vault + Git history

Original imported material
= configurable storage/raw archive

Runtime jobs, processing state and audit events
= lingji_state.db

Rebuildable lexical and metadata index
= lingji_memory.db

Rebuildable semantic index
= Qdrant

Structured source/conversation/message queries
= rebuildable derived read model
```

SQLite indexes, Qdrant and the Structured Read Model are derived, rebuildable data. They are not independent permanent-memory authorities.

`second_brain.sqlite3` remains compatibility data during migration and must not become a second source of truth.

## 4. Current Verified Runtime

```text
Input Sources
  -> src/capture contracts
  -> src/extraction adapters
  -> persistent SQLite extraction queue
  -> raw snapshot
  -> Vault source documents
  -> Structured Read Model
  -> lexical and semantic indexing

Obsidian Vault + Git
  -> lingji_memory.db
       -> FTS5 / BM25 / trigram / metadata
  -> Qdrant SemanticProvider
       -> semantic chunks
  -> HybridRetriever
       -> RRF and metadata weighting
       -> privacy, project, tag, time and Agent Scope
  -> ContextPackBuilder
  -> Unified MemoryGateway
       -> MCP
       -> Local Control API
       -> internal jobs

Tauri Desktop
  -> authenticated Local Control API :8766
```

The following are implemented and focused-tested:

- unified semantic provider wiring in `src`
- Qdrant-backed semantic retrieval with lexical degradation
- Source/Conversation/Message Structured Read Model
- structured ingestion wiring
- Capture foundation contracts
- Memory Inspector Local Control API and Desktop UI

## 5. Retrieval Contract

```text
FTS5 / BM25 / Chinese substring fallback
+
Qdrant semantic search
+
metadata, privacy, time and Agent Scope filters
+
RRF and existing boosts
=
One retrieval pipeline
```

Qdrant failure must not disable lexical retrieval. Unknown vector state must not be fabricated as success or zero.

## 6. Port Contract

```text
8766 = Local Control API and Tauri gateway
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
8765 = compatibility API only during migration
```

Rules:

- Tauri must use `8766`.
- New product APIs must be added to the Local Control API, not the compatibility API.
- `8765` must not receive new primary product responsibilities.

## 7. UI Architecture

The final primary UI is `desktop/lingji-control/`.

It must expose truthful read models for:

- overview and service health
- manual Capture Center
- memory inspector
- knowledge and Obsidian indexing
- sources and conversations
- tasks and structured progress
- vector center
- models, CPU and GPU
- AI clients, permissions and MCP
- opportunity system
- storage, backup and recovery
- settings
- logs and diagnostics

PySide6 may remain during migration for acceptance and diagnosis, but it must not receive new competing product features.

## 8. Workspace and Path Contract

Production and acceptance must physically isolate:

- Vault or fixture Vault
- raw archive
- state database
- memory index database
- Qdrant collection or path
- logs
- generated assets
- runtime settings
- backup destination

Path rules:

1. No machine-specific absolute path may be a production default.
2. Paths must derive from Workspace, Runtime Settings, environment detection or explicit owner selection.
3. Environment detection may propose a path but must not silently make it permanent authority.
4. A request header alone does not provide physical isolation.

## 9. Dependency and Test Contract

Before new product stages depend on a package or startup entry:

- dependency ownership must be explicit
- versions must be reproducible
- clean-environment installation must be validated
- startup tests must verify behavior, not compare whole files byte-for-byte
- test count changes must be explained in the stage report
- targeted stage gates and full-repository results must be reported separately

## 10. Obsidian CLI Migration Contract

The existing Obsidian CLI implementation in `second_brain/` is compatibility code.

Target ownership:

```text
src/obsidian/
  -> CLI discovery and configuration
  -> typed command runner
  -> capability/status service
  -> Local Control API integration
  -> Desktop settings and status
```

Current migration step is contract registration and path cleanup only. Full command migration follows the Manual Capture Center and stable 8766 API boundary.

No new primary Obsidian CLI features may be added under `second_brain/`.

## 11. Migration Rules

1. Freeze new duplicate development in `second_brain/`.
2. Keep Obsidian Vault + Git as permanent authority.
3. Treat SQLite, Qdrant and read models as rebuildable derivatives.
4. Complete engineering hygiene before P2-05 implementation branches begin.
5. Build the Manual Capture Center on existing Capture, Extraction and Queue contracts.
6. Migrate Obsidian CLI into `src` after the Capture Center boundary is stable.
7. Add Schema v2 and Evidence Layer only after current read models and UI are stable.
8. Add conflict review and knowledge update only after Evidence, Revision and owner-review contracts exist.
9. Preserve read-only compatibility and rollback evidence before retiring legacy runtime.

Direct deletion of `second_brain/` or its database is forbidden before parity, export and rollback checks pass.

## 12. Current Execution Order

```text
P0 Engineering Hygiene
  -> path cleanup
  -> dependency and clean-install baseline
  -> startup test repair
  -> documentation authority alignment
  -> Obsidian CLI migration registration

P2-05 Manual Capture Center
  -> Capture Control API
  -> manual import wiring
  -> Desktop Capture Center

Obsidian CLI migration into src
Schema v2 + Evidence Layer
Knowledge revision, conflict and owner review
Retrieval evaluation and relationship expansion
Additional sources and active intelligence
Legacy second_brain retirement
```

## 13. References

- `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
- `docs/MODULES/UNIFIED_DESKTOP_UI_PLAN.md`
- `docs/MODULES/P0_ENGINEERING_HYGIENE_PLAN.md`
- `docs/MODULES/P2_05_MANUAL_CAPTURE_CENTER_PLAN.md`
- `docs/MEMORY_SYSTEM.md`
- `docs/VECTOR_DATABASE.md`
