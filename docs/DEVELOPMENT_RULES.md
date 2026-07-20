# DEVELOPMENT_RULES.md — LingJi Development Rules

> Updated: 2026-07-20
> Architecture authority: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Branch and Environment Isolation

1. Current development branch: `feature/second-brain-memory`.
2. Never modify or write runtime data into `C:\Users\Administrator\Documents\New project-ai`.
3. Runtime data must never be silently written to the C: drive.
4. Databases, vectors, logs, cache, uploads, generated assets and models must use configurable locations, preferably D: or a user-selected path.
5. Never hardcode developer-specific absolute paths.
6. Production and acceptance must physically isolate Vault, raw data, databases, Qdrant, logs, settings and generated assets.

## 2. Mandatory Architecture Direction

1. `src/` is the only long-term platform mainline.
2. `second_brain/` is a compatibility, migration and acceptance runtime.
3. New memory features must be implemented in `src/`.
4. New production ingestion must use `src/extraction/`.
5. New primary desktop features must use `desktop/lingji-control/`.
6. `second_brain/` may receive only:
   - migration-blocking fixes
   - compatibility reads
   - export/migration utilities
   - parity and acceptance tests
7. Do not build equivalent production databases, retrieval algorithms, APIs or UI pages in both paths.
8. Do not delete `second_brain/` or its database before migration parity, export and rollback requirements pass.

## 3. Data Authority

```text
Permanent memory and formal knowledge text
= Obsidian Vault + Git

Original imported material
= configurable raw archive

Runtime task and audit state
= lingji_state.db

Rebuildable lexical/metadata index
= lingji_memory.db

Rebuildable semantic index
= Qdrant

Structured source/conversation/message data
= rebuildable derived read model
```

Rules:

1. Do not introduce another permanent-memory authority.
2. AI-generated permanent-memory candidates require owner approval.
3. AI may not silently modify Core Memory.
4. Qdrant and `lingji_memory.db` must remain rebuildable.
5. Compatibility SQLite data may be read during migration but must not become the final truth source.

## 4. Development Understanding Requirement

Before code changes:

1. confirm branch, remote HEAD and workspace state
2. read `AGENTS.md`, `AI_CONTEXT.md`, `PROJECT_STATUS.md`, `ARCHITECTURE.md` and the relevant module plan
3. locate the real class/function entry point
4. identify the data authority and whether the target is mainline or compatibility code
5. confirm API registration and Tauri gateway
6. confirm storage/workspace boundaries
7. confirm test files and the required Markdown report

Do not create files based only on feature names or assumptions.

Prefer current code maps and verified analysis over repeated full-repository scanning, but re-check code when documents conflict.

## 5. Research Before Development

For design and development work:

1. understand the user requirement and current code
2. review relevant official documentation and reliable implementations when the technology is external or may have changed
3. produce a detailed implementation plan
4. implement with minimal, maintainable code
5. avoid repeated broad refactors
6. create or update a Markdown report after each completed feature or substantial tested code section

## 6. Task Routing

Use the simplest capable execution method.

Use direct repository/document actions for:

- documentation corrections
- architecture decisions
- code review
- small non-runtime changes

Use Codex or local execution when required for:

- running tests
- checking hardware and local models
- building desktop applications
- debugging runtime services
- validating filesystem, Qdrant or Ollama behavior

Independent agents may handle isolated tasks only when their file ownership and contracts do not overlap.

## 7. Retrieval and Vector Rules

1. Preserve the mature `src` HybridRetriever pipeline.
2. Qdrant must be adapted through `src.retrieval.hybrid.SemanticProvider`.
3. Normal search and traced search must share one internal ranking pipeline.
4. Metadata, privacy, time and Agent Scope filters must apply to semantic results.
5. Qdrant failure must preserve lexical retrieval and report degraded state.
6. Do not expose raw vectors by default.
7. Model or dimension changes must trigger an explicit rebuild-required state.
8. Vector counts and per-item existence must come from backend-confirmed data.
9. Do not claim unified semantic retrieval is implemented while `build_memory_gateway()` still passes `semantic_provider=None`.

## 8. Port and API Rules

Target port map:

```text
8766 = authenticated Local Control API and Tauri gateway
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
```

Current transition warning:

- `second_brain` FastAPI currently uses `8765`
- `src` MCP HTTP currently defaults to `8765`
- the conflict is unresolved until code and tests change it

Rules:

1. Tauri must call only the Local Control API on `8766`.
2. Do not add direct Tauri calls to `8765`.
3. Do not assume an HTTP memory-context endpoint is available merely because the legacy API is running.
4. Prefer stdio MCP for local Codex integration until the HTTP port change is implemented and tested.

## 9. Unified Desktop UI and Visibility

1. `desktop/lingji-control/` is the only primary desktop UI.
2. `second_brain/desktop/` and previous local UI implementations are migration, acceptance and diagnostic sources.
3. Audit and migrate useful capabilities before retiring duplicate UI paths.
4. Every major user-facing capability and supported setting must be discoverable in the primary UI or a labeled advanced view.
5. Long tasks must expose structured progress: stage, processed/total, failures, elapsed time and current activity when available.
6. The UI must expose memory, knowledge, sources, vectors, models, GPU/CPU, tasks, watcher, scheduler, storage, backup and service health.
7. Vector visibility is mandatory: mode, collection, readiness, model, dimension, counts, failures and per-item existence.
8. The UI must never fabricate success, zero counts, GPU use, vector readiness or task completion.
9. Brain Status, Memory Inspector, Vector Center and MCP must use shared statistics providers.

## 10. Data and Ingestion Boundaries

1. All new automatic inputs enter through `src/extraction/`.
2. Inputs require an approved adapter, explicit source scope and privacy handling.
3. No drive-wide scanning.
4. Raw source snapshots must retain provenance.
5. Input hashes, adapter versions and idempotency keys must prevent duplicate ingestion.
6. Obsidian formal knowledge is indexed but not silently distilled into personal memory.
7. AI chats and other approved inputs may generate memory candidates, not automatic permanent facts.
8. No automatic publishing.

## 11. Obsidian and Git Safety

1. Read notes before modifying them.
2. No delete, overwrite or batch move without explicit approval.
3. Batch operations must support dry-run.
4. Operations affecting more than 20 notes must stop for preview unless already explicitly approved.
5. Create a Git checkpoint before modifying formal knowledge in bulk.
6. Re-read and verify after writing.
7. Generated content records source, generation time and task ID.
8. Do not commit `.obsidian` cache, secrets, tokens, personal chats, databases or personal absolute paths.

## 12. File and Code Conventions

1. Python files use UTF-8 without BOM.
2. Legacy text may be read with `utf-8-sig`.
3. Use type hints for public Python APIs.
4. Public tool responses use the project result contract where applicable.
5. Keep layers clear: source/data, derived indexes, services/gateway, control/operations, UI.
6. Avoid embedding business logic in API route handlers or React components.
7. Do not duplicate SQL, ranking or status calculations across endpoints.

## 13. Testing

After code changes:

1. run relevant focused tests first
2. run the existing Python suite when feasible
3. run migration/provider contract tests for memory changes
4. run Playwright/Tauri smoke or E2E tests for UI work
5. test Qdrant available and unavailable modes
6. test production/acceptance isolation
7. test with compatibility runtime disabled before retirement claims

Never delete tests, reduce assertions, hide failures or report unexecuted tests as passed.

## 14. Documentation and Delivery

Each substantial task must update the relevant documents:

- architecture or module plan
- code map when entry points change
- project status
- changelog or test report
- migration matrix when compatibility behavior changes

Final task output must distinguish:

- implemented and tested
- implemented but not locally tested
- planned only
- compatibility-only behavior
- known blockers
