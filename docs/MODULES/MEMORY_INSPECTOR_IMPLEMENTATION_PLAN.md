# LingJi Memory Inspector Implementation Plan

Status: Ready for Development
Module: Second Brain + Local Control + Tauri Desktop
Updated: 2026-07-20
Source analysis: `docs/TECH_RESEARCH/MEMORY_INSPECTOR_CODE_ANALYSIS.md`

## 1. Goal

Implement the first usable, strictly read-only Memory Inspector without changing the existing memory schema or creating another memory system.

The feature must make the current Second Brain behavior visible:

1. What memories exist.
2. Where each memory comes from.
3. Current lifecycle status, versions, relations and conflicts.
4. Whether the memory has a corresponding vector point.
5. Why a current search returned each result.
6. Whether exact text matching, semantic matching, project matching or global fallback participated.
7. Which embedding model and Qdrant state were used.

## 2. Confirmed Architecture

The implementation must follow the real runtime chain:

```text
Tauri / React Desktop
  -> Local Control API (127.0.0.1:8766)
  -> authenticated read-only Inspector integration
  -> Second Brain Runtime
       -> MemoryService
       -> RetrievalService
       -> SQLite
       -> OllamaEmbedder
       -> Qdrant VectorStore
```

Confirmed ownership:

- `second_brain/` owns memory CRUD, retrieval, SQLite and Qdrant behavior.
- `src/control/` is the desktop control gateway.
- `desktop/lingji-control/` is the long-term primary desktop UI.
- `second_brain/desktop/` PySide6 remains an acceptance and compatibility UI, not a second primary product.

## 3. Existing Entry Points

### Second Brain

- Memory service: `second_brain/memory/service.py::MemoryService`
- Retrieval service: `second_brain/retrieval/service.py::RetrievalService`
- SQLite schema and access: `second_brain/db.py`
- Configuration: `second_brain/config.py`
- Qdrant access: `second_brain/vector_store.py::VectorStore`
- Embedding: `second_brain/embedding.py::OllamaEmbedder`
- Runtime assembly: `second_brain/runtime.py::build_runtime()`
- Workspace isolation: `second_brain/runtime_registry.py::RuntimeRegistry`
- Second Brain API: `second_brain/api.py`

### Local Control

- Control service: `src/control/service.py::LocalControlService`
- Control API: `src/control/api.py::create_control_app()`
- Startup: `run_control_api.py`

### Tauri Desktop

- Entry: `desktop/lingji-control/src/main.tsx`
- Navigation: `desktop/lingji-control/src/navigation.ts`
- Application composition: `desktop/lingji-control/src/App.tsx`
- API client: `desktop/lingji-control/src/api.ts`
- Types: `desktop/lingji-control/src/types.ts`
- New page location: `desktop/lingji-control/src/pages/`

## 4. Non-Negotiable Boundaries

The first version must remain read-only.

Do not:

- modify memory content or status
- approve, reject, archive, delete or supersede memories
- rebuild Qdrant
- change the SQLite schema
- add a migration framework
- create a second retrieval algorithm
- create a second desktop application
- make Tauri call port `8765` directly
- hardcode memory types or lifecycle statuses independently in the UI
- fabricate historical retrieval explanations that were never stored

All runtime paths must remain configurable and must not introduce C: drive data writes.

## 5. Existing APIs To Reuse

The current Second Brain API already provides:

- `GET /memory/list`
- `GET /memory/{memory_id}`
- `GET /memory/source/{source_id}`
- `POST /memory/search`
- `GET /memory/status`
- `GET /memory/timeline`

Do not duplicate list, detail or normal search SQL merely to create Inspector-branded endpoints.

Allowed implementation choices:

1. Reuse existing list/detail/status behavior and add only Inspector-specific trace and vector-read endpoints.
2. Add thin Inspector adapters only when a normalized UI contract is necessary.

Any adapter must delegate to one shared read implementation.

## 6. Backend Design

### 6.1 Read-Only Inspector Facade

Add a lightweight read model or facade that composes existing services.

Responsibilities:

- normalize memory list and detail responses
- resolve source metadata
- expose versions, relations and conflicts
- derive per-memory vector presence without modifying Qdrant
- return workspace and runtime state
- return current-search retrieval trace

Keep `MemoryService` write behavior unchanged.

### 6.2 Shared Retrieval Pipeline

`RetrievalService.search()` and Inspector trace search must use one internal ranking pipeline.

Recommended shape:

```text
public search()
  -> shared internal retrieval implementation
       -> SQLite exact matching
       -> optional knowledge matching
       -> query embedding
       -> Qdrant search
       -> filter decisions
       -> result merge
       -> ranking
       -> warnings

public search_with_trace()
  -> same internal retrieval implementation
  -> returns results plus trace metadata
```

Do not create two independent ranking calculations.

The Inspector must expose that the current score is a ranking heuristic, not confidence:

- memory text match seed: `0.55`
- knowledge text match seed: `0.65`
- vector contribution: `0.7 * similarity`
- final ranking score: maximum of exact and vector contribution

### 6.3 Trace Contract

Current-search trace should include:

```text
query
workspace
project_scope
embedding_model
vector_available
warnings
results[]:
  id
  kind
  title
  source
  exact_match
  exact_match_fields
  vector_match
  vector_similarity
  ranking_score
  project_match
  global_fallback
  status_filter_match
  type_filter_match
  explanation
```

Warnings must be separate from result rows. Do not return a fake `vector-warning` memory item.

### 6.4 Historical Trace Limitation

The current `retrieval_logs` table stores only query, project value, result IDs and time.

It cannot reconstruct:

- exact-match fields
- vector similarity
- merged ranking score
- filter decisions
- project fallback reason
- embedding model
- Qdrant warning

Therefore version 1 must explain only searches executed through the trace-capable path. It must not invent historical explanations.

### 6.5 Vector Read Support

Add only the minimum read-only VectorStore capability required to inspect one point:

- point exists or not
- payload metadata when available
- collection name and readiness

Do not expose raw vectors by default.

Remember:

- active memories are expected to have vector points
- non-active memories are removed from Qdrant
- Qdrant count includes memory points and knowledge chunks
- SQLite remains authoritative

## 7. API Design

### 7.1 Second Brain Internal Read Contract

Expose or share read-only Inspector behavior from the Second Brain layer.

Preferred additions are limited to capabilities not already covered:

- current retrieval trace
- per-memory vector state
- optional normalized Inspector aggregate

Exact route names may follow existing API style, but duplicate list/detail implementations are forbidden.

### 7.2 Local Control API

Tauri must continue to call only the authenticated Local Control API on port `8766`.

Add read-only control endpoints that delegate to the Second Brain read model, for example:

```text
GET  /api/memory/inspector/status
GET  /api/memory/inspector/list
GET  /api/memory/inspector/{memory_id}
GET  /api/memory/inspector/{memory_id}/source
POST /api/memory/inspector/search
```

These control endpoints may normalize responses for the UI but must not duplicate database or ranking logic.

### 7.3 Brain Status Correction

Fix the current inaccurate memory summary path.

`LocalControlService.brain_status()` must stop relying on a missing `overview["memory_stats"]` value and read actual Second Brain status data.

The existing Brain Status page and the new Inspector page must report consistent counts.

## 8. Tauri UI

Add Memory Inspector to the existing Tauri navigation, preferably adjacent to `脑状态`.

Required sections:

1. Workspace indicator: production or acceptance.
2. Status summary: SQLite, embedding and Qdrant state.
3. Memory count and lifecycle distribution.
4. Filterable, paginated memory list.
5. Read-only memory detail panel.
6. Source metadata panel with explicit expansion for full message content.
7. Versions, relations and conflicts tabs.
8. Per-memory vector status.
9. Retrieval trace search panel.
10. Separate warning area for embedding or Qdrant failures.

The first version must not show write buttons.

Do not add:

- delete
- approve
- reject
- archive
- supersede
- rebuild vectors
- edit memory

PySide6 may be used for regression validation but should not receive a separate new Inspector implementation unless required for compatibility.

## 9. Workspace Isolation

The Inspector must preserve existing runtime isolation:

- production database: configured by `SECOND_BRAIN_DB`, default `data/second_brain.sqlite3`
- acceptance database: `data/acceptance/second_brain.sqlite3`
- production Qdrant collection: configured by `SECOND_BRAIN_QDRANT_COLLECTION`, default `lingji_memories_v1`
- acceptance Qdrant collection: `lingji_acceptance_v1`

Every Inspector response must make the selected workspace clear.

No production and acceptance data may be mixed.

## 10. Development Order

1. Define shared response types and the read-only Inspector contract.
2. Refactor `RetrievalService` minimally so normal and traced search share one internal pipeline.
3. Add minimal per-point Qdrant read support.
4. Implement the Second Brain read-only Inspector facade or thin adapters.
5. Connect `LocalControlService` to the actual Second Brain read model.
6. Add authenticated Local Control API endpoints.
7. Correct Brain Status memory/vector counts.
8. Add the Tauri Memory Inspector page and navigation entry.
9. Add backend, control API, workspace isolation and UI smoke tests.
10. Update code map, project status, changelog and test report.

Avoid unrelated router splitting, directory migration or broad architecture refactoring during this feature.

## 11. Testing

Extend the existing suites:

- `tests/test_second_brain.py`
- `tests/test_desktop.py`
- `tests/test_control_api.py`
- `tests/test_control_api_extended.py`
- `tests/test_brain_status_e2e.py`
- `desktop/lingji-control/scripts/ui-modular-smoke.mjs`

Required cases:

1. List memories through the Inspector path.
2. Read detail, source metadata, versions, relations and conflicts.
3. Return trace without changing normal search ranking.
4. Identify exact-match fields.
5. Return vector similarity and ranking score when Qdrant is available.
6. Preserve SQLite results when Qdrant or embedding is unavailable.
7. Return warnings separately from results.
8. Return 404 for a missing memory.
9. Correctly report per-memory vector presence.
10. Keep production and acceptance workspaces isolated.
11. Confirm all Inspector operations are read-only.
12. Confirm Tauri uses port `8766`, not `8765`.
13. Confirm no schema migration is introduced.
14. Confirm Brain Status and Inspector counts agree.

After implementation run the full existing test suite and the Tauri UI smoke test.

Do not delete tests, lower assertions or hide failures.

## 12. Acceptance Criteria

The feature is accepted only when:

- the user can inspect real Second Brain memories in the Tauri desktop
- the user can inspect source, versions, relations and conflicts
- the user can see whether an active memory has a vector point
- the user can understand why a current search result was returned
- exact, semantic, project and global-fallback reasons are distinguishable
- Qdrant failure falls back to SQLite and shows a warning
- Brain Status uses real Second Brain counts
- Tauri still uses one authenticated API base URL
- no database migration exists
- no write action is exposed
- production and acceptance remain isolated
- existing tests and new tests pass
- documentation and code map are updated
- a Git commit and test report are created

## 13. Deferred Work

Not included in version 1:

- automatic memory deletion
- memory approval or rejection
- memory editing
- autonomous memory rewriting
- ranking-score optimization
- historical trace reconstruction
- raw vector display
- large UI redesign
- removal or restructuring of the PySide6 compatibility UI
- broad split of `second_brain/api.py` into routers
