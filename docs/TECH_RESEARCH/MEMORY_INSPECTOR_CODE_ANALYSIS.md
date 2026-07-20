# Memory Inspector Code Analysis

> Repository: `wangduoyu001/lingji`
>
> Branch analyzed: `feature/second-brain-memory`
>
> Analysis baseline: remote HEAD before this report, `99214a7f68f60f8cbac28092a87a7feacb599cc3`
>
> Scope: code and architecture analysis only. No functional code, dependency, database, schema, or runtime configuration changes.

## Existing Architecture

LingJi currently contains two related but separate application stacks.

### Second Brain stack

```text
scripts/second_brain/start-api.ps1
  -> uvicorn second_brain.api:app (127.0.0.1:8765)
  -> RuntimeRegistry
       -> production Runtime
       -> acceptance Runtime
            -> Database (SQLite)
            -> OllamaEmbedder
            -> VectorStore (Qdrant)
            -> MemoryService
            -> RetrievalService
            -> DistillationService
            -> connectors
```

The Second Brain API is the real owner of the current memory CRUD, retrieval, source, knowledge, conflict, timeline, and vector-rebuild behavior.

`RuntimeRegistry` creates two physically separated workspaces:

- Production database: configurable through `SECOND_BRAIN_DB`, default `data/second_brain.sqlite3`.
- Acceptance database: `data/acceptance/second_brain.sqlite3`.
- Production Qdrant collection: configurable through `SECOND_BRAIN_QDRANT_COLLECTION`, default `lingji_memories_v1`.
- Acceptance Qdrant collection: `lingji_acceptance_v1`.

The API selects the runtime using the `X-LingJi-Workspace` request header. The default is `production`.

### Local Control Center stack

```text
desktop/lingji-control/src/main.tsx
  -> Root.tsx
  -> App.tsx
  -> Tauri / React pages
  -> Local Control API (127.0.0.1:8766)
       -> run_control_api.py
       -> src.control.api.create_control_app()
       -> LocalControlService
```

The Tauri control center is the long-term main desktop UI according to the repository rules. It currently talks only to the Local Control API on port `8766`, not directly to the Second Brain API on port `8765`.

The current `BrainStatusPage` calls `/api/brain/status`. `LocalControlService.brain_status()` tries to read `overview["memory_stats"]`, but `LocalControlService.overview()` does not currently return a `memory_stats` field. Therefore the Tauri page can report memory and vector counts as zero even when the Second Brain database contains data. Memory Inspector should not reuse that inaccurate aggregation without first connecting it to the real Second Brain runtime or a read-only Second Brain client.

### Documentation path discrepancy

The requested file:

`docs/TECH_RESEARCH/MEMORY_INSPECTOR_IMPLEMENTATION_PLAN.md`

does not exist on the analyzed branch.

The real implementation plan is:

`docs/MODULES/MEMORY_INSPECTOR_IMPLEMENTATION_PLAN.md`

A related design document also exists at:

`docs/MODULES/memory_inspector.md`

Both were read for this analysis. Future task instructions should use the real path to avoid false missing-file failures.

### Current architecture conclusion

Memory Inspector should be a read-only explanation layer over the existing Second Brain services. It must not create a second memory store, second retrieval implementation, third desktop dashboard, or database migration.

The safest target architecture is:

```text
Tauri Memory Inspector page
  -> Local Control API read-only inspector endpoints
  -> read-only integration with Second Brain Runtime / inspector facade
       -> MemoryService for canonical memory reads
       -> RetrievalService for retrieval behavior
       -> Database for versions, relations, source metadata and logs
       -> VectorStore for collection health and vector metadata
```

The PySide6 desktop can remain an acceptance and compatibility UI, but new primary UI work should land in the Tauri control center.

## MemoryService

### Real path

`second_brain/memory/service.py`

### Class

`MemoryService`

### Constructor dependencies

```text
Database
OllamaEmbedder
VectorStore
```

These dependencies are created in `second_brain/runtime.py::build_runtime()` and shared with `RetrievalService` and the connectors.

### Methods

| Method | Responsibility |
|---|---|
| `__init__(database, embedder, vectors)` | Stores shared runtime dependencies. |
| `ensure_project(name)` | Normalizes the project name, returns an existing project ID, or inserts a new project. |
| `create(...)` | Inserts a memory and initial version, performs duplicate detection through the database uniqueness constraint, and indexes immediately when status is `active`. |
| `get(memory_id)` | Reads one memory joined with the project name. Raises `KeyError` when missing. |
| `set_status(memory_id, status, reason)` | Updates status, appends a version record, indexes active memories, and deletes non-active memories from Qdrant. |
| `supersede(old_memory_id, new_memory_id, new_memory, reason)` | Activates or creates the replacement, marks the old memory superseded, records relation/version history, removes the old vector, and indexes the new memory. |
| `pending()` | Lists pending memories ordered by creation time descending. |
| `_index(memory)` | Embeds title plus content and upserts the vector using the memory ID as the Qdrant point ID. |
| `rebuild_vectors()` | Rebuilds Qdrant from all active memories and all knowledge-document chunks. |

### Write data flow

```text
MemoryService.create()
  -> ensure_project()
  -> SQLite memories INSERT
  -> SQLite memory_versions INSERT(version=1)
  -> get()
  -> when status == active
       -> _index()
       -> OllamaEmbedder.embed(title + content)
       -> VectorStore.upsert(memory_id, vector, payload)
```

### Status data flow

```text
MemoryService.set_status()
  -> get existing memory
  -> update memories.status
  -> append memory_versions row
  -> active: embed and upsert
  -> any other status: delete Qdrant point by memory ID
```

### Supersede data flow

```text
MemoryService.supersede()
  -> read old memory
  -> create or activate new memory
  -> mark old memory superseded
  -> set new.supersedes_id
  -> insert memory_relations(type=supersedes)
  -> append old memory version
  -> delete old Qdrant point
  -> index new memory
```

### Inspector-relevant findings

1. `MemoryService` has no general list method, version method, source expansion method, or embedding-status method. Existing list/detail API handlers query SQLite directly.
2. Memory point IDs in Qdrant are exactly the SQLite memory IDs. This makes read-only correlation straightforward.
3. Only `active` memories are expected to have vectors. Any other status removes the memory point.
4. The `memory_type` value is uppercased but not validated against a canonical enum. Documentation and UI currently disagree on available types. Inspector filters should not hardcode a new list until the project defines one authoritative source.
5. Valid statuses are defined in code as: `pending`, `active`, `superseded`, `conflicted`, `rejected`, `archived`, `deleted`. Existing PySide filters omit `deleted`.
6. Inspector must call no write methods. In particular, it must not use `set_status()`, `supersede()`, `rebuild_vectors()`, or any direct `UPDATE`/`INSERT` statement.

## RetrievalService

### Real path

`second_brain/retrieval/service.py`

### Class

`RetrievalService`

### Methods

| Method | Responsibility |
|---|---|
| `search(query, project, memory_types, active_only, top_k, include_knowledge)` | Hybrid retrieval from SQLite text matching and Qdrant semantic search, followed by filtering, score merging, sorting, and retrieval-log insertion. |
| `context(project, task, max_tokens)` | Calls `search()`, applies an approximate character budget, and groups selected results into knowledge, rules, decisions, lessons, preferences, and source references. |

### Query flow

```text
request query
  -> normalize project and memory types
  -> SQLite memory LIKE search
       title LIKE query OR content LIKE query
       optional active/type/project filters
       initial score = 0.55
  -> optional SQLite knowledge LIKE search
       title LIKE query OR content LIKE query
       optional project filter
       initial score = 0.65
  -> OllamaEmbedder.embed(query)
  -> Qdrant search(limit = top_k * 4)
  -> filter Qdrant results by project, kind, status and memory type
  -> merge by point/result ID
       score = max(existing score, 0.7 * Qdrant similarity)
  -> sort descending
  -> keep top_k
  -> insert retrieval_logs(query, project_id, result_ids_json, created_at)
  -> return list
```

When a project is supplied, retrieval includes both that project and `global`. This should be visible in any retrieval explanation because a result can be returned through global fallback rather than a direct project match.

### Current score meaning

The returned `score` is a ranking heuristic, not a probability or a normalized confidence value.

- Exact memory text match starts at `0.55`.
- Exact knowledge text match starts at `0.65`.
- Vector contribution is `0.7 * similarity`.
- The final score is the maximum of the exact-match seed and vector contribution, not a sum.

Inspector UI should label it as `ranking score` or `retrieval score`, not `confidence`.

### Qdrant failure behavior

Vector errors are caught. SQLite results remain available, and a synthetic item is inserted:

```text
id = vector-warning
kind = warning
content = exception text
```

The warning is not written into `result_ids_json`. A future trace response should separate warnings from actual results instead of displaying the warning as a fake memory row.

### Retrieval trace gap

The existing `retrieval_logs` table persists only:

- query
- project value
- result ID list
- created time

It does not persist:

- exact-match reason
- vector similarity
- final merged score
- filter decisions
- source metadata
- active/global project fallback reason
- embedding model used
- Qdrant warning

Because the implementation plan forbids a database migration, the first Inspector version should return trace details synchronously from a read-only retrieval method. It should not attempt to invent historical explanations from `retrieval_logs`, because those facts were never stored.

Recommended behavior is to preserve `search()` for compatibility and add a trace-capable read path that reuses the same ranking implementation. The retrieval algorithm must have one internal implementation, not two drifting copies.

## Database

### Database location

Configuration is defined in:

`second_brain/config.py`

Production default:

`data/second_brain.sqlite3`

Override:

`SECOND_BRAIN_DB`

Acceptance database:

`data/acceptance/second_brain.sqlite3`

Acceptance path construction is defined in:

`second_brain/runtime_registry.py::acceptance_settings()`

### Schema location

The schema is an inline `SCHEMA` SQL string in:

`second_brain/db.py`

Initialization flow:

```text
build_runtime()
  -> Database(config.database_path)
  -> Database.initialize()
  -> connection.executescript(SCHEMA)
```

There is no separate migration framework or schema directory in the current Second Brain implementation.

### `memories` table structure

| Column | Type / constraint | Meaning |
|---|---|---|
| `id` | `TEXT PRIMARY KEY` | Stable memory ID and Qdrant point ID for memory vectors. |
| `memory_type` | `TEXT NOT NULL` | Uppercased logical type, currently not constrained by SQL enum. |
| `title` | `TEXT NOT NULL` | Memory title. |
| `content` | `TEXT NOT NULL` | Canonical memory content. |
| `project_id` | `TEXT REFERENCES projects(id)` | Optional owning project. |
| `status` | `TEXT NOT NULL DEFAULT 'pending'` | Lifecycle status. |
| `importance` | `REAL NOT NULL DEFAULT 0.5` | Ranking/business importance value. |
| `confidence` | `REAL NOT NULL DEFAULT 0.5` | Memory confidence value, separate from retrieval score. |
| `valid_from` | `TEXT` | Start of validity period. |
| `valid_to` | `TEXT` | End of validity period. |
| `supersedes_id` | `TEXT REFERENCES memories(id)` | Previous memory superseded by this memory. |
| `source_id` | `TEXT REFERENCES sources(id)` | Source record. |
| `source_excerpt` | `TEXT` | Stored source excerpt. |
| `content_hash` | `TEXT NOT NULL` | Duplicate-detection hash. |
| `created_at` | `TEXT NOT NULL` | Creation timestamp. |
| `updated_at` | `TEXT NOT NULL` | Last update timestamp. |

Uniqueness:

`UNIQUE(content_hash, project_id)`

Index:

`idx_memories_status_project(status, project_id)`

### Related tables needed by Inspector

| Table | Inspector use |
|---|---|
| `projects` | Resolve project ID to name. |
| `sources` | Show source type, source reference, metadata and creation time. |
| `memory_versions` | Show version and status history. |
| `memory_relations` | Show supersede and future relation links. |
| `conflicts` | Show open/resolved conflict state. |
| `retrieval_logs` | Show historical query and returned IDs, with the limitations described above. |
| `conversations` / `messages` | Optional source expansion. Full message content should not be returned by default. |

### Database findings

1. Existing `/memory/{memory_id}` already returns the memory, versions, relations and conflicts.
2. Existing `/memory/source/{source_id}` returns source, conversations and full messages. Inspector should default to source metadata and require explicit expansion for full content to reduce privacy exposure and payload size.
3. `retrieval_logs.project_id` is not a foreign key and currently receives the project string passed to `RetrievalService.search()`. Inspector must not assume it contains a real `projects.id` value.
4. No schema change is required for list, detail, source, health, current retrieval trace, or vector-state inspection.

## Vector Layer

### Initialization location

Runtime assembly:

`second_brain/runtime.py::build_runtime()`

```text
OllamaEmbedder(config.ollama_url, config.embed_model, config.fallback_embed_model)
VectorStore(config.qdrant_collection, path=config.qdrant_path, url=config.qdrant_url)
```

Qdrant client implementation:

`second_brain/vector_store.py::VectorStore`

The client is lazy-initialized when `VectorStore.client` is first accessed.

Modes:

- Remote: `QdrantClient(url=...)`
- In-memory test: `QdrantClient(location=":memory:")`
- Embedded local: `QdrantClient(path=...)`

### Collection names

Production default:

`lingji_memories_v1`

Configuration variable:

`SECOND_BRAIN_QDRANT_COLLECTION`

Acceptance:

`lingji_acceptance_v1`

### Embedding entry

Embedding implementation:

`second_brain/embedding.py::OllamaEmbedder.embed()`

Primary model default:

`bge-m3`

Fallback model default:

`nomic-embed-text`

Ollama endpoints:

1. `/api/embed`
2. `/api/embeddings` fallback when the first endpoint returns 404

Embedding call sites relevant to Inspector:

- `MemoryService._index()` for active memory insertion/update.
- `MemoryService.rebuild_vectors()` for full rebuild.
- `RetrievalService.search()` for query vectors.
- `ObsidianConnector.index_file()` for knowledge chunks.

### Vector payloads

Memory point:

```text
id = memory.id
payload = kind, title, content, memory_type, project, status
```

Knowledge point:

```text
id = deterministic_id(document_id, chunk_index)
payload = kind, document_id, chunk_index, title, content, project, source_path
```

### Vector findings

1. `VectorStore.status()` provides collection-level mode, name, readiness and total vector count.
2. There is no existing method to check one memory point by ID or to list all memory vector IDs without vectors.
3. A per-memory `embedding_status` shown by Inspector cannot be read from SQLite because no such column exists.
4. It can be derived read-only from status plus Qdrant point existence, but the vector layer needs a minimal read method for point metadata/existence. This must not mutate the collection.
5. Collection count includes both memory vectors and knowledge chunks, so total Qdrant count is not equal to memory count.
6. Dimension mismatch raises an error instructing the user to rebuild Qdrant.
7. Qdrant remains a cache. SQLite is the canonical source.

## API Layer

### Second Brain startup entry

`script/second_brain/start-api.ps1` does not exist. The real path is:

`scripts/second_brain/start-api.ps1`

It starts:

```text
python -m uvicorn second_brain.api:app --host 127.0.0.1 --port 8765
```

FastAPI application:

`second_brain/api.py::app`

### Router location

There is no `APIRouter` module for the Second Brain API. All routes are registered directly on one `FastAPI` instance in `second_brain/api.py` through `@app.get()` and `@app.post()` decorators.

This file is already approximately 517 lines and contains memory, knowledge, system, watcher and acceptance endpoints.

### Existing Inspector-like endpoints

| Endpoint | Existing behavior |
|---|---|
| `GET /memory/list` | Filtered and paginated memory list with project join. |
| `GET /memory/{memory_id}` | Memory detail, versions, relations and conflicts. |
| `GET /memory/source/{source_id}` | Source, conversations and messages. |
| `POST /memory/search` | Hybrid search through `RetrievalService.search()`. |
| `GET /memory/status` | Counts, memory states, Qdrant status, embedding status and paths. |
| `GET /memory/timeline` | Memory/task/import event union. |

The planned endpoints `GET /memory/inspector/list` and `GET /memory/inspector/{id}` would duplicate existing functionality unless they return an Inspector-specific normalized view. The implementation should either:

1. Reuse the existing endpoints in the UI and add only trace/vector explanation endpoints, or
2. Add Inspector endpoints as thin read-only adapters that delegate to one shared implementation.

Do not duplicate SQL or retrieval ranking in multiple handlers.

### Local Control API startup entry

`run_control_api.py`

FastAPI factory:

`src/control/api.py::create_control_app()`

Default port:

`127.0.0.1:8766`

This is the API used by the Tauri desktop UI. It currently has only `/api/brain/status` for memory-related display and has no memory list, detail, source, retrieval, or trace endpoints.

### API recommendation

The Tauri UI should continue using the authenticated loopback Local Control API. The control layer should expose read-only Memory Inspector endpoints and internally reuse the Second Brain implementation. The browser/Tauri front end should not independently call port `8765`, because that bypasses the control token boundary and creates two client configurations.

A future refactor may split `second_brain/api.py` into routers, but that is not required for the first Inspector and should not be mixed into this feature unless explicitly approved.

## UI Layer

### Legacy PySide6 UI

Entry:

`second_brain/desktop/main.py::main()`

Window:

`second_brain/desktop/main_window.py::MainWindow`

API client:

`second_brain/desktop/api_client.py::ApiClient`

The client talks directly to `http://127.0.0.1:8765` and defaults to the acceptance workspace.

Page structure:

1. 系统总览 — `DashboardPage`
2. 一键验收 — `AcceptancePage`
3. 聊天导入 — `ImportPage`
4. 记忆审核 — `MemoryPage`
5. 搜索与上下文 — `SearchPage`
6. 冲突处理 — `ConflictPage`
7. Obsidian知识 — `KnowledgePage`
8. 任务与时间线 — `ActivityPage`
9. 系统与监听器 — `SystemPage`

`MemoryPage` already consumes `/memory/list` and `/memory/{id}`. `SearchPage` already consumes `/memory/search` and `/memory/context`.

This UI is the shortest experimental integration point, but it should not become the primary new dashboard because repository rules designate the Tauri control center as the main UI.

### Main Tauri / React UI

Entry chain:

```text
desktop/lingji-control/src/main.tsx
  -> Root.tsx
  -> App.tsx
```

Navigation definition:

`desktop/lingji-control/src/navigation.ts`

Current pages:

1. 总览
2. 脑状态
3. 系统与算力
4. AI 与模型
5. 任务
6. 主动投喂
7. 媒体分析
8. 存储
9. 备份
10. 环境验收
11. 设置
12. 日志

Tauri native entry:

`desktop/lingji-control/src-tauri/src/main.rs`

The native layer supplies control API credentials and defaults the control API base URL to `http://127.0.0.1:8766`.

### UI recommendation

Add Memory Inspector as a page in the existing Tauri navigation, preferably adjacent to `脑状态`. The page should contain:

- status and count summary
- memory filters and paginated list
- read-only detail panel
- source metadata panel
- versions, relations and conflicts tabs
- vector/embedding state
- retrieval trace panel with exact-match and semantic-match explanation
- separate warning display when Qdrant or embedding is unavailable
- production/acceptance workspace indicator

The page must not include delete, approve, reject, supersede, rebuild, or any other write action in the first Inspector phase.

Do not create a separate desktop application or a third dashboard.

## Development Entry Points

### Backend read model

Primary existing files to reuse:

- `second_brain/memory/service.py`
- `second_brain/retrieval/service.py`
- `second_brain/db.py`
- `second_brain/vector_store.py`
- `second_brain/runtime.py`
- `second_brain/runtime_registry.py`

Recommended implementation rule:

- Keep `MemoryService` write behavior unchanged.
- Add read-only inspection behavior through a thin facade or clearly isolated read methods.
- Refactor retrieval only enough to share one ranking pipeline between normal search and traced search.
- Do not create a second ranking algorithm.
- Do not add a database migration.

### Second Brain API

Entry:

`second_brain/api.py`

Existing endpoints should be reused where possible. If Inspector-specific endpoints are required by the product contract, they should be thin adapters and should return normalized read-only response models.

Suggested trace response fields:

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
  status_filter_match
  type_filter_match
  explanation
```

This trace should be generated during the current search. Historical `retrieval_logs` cannot provide these details.

### Local Control API

Entry files:

- `src/control/service.py`
- `src/control/api.py`
- `run_control_api.py`

Required architectural correction before UI trust:

- Replace the current non-functional `overview["memory_stats"]` assumption with data from the real Second Brain runtime or a read-only Second Brain integration.
- Expose authenticated read-only Inspector endpoints through port `8766`.
- Preserve the Tauri single-API model.

### Tauri UI

Entry files:

- `desktop/lingji-control/src/types.ts`
- `desktop/lingji-control/src/navigation.ts`
- `desktop/lingji-control/src/App.tsx`
- `desktop/lingji-control/src/api.ts`
- `desktop/lingji-control/src/pages/BrainStatusPage.tsx`
- a future Inspector page under `desktop/lingji-control/src/pages/`

Do not hardcode memory types or statuses independently in the new page. Prefer values returned by the backend or a shared contract.

### Tests to extend during implementation

Existing relevant tests:

- `tests/test_second_brain.py`
- `tests/test_desktop.py`
- `tests/test_control_api.py`
- `tests/test_control_api_extended.py`
- `tests/test_brain_status_e2e.py`
- `desktop/lingji-control/scripts/ui-modular-smoke.mjs`

Required future cases from the implementation plan:

1. List memories.
2. Read detail, source, versions and relations.
3. Return retrieval trace without duplicating ranking logic.
4. Handle missing memory with 404.
5. Preserve SQLite results when Qdrant is unavailable.
6. Separate warnings from actual results.
7. Confirm production and acceptance workspace isolation.
8. Confirm all Inspector operations are read-only.
9. Confirm Tauri uses the control API rather than directly calling port `8765`.
10. Confirm no schema migration is introduced.

### Recommended development order

1. Define a read-only Inspector response contract.
2. Extract or wrap one shared retrieval pipeline capable of returning trace metadata.
3. Add a minimal per-point Qdrant existence/metadata read method.
4. Add Second Brain read-only endpoints or shared facade methods.
5. Integrate the Local Control Service with the real Second Brain read model.
6. Add authenticated Local Control API endpoints.
7. Add the Tauri Memory Inspector page.
8. Add API, fallback, workspace-isolation and UI smoke tests.
9. Update `CODE_MAP.md`, project status, changelog and test report after implementation.

### Blocking and caution items

- The required implementation-plan path in the task is wrong; use `docs/MODULES/MEMORY_INSPECTOR_IMPLEMENTATION_PLAN.md`.
- `docs/PROJECT_STATUS.md` reports latest commit `21fe687`, but the analyzed remote branch HEAD before this report is `99214a7f68f60f8cbac28092a87a7feacb599cc3`. The status document is stale.
- Tauri memory count currently does not come from the Second Brain SQLite database.
- Existing retrieval logs are insufficient for historical explanations.
- Qdrant total vector count mixes memory points and knowledge chunks.
- Memory type definitions differ between documentation and PySide UI.
- The first Inspector should remain strictly read-only and should not expose lifecycle mutations.
