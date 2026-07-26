# MEMORY_SYSTEM.md — LingJi Unified Memory System

> Updated: 2026-07-21
> Status: Active memory contract
> Formal branch: `feature/second-brain-memory`
> Authoritative plan: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Goal

LingJi maintains one owner-controlled permanent memory for the user and one permission-aware memory gateway for all approved AI clients.

The system must not keep two independent permanent-memory databases.

## 2. Authority Model

```text
Permanent memory and formal knowledge text
= Obsidian Vault + Git

Original imported material
= configurable raw archive

Runtime tasks, processing state and audit events
= lingji_state.db

Rebuildable lexical and metadata index
= lingji_memory.db

Rebuildable semantic index
= Qdrant

Structured source/conversation/message query model
= rebuildable derived read model
```

Obsidian remains human-readable and owner-editable. Git records formal changes. SQLite indexes, Qdrant and read models accelerate retrieval and inspection, but do not own permanent truth.

## 3. Current Transition State

`src/` is the long-term memory platform and now provides:

- owner-reviewed memory lifecycle
- Core Memory and context pinning
- FTS5/BM25/trigram retrieval
- Qdrant semantic retrieval with lexical fallback
- privacy, project, tag, time and Agent Scope filters
- citations and Context Pack
- multi-AI MemoryGateway and MCP
- Source/Conversation/Message Structured Read Model
- structured ingestion wiring
- Capture foundation contracts
- Memory Inspector API and Desktop UI

`second_brain/` remains compatibility and migration runtime only. Useful behavior may be migrated into `src`, but no new primary product capability may be developed there.

`second_brain.sqlite3` remains compatibility data, not long-term authority.

## 4. Unified Data Flow

```text
AI chats / Codex / web / files / media / manual feeding
  -> src/capture contract
  -> src/extraction adapter
  -> persistent queue, idempotency and privacy scan
  -> raw snapshot
  -> source Markdown or derived assets
  -> Structured Read Model
  -> memory candidate when appropriate
  -> owner review
  -> permanent memory in Obsidian/Git
  -> incremental lexical and semantic indexing
  -> MemoryGateway
  -> approved AI clients
```

Obsidian formal knowledge is indexed but is not automatically converted into personal memory without an explicit rule and owner review.

## 5. Memory Lifecycle

```text
captured
-> source evidence
-> candidate
-> pending owner review
-> promoted permanent memory
-> active or core
-> superseded / archived with history retained
```

Rules:

1. AI may propose permanent memory when its profile allows it.
2. AI may not silently promote or rewrite Core Memory.
3. Superseded memory remains traceable but must not appear as current context.
4. Conflict detection creates review candidates, not automatic rewrites.
5. Deletion and destructive batch actions require explicit owner confirmation and rollback protection.

## 6. Memory Metadata

The canonical Markdown metadata contract should cover:

- stable memory ID
- title and aliases
- memory type and tier
- status and review status
- privacy
- project and tags
- relationships
- valid-from and valid-to
- superseded-by
- pin-to-context
- Agent Scope
- importance, confidence and recall weight
- source and generation provenance
- content hash and revision information

The UI must not invent a separate enum when a backend contract exists.

## 7. Retrieval

The verified retrieval pipeline is:

```text
FTS5 / BM25 / Chinese fallback
+
Qdrant semantic channel
+
metadata, privacy, time and Agent Scope filtering
+
RRF and existing boosts
```

Qdrant failure must preserve lexical retrieval and return an explicit degraded status. Unknown semantic state must remain unknown rather than being converted to false or zero.

## 8. Context Pack and AI Access

All AI clients must use the unified MemoryGateway.

Context Pack must provide:

- Core Memory priority
- project scope
- privacy and Agent Scope enforcement
- type and tag filters
- strict context budget
- citations and line ranges
- memory revision
- generation time and warnings

Different AI clients may receive different views of the same canonical memory according to permissions. They must not maintain separate authoritative copies.

## 9. Structured Conversations

Source, Conversation and Message records are rebuildable evidence and audit data.

They must be:

- rebuildable from raw snapshots or Vault source documents
- linked to stable source IDs
- privacy filtered
- expandable only on explicit request for full content
- linked to Memory and Chunk when a stable relation exists
- treated as source evidence, not automatically as permanent personal memory

The Memory Inspector is the primary Desktop surface for inspecting these relationships.

## 10. Versions, Evidence, Relations and Conflicts

The next memory-quality stage must be built in this order:

```text
Stable Read Model
+ Memory Inspector
-> Schema v2 and Evidence Layer
-> Revision and provenance
-> Conflict candidates
-> Owner Review UI
-> Knowledge update workflow
```

Evidence, Revision and Conflict must reference canonical Vault/Git content. They must not create another authoritative body store.

Automatic knowledge rewriting is forbidden before owner-review and rollback contracts exist.

## 11. Obsidian CLI Migration

The existing CLI implementation under `second_brain/` is compatibility code.

Target location:

```text
src/obsidian/
```

Target boundaries:

- executable discovery and owner-configured path
- Vault path derived from Workspace or Runtime Settings
- typed CLI command runner
- capability and health status
- Local Control API access through port 8766
- Desktop settings and diagnostics

Machine-specific default installation paths are forbidden. Environment detection may be used as a fallback, but the selected path must be visible and owner-editable.

Full CLI command migration follows the Manual Capture Center. The current P0 stage only registers the final interface, path contract and migration boundary.

## 12. Production and Acceptance

Production and acceptance must physically isolate all mutable resources:

- Vault or fixture Vault
- raw archive
- state database
- memory index
- Qdrant collection/path
- logs
- runtime settings
- backup destinations

No machine-specific absolute path may be a production default.

## 13. Dependency and Validation Contract

Memory-stage validation must distinguish:

- focused milestone gates
- frontend build gates
- clean-environment installation
- optional provider tests
- full-repository environment failures

Requirements must be reproducible and test count changes must be explained. Startup tests must validate observable behavior instead of comparing complete source files as text.

## 14. Migration Safety

Retirement order:

1. migrate missing capability
2. verify against common fixtures and read-only real samples
3. stop legacy auto-start
4. stop legacy writes
5. preserve read-only compatibility
6. export and verify data
7. archive or remove old runtime

Direct deletion before parity and rollback validation is forbidden.

## 15. Current Execution Order

```text
P0 Engineering Hygiene
-> P2-05 Manual Capture Center
-> Obsidian CLI migration into src
-> Schema v2 + Evidence Layer
-> Revision, conflict and owner review
-> relationship expansion and retrieval evaluation
-> additional input sources
-> active intelligence
-> second_brain retirement
```
