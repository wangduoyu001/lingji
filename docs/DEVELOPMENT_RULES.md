# DEVELOPMENT_RULES.md — LingJi Development Rules

> Updated: 2026-07-29
> Architecture authority: `docs/ARCHITECTURE.md`
> Current-state authority: `docs/PROJECT_STATUS.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. Branch and Environment Isolation

1. Current development branch: `master`.
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

## 4. Minimal Context Requirement

Before code changes, read only the smallest evidence set needed for the task:

1. confirm branch, upstream, recent commit and workspace status
2. read the relevant section of `docs/PROJECT_STATUS.md`
3. read the relevant module in `docs/MODULES/CODE_MAP.md`
4. read `docs/ACCEPTANCE/README.md` and the latest relevant entry in `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
5. inspect the directly affected workflow, build or test entry
6. locate the real class/function entry point, direct callers and focused tests
7. confirm data authority, API registration, storage boundary and primary/compatibility ownership

Do not repeatedly read all of `AGENTS.md`, `docs/PROJECT_STATUS.md`, `docs/ARCHITECTURE.md` or this file. Read the governing file once, keep a short execution-constraint summary, and use targeted keyword or section lookup when a later decision depends on a specific rule.

Do not perform an untargeted whole-repository scan. Do not create files based only on feature names or assumptions. Prefer current code maps and verified evidence, but re-check code when documents conflict.

## 5. Research Before Development

For design and development work:

1. understand the user requirement and current code
2. review relevant official documentation and reliable implementations when the technology is external or may have changed
3. define the change-specific automatic tests, real-machine tests, owner observations, regressions, cleanup and rollback in `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
4. produce a bounded implementation plan
5. implement with minimal, maintainable code
6. avoid repeated broad refactors
7. update an existing authoritative document or test report after a substantial tested change
8. update `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md` when user flow, runtime, install, data, connector, security or release behavior changes

A new Markdown file is allowed only when no existing authority can carry the information and the new file has a unique, durable responsibility. Do not create duplicate optimization summaries, final summaries, supplemental notes or renamed copies of existing documents.

## 5A. External Code License and Provenance Gate

Before adding any external package, copied implementation or generated adapter:

1. Record the exact package/repository, version or commit, license, source URL, transitive runtime impact and intended in-project boundary in the change plan.
2. Prefer official documentation and primary source repositories; preserve provenance in the implementation or acceptance evidence so a future rebuild can identify the source.
3. Reject code or dependencies with AGPL, GPL, SSPL, BSL, custom, unknown or incompatible licensing, and reject any component that introduces a second database, retriever, queue, API, UI, telemetry path, cloud control plane or permanent-memory authority.
4. For Phase 1 automatic memory, `watchfiles==1.2.0` is the only planned new watcher dependency and may be added only in Task 4 after its MIT license and provenance are recorded. Task 0 is documentation-only and must not modify dependency files.
5. Borrow patterns from Mem0/OpenMemory, Letta, Zep/Graphiti and LlamaIndex only as documented design references; do not import their product runtimes or schemas.

## 5B. Automatic Derived Memory versus Core Memory

Raw AI chats, snapshots, provenance and parsed records are evidence and rebuildable retrieval inputs. A low-risk, high-confidence (`>= 0.90`), conflict-free derived current-memory projection may activate automatically, but it is not formal permanent knowledge and must be reconstructible from evidence. Core Memory, identity, high-risk facts and formal permanent knowledge require explicit owner confirmation. `superseded`, `invalidated` and `archived` facts remain auditable with validity and replacement links but are excluded from current retrieval, ContextPack and MCP modes.

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
8765 = compatibility API during migration
```

Rules:

1. Tauri must call only the Local Control API on `8766`.
2. Do not add direct Tauri calls to `8765`.
3. New primary product APIs must not be added to the compatibility API.
4. Prefer stdio MCP for local Codex integration unless HTTP transport is explicitly required and tested.

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
10. Every changed page must be exercised in the real packaged Desktop; all visible controls require a real effect or an explicit unavailable state.

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
8. Replace an obsolete implementation or document instead of copying it into a new parallel path.

## 13. Testing

Run focused tests first. Use the repository validation entry instead of inventing parallel command sets:

```powershell
.\scripts\validate.ps1 -Mode focused -Area <area>
.\scripts\validate.ps1 -Mode full
.\scripts\validate.ps1 -Mode release
python scripts/check_acceptance_sync.py
```

- `focused` runs the mapped module tests during development.
- `full` runs the complete local merge gate once on the final tree.
- `release` adds Windows Sidecar/Tauri/NSIS build and release-artifact preparation; GitHub release CI and owner-machine installation remain the final release authority.
- `npm run build` is build-only; Desktop smoke is invoked explicitly.
- Also test Qdrant available/unavailable modes, production/acceptance isolation and compatibility-runtime-disabled behavior when the changed module depends on those contracts.
- Product-affecting changes must update `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`; the acceptance sync CI gate must fail otherwise.

Never delete tests, reduce assertions, hide failures, rerun unchanged full gates without cause, or report unexecuted tests as passed.

## 14. Acceptance Governance

1. `docs/ACCEPTANCE/README.md` is the durable acceptance authority.
2. `CODEX_ACCEPTANCE_INSTRUCTIONS.md` contains the common executable baseline for Codex.
3. `CHANGE_ACCEPTANCE_LOG.md` records the exact incremental acceptance required by every product-affecting change.
4. `REPORT_TEMPLATE.md` defines the final evidence format.
5. Every product-affecting PR must update `CHANGE_ACCEPTANCE_LOG.md` in the same PR.
6. A change to user flow, install, runtime, lifecycle, storage, API, MCP, connector, security or release behavior must also update `CODEX_ACCEPTANCE_INSTRUCTIONS.md`.
7. Chat messages and historical reports may not override the current acceptance authority.
8. Real-machine acceptance uses direct overwrite installation by default. Do not uninstall or delete owner data unless the task explicitly requires and authorizes it.
9. Old acceptance directories, duplicate artifacts, ordinary successful logs, screenshots, fixtures and temporary config copies are removed after the report is committed.
10. Product Head remains fixed once its Artifact is selected. Final acceptance reports are committed on a separate report branch.
11. Owner-only observations, including console-window behavior and first-time comprehension, cannot be self-certified by Codex.
12. A PR is not mergeable in practice merely because GitHub reports `mergeable=true`; required owner acceptance and report evidence must also pass.

## 15. Documentation and Delivery

One fact has one detailed authority:

- `docs/ARCHITECTURE.md`: stable architecture, boundaries and core data flow
- `docs/PROJECT_STATUS.md`: current stage, completion state, risks, blockers and next step
- `docs/CHANGELOG.md`: user-facing or release-significant changes
- `docs/ACCEPTANCE/`: current acceptance rules, executable instructions, change-specific requirements and report template
- `docs/TEST_REPORTS/`: commands, environment, results, limitations and validated commit
- `docs/MODULES/CODE_MAP.md`: code entry points, ownership and focused validation only; do not duplicate current status or CI history
- `docs/DEVELOPMENT_RULES.md`: durable development and governance rules

Update the existing authority instead of creating a parallel document. Historical module plans and implementation reports may remain as evidence but must not override the current architecture, project status or acceptance authority.

Final task output must distinguish:

- implemented and tested
- implemented but not locally tested
- planned only
- compatibility-only behavior
- known blockers
