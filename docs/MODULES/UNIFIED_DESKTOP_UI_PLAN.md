# LingJi Unified Desktop UI Plan

Status: Required Architecture
Module: Tauri Desktop + Local Control API
Updated: 2026-07-20

## 1. Final Decision

LingJi must ship with one primary desktop application.

The final primary UI is the current Tauri / React application under:

`desktop/lingji-control/`

The previously developed local UI and the PySide6 desktop are reference and acceptance implementations only. Their useful functions, page structure, interaction ideas and status displays must be audited and migrated into the current Tauri application. They must not continue evolving as separate primary products.

Final runtime chain:

```text
Tauri / React Desktop
  -> Local Control API (127.0.0.1:8766)
  -> LingJi services and Second Brain runtime
  -> SQLite / Qdrant / Ollama / Obsidian / task services
```

The Tauri application must not call port `8765` directly. The Local Control API remains the single desktop gateway.

## 2. Product Requirement

The desktop UI is not only a launcher. It must make the entire LingJi system visible and controllable.

The user must be able to see:

1. Every major capability.
2. Every user-configurable setting.
3. Current and historical task progress.
4. Current system health and errors.
5. Memory and knowledge state.
6. Whether vectors exist.
7. Qdrant collection state and vector counts.
8. Which embedding model is active.
9. Whether local GPU or CPU is being used.
10. Which workspace and storage paths are active.

No important backend capability may remain permanently hidden behind scripts when a safe UI representation is possible.

## 3. Single UI Rule

Do not create another dashboard or desktop application.

- `desktop/lingji-control/` is the only primary UI.
- `second_brain/desktop/` PySide6 remains for acceptance, compatibility and emergency diagnosis.
- Previous local UI code is a migration source, not a second product.
- New features must be added to the Tauri navigation unless they are explicitly developer-only.
- Duplicate pages must be consolidated rather than maintained independently.

## 4. Required Navigation

The final Tauri navigation must expose the following product areas.

### 4.1 Overview

Show one-page system state:

- LingJi service state
- Second Brain state
- current workspace
- memory count by lifecycle status
- knowledge document count
- vector count by kind
- active embedding model
- Qdrant readiness
- running tasks
- failed tasks
- watcher state
- scheduler state
- storage usage
- latest backup
- recent warnings

### 4.2 Memory Inspector

Show:

- memory list and filters
- memory detail
- source metadata
- lifecycle status
- versions and supersede relations
- conflicts
- per-memory vector existence
- retrieval trace
- exact-match fields
- vector similarity
- ranking score
- project match or global fallback
- embedding model used
- Qdrant participation and warnings

The first version remains strictly read-only.

### 4.3 Knowledge and Obsidian

Show:

- indexed Obsidian documents
- indexing state
- source path
- chunk count
- vector state
- last indexed time
- failed files
- manual refresh and safe dry-run actions

Obsidian content must not be auto-distilled into memories.

### 4.4 Sources and Active Feeding

Show all supported input sources:

- AI chat imports
- Codex task imports
- Obsidian knowledge
- uploaded files
- future social-media and media connectors

For every source show:

- enabled state
- configured path or account
- last scan
- queued items
- processed items
- failures
- current progress

### 4.5 Tasks and Progress Center

Every long-running operation must publish visible progress.

Required fields:

- task name
- task ID
- current stage
- percentage when measurable
- processed / total items
- success count
- failure count
- start time
- elapsed time
- estimated remaining work only when the backend has real data
- current file or entity
- latest log message
- retry state

Safe actions may include pause, resume, retry and cancel. Destructive actions require explicit confirmation.

### 4.6 Vector Center

The user must be able to feel that vector indexing exists and is working.

Show at minimum:

- Qdrant mode: embedded / remote / in-memory
- connection state
- collection name
- collection readiness
- vector dimension
- active embedding model
- fallback embedding model
- total vector count
- memory vector count
- knowledge chunk vector count
- vectors missing for active memories
- orphan vectors when detectable
- latest vector write time
- latest query time
- latest rebuild or incremental sync
- dimension mismatch or rebuild-required warning
- production / acceptance workspace distinction

Per-memory and per-document views must show whether a corresponding vector point exists.

Qdrant remains rebuildable. SQLite and raw data remain authoritative.

### 4.7 Models and Compute

Show:

- local models installed
- model purpose
- model size
- required RAM / VRAM
- compatibility with the current computer
- CPU / GPU execution state
- active model
- fallback model
- Ollama state
- cloud API providers
- API configuration status without exposing secrets
- direct links to official API consoles where appropriate

GPU acceleration must have a clear enabled, disabled or unavailable state. The UI must not pretend acceleration is active when the backend cannot confirm it.

### 4.8 Opportunity Center

Expose the retained LingJi opportunity-analysis capability:

- discovered opportunities
- source material
- analysis status
- score and ranking
- user feedback
- accepted / rejected / pending state
- processing history

This must use the unified data and task services rather than a separate dashboard.

### 4.9 Storage, Backup and Recovery

Show:

- configured storage roots
- database path
- Qdrant path or URL
- archive path
- Obsidian path
- free space
- storage usage by category
- backup state
- last successful backup
- restore points
- integrity-check result

Runtime data must never be silently written to C: drive.

### 4.10 Settings

Every supported configuration must have a discoverable UI entry or a clearly labeled advanced configuration view.

Settings include:

- workspace
- storage paths
- source paths
- watcher intervals
- scheduler jobs
- model selection
- embedding model
- Qdrant mode and location
- API providers
- GPU preference
- privacy and indexing boundaries
- backup behavior
- log level
- startup behavior

Settings must be validated before saving and must show restart requirements.

### 4.11 Logs and Diagnostics

Show:

- structured application logs
- task logs
- recent errors
- service health
- API connectivity
- database integrity
- Qdrant health
- embedding health
- watcher health
- scheduler health
- exportable diagnostic report

## 5. Global Status Surface

The desktop shell must keep critical state visible without requiring navigation into multiple pages.

Recommended persistent indicators:

```text
Workspace | API | SQLite | Qdrant | Embedding | Watcher | Tasks | GPU | Storage
```

Each indicator must have explicit states such as:

- healthy
- busy
- degraded
- unavailable
- disabled
- configuration required

Do not use a generic green light when the underlying service has not been checked.

## 6. Previous Local UI Migration

Before removing or freezing the previous local UI, perform a page and capability audit.

For every previous page or component record:

| Field | Meaning |
|---|---|
| Existing path | Real local or repository path |
| Function | What the page actually does |
| Backend dependency | API, file, process or database used |
| Current Tauri equivalent | Existing destination page |
| Decision | migrate / merge / redesign / retire |
| Missing backend contract | API or progress data still required |
| Acceptance test | How parity will be verified |

Do not copy visual code blindly. Migrate useful capabilities and validated interaction patterns into the current Tauri design system.

## 7. Backend Visibility Contract

The UI cannot invent status or progress. Backend services must expose truthful read models for:

- system overview
- service health
- task progress
- memory statistics
- vector statistics
- model state
- storage state
- watcher state
- scheduler state
- backup state

All major long-running tasks must publish structured progress events. Plain log scraping is not an acceptable permanent progress API.

## 8. Development Order

1. Audit the previous local UI and current Tauri pages.
2. Produce a migration matrix.
3. Define shared status, progress, vector and settings contracts.
4. Fix the current `memory_stats` aggregation gap.
5. Implement Memory Inspector through the unified control API.
6. Implement the Vector Center and per-item vector existence views.
7. Implement the global task and progress center.
8. Consolidate settings into the Tauri application.
9. Migrate useful remaining functions from previous UI implementations.
10. Run Playwright and native desktop acceptance tests.
11. Freeze and later remove duplicate primary UI paths only after parity is proven.

## 9. Acceptance Criteria

The unified UI is accepted only when:

- one primary Tauri desktop application exposes all major LingJi capabilities
- no major feature requires launching another desktop UI
- all user-facing settings are discoverable
- task progress is visible and truthful
- memory, source and retrieval behavior are inspectable
- vector existence is visible per memory or document where supported
- Qdrant collection and embedding state are visible
- production and acceptance workspaces are clearly distinguished
- failures and degraded states are visible instead of silently returning zero
- previous local UI functions are accounted for in a migration matrix
- duplicate UI implementations are no longer developed as primary products
- Playwright and desktop smoke tests pass

## 10. Out of Scope Until Visibility Exists

Do not prioritize decorative redesign, animation-heavy dashboards or additional desktop frameworks before the status, progress, settings and vector visibility contracts are complete.

The UI should first be truthful, complete and operable. Looking expensive while displaying fabricated zeros is not a feature.
