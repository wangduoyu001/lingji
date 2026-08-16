# DEVELOPMENT_RULES.md — LingJi Development Rules

> Updated: 2026-08-16
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
11. Daily owner-facing UI must follow the active permanent-second-brain contract in Section 16; technical visibility requirements belong in Advanced unless they directly block owner capability.

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

## 16. Active Permanent-Second-Brain Product Contract

This section is the durable product-development contract for the next LingJi Desktop architecture.

### 16.1 Product Goal

LingJi must be developed as both:

1. **the owner's second permanent memory brain**; and
2. **an active local intelligent assistant**.

Neither role is optional. A build that only stores memory but waits for manual operation is incomplete. A build that automates work but cannot transparently preserve, retrieve and correct long-term owner memory is also incomplete.

The daily product promise is:

> 灵机长期记住我，并持续替我观察、整理和推进数字工作；它能自己安全完成的事情自己完成，只在必须由我决定时打扰我。

### 16.2 Active System Loop

All supported sources should converge on one owner-comprehensible loop:

```text
Discovery
  -> Understanding
  -> Decision
  -> Action
  -> Verification
  -> Memory
  -> Briefing
```

A discovery must not disappear into anonymous counters. Where evidence exists, the system must retain the causal chain from discovered object to decision, action, result and memory effect.

### 16.3 Decision Classes

Every automatically discovered item that needs handling should resolve to one of these decision classes:

```text
AUTO    = safe, reversible and permitted; execute automatically
RETRY   = transient failure; retry automatically within policy
OBSERVE = insufficient evidence; keep observing without interrupting owner
IGNORE  = duplicate, irrelevant or intentionally unsupported; record reason and stop
ASK     = permission, privacy, conflict, irreversible action or owner-only judgment required
```

Rules:

1. Only `ASK` may create a primary owner-interruption item.
2. Technical errors that can be retried or degraded safely are not owner decisions.
3. The reason for each non-trivial decision must be traceable to evidence or explicit policy.
4. A UI label may simplify the wording but may not change the underlying decision class.

### 16.4 Owner Work Item Contract

The daily UI must not derive owner truth from unrelated summary counts. The backend/projector should expose real work items carrying, when applicable:

```text
object_id
object_type
title
source
provenance
discovered_at
why_it_matters
decision_class
decision_reason
current_stage
what_was_done
result
next_action
next_actor
owner_action_required
owner_action_id
evidence_id
memory_effect
```

Rules:

1. No `owner_action_id` means no clickable owner action.
2. No evidence means the UI must not present a specific claim as confirmed fact.
3. `next_actor` must resolve to a human concept such as `LingJi`, `Owner`, `External system`, or `None/completed`.
4. Pagination controls must follow backend-confirmed `has_more`/cursor/total semantics. Frontend code may not invent another page merely because the current page is full.
5. If summary counts and object-level details disagree, show a consistency/degraded state rather than hiding the mismatch.

### 16.5 Daily Information Architecture

Primary navigation should converge toward:

```text
首页
记忆
工作
需要我
高级
```

The homepage is a briefing, not a monitoring dashboard. It should answer in this order:

1. **我现在需要做什么？**
2. **灵机刚刚替我做了什么？**
3. **灵机现在正在做什么？**
4. **接下来灵机会做什么？**
5. **记忆发生了什么变化？**
6. **有什么重要冲突、缺口或未知？**

Do not fill the homepage with technical statistics simply because they are available.

### 16.6 Memory Is a Primary Surface

Memory must not remain hidden as an advanced inspector.

The primary Memory experience must eventually support:

- natural-language memory query;
- browsable durable memories;
- project / decision / preference / fact / plan or equivalent human-readable grouping;
- source and evidence inspection;
- confidence / verification state;
- corrections and governed forgetting;
- superseded or conflicting memory;
- recent memory changes;
- justified memory gaps.

A graph view is optional and secondary. It does not substitute for browse/search/evidence.

### 16.7 Memory Layers

The product should distinguish at least these conceptual layers even if the physical storage implementation differs:

```text
Raw Source
= imported or observed evidence, provenance preserved

Working Memory
= temporary/project/task context that LingJi may update automatically under policy

Permanent/Core Memory
= durable owner knowledge, preferences, decisions and important facts governed by permanent-memory policy
```

The permanent-memory policy must remain consistent with the architecture authority and safety rules. Product UX may propose safer automation later, but it may not silently weaken the current permanent-memory approval boundary without an explicit architecture and acceptance change.

### 16.8 Memory Gap and Conflict Detection

The system should not make the owner manually guess what is missing.

Where evidence is sufficient, LingJi may surface:

- a decision with no recorded reason;
- a project with no current goal or completion criterion;
- conflicting owner preferences or project priorities;
- frequently repeated information that has not yet become durable memory;
- stale memory contradicted by newer evidence;
- a source that should contribute memory but has stopped syncing.

Each gap/conflict must explain why it was surfaced and what evidence supports it. Do not invent gaps from generic templates when there is no owner-specific evidence.

### 16.9 Active Source Discovery

For approved source classes, prefer this interaction:

```text
safe metadata scan
-> source/tool detection
-> capability judgment
-> safe automatic handling
-> permission only at the boundary where content/privacy/irreversible access begins
```

Rules:

1. No drive-wide scanning.
2. Discovery scopes must be explicit and safe.
3. Explain what was found and what LingJi can do with it.
4. Explain why authorization is needed before asking for it.
5. After an approved persistent permission, do not repeatedly ask for the same low-risk scope unless permission expires or the scope changes.
6. Connection state should be expressed in owner value terms, not only protocol/auth jargon.

### 16.10 Global Owner Input

Manual capture remains necessary, but it should not require the owner to understand internal module routing.

The product should converge on one obvious global input/command entry that can route intents such as:

```text
记住：……
查找：……
我为什么之前决定……？
把这份资料加入灵机
最近灵机自动做了什么？
```

Existing Capture Center contracts should be reused behind this experience rather than duplicated.

### 16.11 Work History, Not Raw Logs

The normal owner activity page should describe meaningful work history:

```text
发现了什么
为什么处理
采取了什么动作
结果是什么
是否影响记忆
下一步是什么
```

Raw logs remain Advanced diagnostics.

### 16.12 Capability-Oriented Degradation

Daily UI must describe degraded capabilities rather than internal implementation names where possible.

Prefer:

```text
语义检索暂不可用，已使用全文检索
```

instead of:

```text
Qdrant unavailable / embedding offline
```

Technical detail remains available under Advanced.

### 16.13 V4 Automatic Acceptance Before Owner-Machine Acceptance

A new real-machine M5 task must not be activated merely because the UI builds.

Before a new Artifact may be handed to the owner machine, the exact product SHA must automatically pass scenario-level acceptance covering at minimum:

1. no data / first-run state;
2. approved source discovered automatically;
3. source requiring permission;
4. new item discovered and automatically processed;
5. duplicate item ignored with reason;
6. transient failure retried automatically;
7. item that genuinely requires owner decision;
8. no real pending action -> no `去处理` control;
9. real pending action -> target page contains the exact object/action;
10. backend `has_more=false` -> no active next-page control;
11. summary/detail inconsistency -> explicit degraded/consistency state;
12. real execution trace visible for a selected work item;
13. memory created/updated state is traceable to source evidence;
14. memory browse/search can show what is actually remembered;
15. memory-empty state explains whether the system will continue automatically or needs the owner;
16. vector/semantic failure preserves lexical retrieval and reports capability degradation truthfully;
17. privacy projection removes secret/token/auth material, private absolute paths and raw content where the UI contract does not require them;
18. Mac and Windows package/build/runtime regressions remain green on the same product SHA.

Only after all automatic gates for the exact candidate SHA pass may `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` be switched to a new `ACTIVE` M5 task and new Mac/Windows Artifacts be selected.

Real-machine acceptance should then concentrate on things automation cannot fully prove: immediate comprehension, visual quality, actual local discovery, packaged behavior, window recovery, native lifecycle and physical production-data isolation.

### 16.14 Owner-Comprehension Exit Criterion

The V4 daily experience is not considered complete until a first-time owner can answer within roughly five seconds, without reading technical documentation:

```text
灵机刚刚做了什么？
灵机现在在做什么？
灵机接下来会做什么？
我现在需要做什么？
```

And from the primary Memory surface, the owner must be able to determine:

```text
灵机到底记住了什么？
这些记忆来自哪里？
哪些重要信息仍然缺失或冲突？
```

Passing API/build tests without satisfying this product comprehension contract is not sufficient for M5 acceptance.
