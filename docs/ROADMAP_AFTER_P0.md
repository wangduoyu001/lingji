# LingJi Roadmap After P0

> Updated: 2026-07-21  
> Formal Branch: `feature/second-brain-memory`  
> Current Gate: P0 Engineering Hygiene must pass before P2-05 starts.  
> Scope Decision: no system listener, clipboard listener, folder listener, mobile share client, or browser extension in the current roadmap.

## 1. Current Position

Completed and merged:

- P0 Workspace/Port Contract
- P1 Unified Semantic Memory
- P2-01 Vector Center
- P2-02 Collection Migration
- P2-03 Structured Read Model
- P2-03B Structured Ingestion Wiring
- P2-03C Capture Sources Foundation
- P2-04 Memory Inspector Desktop UI

Current blocking work:

- P0 Engineering Hygiene final Windows validation
- portable paths
- reproducible dependency baselines
- startup contract tests
- complete repository test baseline

## 2. Remaining Product Stages

### Stage A: P2-05 Manual Capture Center

Goal:

- submit text, web content, supported files, ChatGPT exports, Codex reports, and media manually
- persist jobs through the existing extraction queue
- expose progress, retry, cancel, pause, resume, and result references
- jump from completed jobs to Memory Inspector

Parallel workstreams:

1. Capture Control API
2. Manual Import Wiring
3. Desktop Capture Center UI
4. Integration and validation after the three implementation branches stabilize

Recommended concurrent writers: 3  
Maximum team size including validator: 4

### Stage B: Obsidian CLI Formal Migration

Goal:

- move configuration, discovery, models, client, and service into `src/obsidian/`
- expose status and safe operations through Local Control API
- add Desktop settings and status UI
- stop new production behavior from being added to `second_brain/`

Recommended concurrent writers: 2 to 3  
Maximum team size including validator: 4

Suggested split:

1. discovery/config/client
2. service/API/runtime settings
3. Desktop status/settings and migration tests

### Stage C: Schema v2 and Evidence Layer

Goal:

- stable evidence identity
- provenance and citation contracts
- revision lineage
- schema migration and rebuild contracts
- Inspector support for evidence, revisions, and conflicts

This stage has high shared-schema risk.

Recommended concurrent writers: 2  
Maximum team size including fixtures/validator: 3

Suggested split:

1. schema/migration/read model
2. gateway/API/Inspector contracts
3. test fixtures and migration validation only

### Stage D: Knowledge Update, Revision, Conflict, and Owner Review

Goal:

- generate update candidates without silently modifying permanent knowledge
- compare old and new evidence
- show revisions and conflicts
- support owner accept, edit, merge, reject, and defer actions

Recommended concurrent writers: 3  
Maximum team size including validator: 4

Suggested split:

1. candidate and revision service
2. conflict policy and owner-review API
3. Desktop review UI

### Stage E: Retrieval Evaluation and Relationship Expansion

Goal:

- establish a repeatable retrieval benchmark
- compare lexical, semantic, hybrid, and relationship-expanded results
- add explanations and quality metrics
- only add relationship expansion after measurable benefit

Recommended concurrent writers: 2  
Maximum team size including evaluator: 3

### Stage F: Project Memory and Relationship Views

Goal:

- show relationships between projects, files, conversations, memories, decisions, people, and tasks
- provide project-level context packs and project history
- keep Obsidian as the editable knowledge authority

Recommended concurrent writers: 3  
Maximum team size including validator: 4

### Stage G: Active Second Brain

Goal:

- daily and weekly briefs
- forgotten-task and risk reminders
- project-change summaries
- opportunity discovery
- recommendation explanations and owner controls

Recommended concurrent writers: 3 to 4  
Maximum team size: 5, only when notification, ranking, UI, and evaluation ownership are isolated

### Stage H: Production Cutover and Compatibility Retirement

Goal:

- production embedding-model decision
- controlled vector rebuild and validation
- backup and rollback drill
- migrate remaining approved compatibility behavior into `src/`
- stop `second_brain/` writes and retire it gradually

Recommended concurrent writers: 2  
Maximum team size including migration validator: 3

## 3. Effective Concurrency Rules

The repository should not run more than four active implementation engineers during core-platform work.

Typical safe model:

- 3 implementation engineers on isolated file ownership
- 1 integration and validation engineer after stable branch commits exist
- remote architecture, review, documentation, and branch governance handled separately

Five engineers are only reasonable when at least two workstreams are isolated adapters, evaluation, documentation, or test infrastructure.

More than five active writers is not recommended because the following files and contracts are shared hotspots:

- `src/control/api.py`
- `src/control/service.py`
- `src/control/runtime_settings.py`
- `src/config.py`
- `src/extraction/queue.py`
- schema and migration files
- Desktop navigation, API types, and common contracts
- `docs/PROJECT_STATUS.md`
- `docs/MODULES/CODE_MAP.md`

## 4. Branch and Integration Rules

1. Every parallel stage starts from one verified base commit.
2. Shared files have one declared owner per stage.
3. Implementation branches do not merge one another.
4. Shared status documents are updated only by the integration branch.
5. No rebase or force push during coordinated development.
6. Each large task includes implementation documentation and a test report.
7. A stage is merged only after targeted tests, build gates, and integration tests pass.
8. Full-suite failures must be classified precisely; environment-specific failures cannot be described as an all-green run.

## 5. Rough Completion Estimate

Relative to the complete Personal Memory OS vision:

- storage, workspace, retrieval, vector, read model, and inspector foundation: substantially complete
- practical manual-ingestion and owner-review loop: not complete
- evidence, revision, conflict, and knowledge-maintenance loop: not complete
- project relationship and active recommendation loop: not complete
- production cutover and compatibility retirement: not complete

Estimated current completion:

- core memory-platform foundation: 65 to 75 percent
- usable second-brain MVP: 40 to 50 percent
- full long-term Personal Memory OS vision: 25 to 35 percent

These percentages are planning estimates, not test metrics.

## 6. Immediate Sequence

```text
P0 Windows final gate
-> merge P0
-> move P2-05 branches to the verified base
-> run three P2-05 implementation branches in parallel
-> integration review and test
-> formal merge
-> Obsidian CLI formal migration
-> Evidence Layer and owner-review loop
```
