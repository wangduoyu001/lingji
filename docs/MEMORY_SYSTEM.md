# MEMORY_SYSTEM.md — LingJi Unified Memory System

> Updated: 2026-07-20
> Status: Target memory contract with migration notes
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

Structured conversation/message query model
= rebuildable derived index
```

Obsidian remains human-readable and owner-editable. Git records formal changes. Indexes accelerate retrieval but do not own permanent truth.

## 3. Current Transition State

`src/` is the long-term memory platform and already provides:

- owner-reviewed memory lifecycle
- Core Memory and context pinning
- FTS5/BM25/trigram retrieval
- privacy, project, tag, time and Agent Scope filters
- citations and Context Pack
- multi-AI MemoryGateway and MCP

`second_brain/` remains a compatibility runtime because it still provides:

- live Qdrant and Ollama embedding
- structured sources, conversations and messages
- memory versions, relations and conflicts
- production/acceptance isolation patterns

These capabilities must be migrated into `src` without preserving a second authority.

## 4. Unified Data Flow

```text
AI chats / Codex / web / files / media / manual feeding
  -> src/extraction adapter
  -> input hash, idempotency and privacy scan
  -> raw snapshot
  -> source Markdown or derived assets
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

The final retrieval pipeline is:

```text
FTS5 / BM25 / Chinese fallback
+
Qdrant semantic channel
+
metadata, privacy, time and Agent Scope filtering
+
RRF and existing boosts
```

Current verified limitation: `src` has the semantic provider interface but does not yet connect it in `build_memory_gateway()`.

Qdrant failure must preserve lexical retrieval and return an explicit degraded status.

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

Source, conversation and message records are useful for audit and source expansion.

They must be:

- rebuildable from raw snapshots or Vault source documents
- linked to stable source IDs
- privacy filtered
- expandable only on explicit request for full content
- treated as source evidence, not automatically as permanent personal memory

## 10. Versions, Relations and Conflicts

The final query model may combine:

- Git history
- file and state events
- Markdown relationships
- deterministic derived tables

The useful query patterns from `second_brain` may be migrated, but the final read model must reference the canonical Vault memory rather than maintain a second memory body.

## 11. Production and Acceptance

Production and acceptance must physically isolate all mutable resources:

- Vault or fixture Vault
- raw archive
- state database
- memory index
- Qdrant collection/path
- logs and runtime settings

## 12. Migration Safety

`second_brain.sqlite3` must remain available during dual-read verification and export.

Retirement order:

1. migrate missing capability
2. verify against common fixtures and read-only real samples
3. stop legacy auto-start
4. stop legacy writes
5. preserve read-only compatibility
6. export and verify data
7. archive or remove old runtime

Direct deletion before parity and rollback validation is forbidden.
