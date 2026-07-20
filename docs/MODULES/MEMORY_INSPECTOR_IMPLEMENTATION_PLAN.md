# LingJi Memory Inspector Implementation Plan

Status: Staged development after unified semantic prerequisite
Updated: 2026-07-20
Primary module: `src` MemoryGateway + Local Control API + Tauri
Architecture: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
Audit: `docs/TECH_RESEARCH/SRC_SECOND_BRAIN_CAPABILITY_AUDIT.md`

## 1. Corrected Goal

Implement a read-only Memory Inspector for the one unified LingJi memory system.

It must show:

- what permanent memories and formal knowledge exist
- where they came from and their citation lines
- lifecycle and owner-review state
- relations, revisions and conflict candidates
- whether lexical and semantic indexes exist
- why a current search returned each result
- which project, privacy, time and Agent Scope filters participated
- active embedding model and Qdrant state

The Inspector must not turn the compatibility `second_brain.sqlite3` into the final memory authority.

## 2. Corrected Runtime Chain

```text
Tauri / React
  -> authenticated Local Control API :8766
  -> src MemoryGateway and unified read models
       -> Obsidian Vault + Git authority
       -> lingji_memory.db lexical/metadata index
       -> Qdrant SemanticProvider
       -> state/events/source read models
```

`second_brain/` is a migration and compatibility source only.

PySide6 remains an acceptance and diagnostic reference. New primary Inspector development belongs only in Tauri.

## 3. Verified Prerequisite

`src/retrieval/hybrid.py` supports `SemanticProvider`, but `src/gateway/bootstrap.py` currently passes `semantic_provider=None`.

Therefore a complete Inspector with real vector state and semantic trace depends on the unified Qdrant provider work.

Do not bypass this prerequisite by making Tauri read the legacy database as its permanent backend.

## 4. Development Boundaries

Version 1 is read-only.

Do not expose:

- edit memory
- approve or reject
- promote or supersede
- archive or delete
- automatic conflict resolution
- Qdrant rebuild from the Inspector page
- raw vector values

Do not:

- create a second retrieval algorithm
- duplicate MemoryGateway filters or ranking
- make Tauri call `8765`
- use the compatibility SQLite memory body as final truth
- fabricate historical retrieval explanations
- mix production and acceptance storage
- hardcode memory types, statuses or model state independently in React

Changes to rebuildable index/read-model schemas require an explicit design note and tests. Permanent-memory authority must remain unchanged.

## 5. Backend Read Model

Create or extend a read-only Inspector facade under the long-term `src` path.

It composes:

- `src/gateway/memory_gateway.py`
- `src/retrieval/memory_db.py`
- `src/retrieval/hybrid.py`
- Qdrant SemanticProvider and vector diagnostics
- state and audit events
- source/conversation derived read model when available
- relation, revision and conflict derived read models when available

Responsibilities:

- list and filter canonical memories
- return detail and citations
- return current index revision
- return source and provenance metadata
- return lifecycle and review state
- derive vector existence without mutation
- return system and workspace state
- return current-search retrieval trace

## 6. One Retrieval Pipeline

Normal search and traced search must call the same internal retrieval implementation.

```text
search()
  -> shared candidate collection
       -> FTS5/BM25
       -> Chinese fallback
       -> optional Qdrant semantic channel
       -> metadata/privacy/time/Agent Scope filters
       -> RRF and existing boosts
       -> dedupe and citations

search_with_trace()
  -> same implementation
  -> results + explanation metadata
```

No second scoring formula is permitted.

## 7. Trace Contract

A current-search trace should include:

```text
query
workspace
memory_revision
lexical_available
semantic_available
embedding_model
qdrant_collection
warnings
filters:
  project
  memory_types
  statuses
  privacy
  agent_id
  tags
  as_of
results[]:
  memory_id
  chunk_id
  title
  citation
  retrieval_channels
  lexical_rank
  semantic_rank
  semantic_similarity
  rrf_score
  metadata_boosts
  final_retrieval_score
  project_match
  privacy_match
  time_match
  agent_scope_match
  explanation
```

The exact fields may evolve, but explanations must be derived from the real shared ranking process.

Historical logs cannot reconstruct fields that were never stored. Version 1 explains only searches executed through the trace path.

## 8. Vector Inspection Contract

The unified vector provider must expose read-only diagnostics:

- mode and endpoint/path
- collection and workspace
- readiness
- vector dimension
- configured, fallback and active embedding models
- counts by payload kind
- per-memory and per-chunk point existence
- missing expected points
- orphan points when detectable
- last write, query and rebuild timestamps when tracked
- dimension mismatch and rebuild-required state
- last error

Qdrant outage must preserve lexical search and return a visible degraded warning.

## 9. Source and Revision Views

Source view should prefer canonical and rebuildable evidence:

- Vault path and line range
- raw snapshot reference
- source type and external ID
- model and import metadata
- conversation/message metadata when the derived read model exists
- Git/file revision and audit events

Full private message content is expanded only after explicit user action.

Relations, versions and conflicts must reference canonical memory IDs. Legacy tables may be used for migration verification, not as the final read source.

## 10. Local Control API

Tauri calls only `127.0.0.1:8766`.

Recommended authenticated read-only contracts:

```text
GET  /api/memory/inspector/status
GET  /api/memory/inspector/list
GET  /api/memory/inspector/{memory_id}
GET  /api/memory/inspector/{memory_id}/source
GET  /api/memory/inspector/{memory_id}/vector
POST /api/memory/inspector/search
```

Routes may be consolidated if existing API conventions provide a cleaner contract. They must delegate to shared services, not contain independent SQL or ranking logic.

Brain Status, Memory Inspector and MCP must use the same statistics provider.

## 11. Tauri Page

Location: `desktop/lingji-control/src/pages/`

Required sections:

1. workspace and memory revision
2. authority and storage paths
3. memory counts and lifecycle distribution
4. filterable paginated memory list
5. read-only detail and citations
6. source/provenance panel
7. revisions, relations and conflicts
8. lexical and vector index state
9. per-item vector existence
10. current retrieval trace
11. clear degraded and error warnings

The page must distinguish:

- canonical memory text
- lexical index state
- semantic index state
- source evidence
- compatibility migration data

## 12. Workspace Isolation

Production and acceptance must isolate:

- Vault or fixture Vault
- raw archive
- state database
- memory index database
- Qdrant collection/path
- logs
- runtime settings

Every Inspector response includes the selected workspace.

## 13. Development Order

### Stage 0: contracts and freeze

- confirm canonical IDs and workspace contract
- freeze new legacy Inspector development
- define shared status, trace and vector response types

### Stage 1: unified semantic provider

- adapt Qdrant and Ollama embedding into `src`
- connect `build_memory_gateway()`
- add incremental synchronization, rebuild and health
- add production/acceptance isolation
- test lexical fallback

### Stage 2: base Inspector backend

- canonical list/detail/citations
- index and vector status
- current retrieval trace
- unified statistics

### Stage 3: control API and Tauri

- authenticated `8766` routes
- Memory Inspector page
- persistent global health indicators
- no direct legacy API calls

### Stage 4: source, relation and conflict enrichment

- rebuildable conversation/message read model
- revision and relation read model
- read-only conflict candidates

### Stage 5: dual-read migration verification

- compare legacy and unified results
- explain differences
- prove formal behavior with compatibility runtime disabled

## 14. Tests

Required contract tests:

- same Vault input produces stable memory and chunk IDs
- list/detail use canonical memory data
- citations include file and line ranges
- normal and trace search return the same ordered results
- lexical-only mode works when Qdrant is unavailable
- semantic results obey privacy, time and Agent Scope
- active/core vector coverage is consistent
- production and acceptance are physically isolated
- missing memory returns 404
- warnings are separate from result rows
- Brain Status, Inspector and MCP counts agree
- Tauri uses only `8766`
- every Inspector route is read-only
- legacy runtime can be disabled for formal Inspector flows after migration

Run relevant Python tests and Playwright/Tauri smoke tests. Do not lower assertions or hide unavailable dependencies.

## 15. Acceptance Criteria

Accepted only when:

- the user inspects canonical LingJi memory in the Tauri desktop
- source and citations are visible
- lexical and semantic index states are truthful
- per-item vector existence is visible
- current retrieval reasons match the real ranking pipeline
- Qdrant failure degrades cleanly to lexical search
- AI permissions and workspace isolation remain enforced
- Brain Status, Inspector and MCP agree
- no permanent-memory authority was duplicated
- documentation and test report are updated

## 16. Deferred

- editing and destructive lifecycle actions
- automatic conflict resolution
- historical trace reconstruction
- raw vector display
- compatibility database retirement
- large visual redesign unrelated to information architecture
