# LingJi Unified Desktop UI Plan

Status: Required product architecture
Updated: 2026-07-20
Primary UI: `desktop/lingji-control/`
Architecture: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Final Decision

LingJi ships with one primary desktop application: the Tauri / React application under `desktop/lingji-control/`.

Previous local UI implementations and `second_brain/desktop/` are migration, acceptance, compatibility and diagnostic references. Their useful functions and interaction patterns must be audited and migrated into Tauri. They must not continue as competing primary products.

## 2. Correct Runtime Chain

```text
Tauri / React Desktop
  -> authenticated Local Control API :8766
  -> src platform services
       -> Unified MemoryGateway
       -> extraction and task services
       -> model and hardware services
       -> storage and backup services
       -> opportunity services
  -> Obsidian/Git authority
  -> lingji_memory.db + Qdrant indexes
```

Tauri must not call the compatibility `second_brain` API on `8765` directly.

## 3. Product Requirement

The desktop UI is the visible control surface of the entire private second brain, not a launcher.

The owner must be able to see:

- every major capability
- every supported user setting
- current and historical task progress
- memory and knowledge state
- source and conversation provenance
- whether vectors exist and are healthy
- active embedding and language models
- CPU/GPU execution state when confirmed
- AI clients, permissions and MCP state
- workspace and storage paths
- errors, degraded states, backup and recovery

No important safe backend capability may remain permanently hidden behind scripts.

## 4. Single UI Rules

- `desktop/lingji-control/` is the only primary UI.
- `second_brain/desktop/` is frozen for acceptance, migration and diagnosis.
- new user-facing pages are added only to Tauri.
- duplicate pages are consolidated, not maintained independently.
- old UI code is a capability source, not the final visual design.
- all Tauri data comes through authenticated `8766` contracts.

## 5. Required Navigation

### 5.1 Overview

Show one truthful system summary:

- workspace
- Local Control API
- Unified MemoryGateway
- Vault and Git state
- lexical index state and memory revision
- Qdrant readiness and vector counts
- active embedding model
- extraction queue and running tasks
- watcher and scheduler state
- model/Ollama state
- CPU/GPU state
- storage usage
- backup and integrity state
- recent warnings and failures

Do not show a generic green state when individual services have not been checked.

### 5.2 Memory Inspector

Show:

- canonical memory list and filters
- detail, metadata and citation lines
- source and provenance
- lifecycle and owner-review state
- revisions, relations and conflict candidates
- lexical index state
- per-memory and per-chunk vector existence
- current retrieval trace
- lexical and semantic channels
- semantic similarity, RRF and final retrieval score
- project, privacy, time and Agent Scope decisions
- embedding model and Qdrant warnings

Version 1 is read-only.

### 5.3 Knowledge and Obsidian

Show:

- Vault path and Git state
- indexed documents and chunks
- lexical and vector index state
- last indexed revision and time
- failed files and reasons
- safe refresh and dry-run operations
- relationships and project links

Obsidian formal knowledge must not be silently promoted into personal memory.

### 5.4 Sources and Conversations

Show all supported input types:

- AI chats
- Codex tasks
- web/social capture
- uploaded documents
- audio/video/media
- Obsidian knowledge
- future approved adapters

For each source show:

- enabled/configured state
- account or path without exposing secrets
- raw snapshot/provenance
- queue and processing state
- imported conversations/messages when available
- last scan and last success
- failures and retries

### 5.5 Tasks and Progress Center

Every long-running operation must publish structured progress:

- task name and ID
- stage
- measurable percentage
- processed/total
- successes and failures
- current item
- start and elapsed time
- retry state
- latest structured message
- cancellation or pause support when safe

Plain log scraping is not a permanent progress API.

### 5.6 Vector Center

The vector system must be visible enough that the owner can confirm it exists and is working.

Show:

- Qdrant mode and endpoint/path
- workspace and collection
- connection and readiness
- vector dimension
- configured, fallback and active embedding models
- total vectors and counts by kind
- missing expected vectors
- orphan vectors when detectable
- last write, query and rebuild
- dimension mismatch and rebuild-required state
- last error
- per-memory and per-document point existence

Qdrant is a rebuildable index. Obsidian/Git and raw sources remain authoritative.

### 5.7 Models and Compute

Show:

- installed local models
- model purpose and size
- RAM/VRAM requirements
- current-machine compatibility
- active and fallback models
- Ollama state
- CPU/GPU execution state
- cloud providers and configuration status without secrets
- official provider console links where appropriate

GPU acceleration must be displayed as confirmed enabled, disabled, unavailable or unknown.

### 5.8 AI Clients and Memory Access

Show:

- registered AI profiles
- allowed tools
- privacy access
- Agent Scope
- maximum context budget
- ability to propose memory
- local-only restrictions
- MCP transport and health
- recent context-pack and memory-access events when available

All AI clients use the same MemoryGateway, not separate memory copies.

### 5.9 Opportunity Center

Expose the retained opportunity system through unified task and data services:

- opportunities and source material
- analysis status and score
- owner feedback
- accepted/rejected/pending state
- processing history

Do not maintain a separate opportunity dashboard runtime.

### 5.10 Storage, Backup and Recovery

Show:

- Vault, raw, state DB, memory DB and Qdrant locations
- free space and category usage
- backup state and last success
- restore points
- integrity results
- production/acceptance separation

Runtime data must not be silently written to the C: drive.

### 5.11 Settings

All supported settings must be discoverable in normal or advanced views:

- workspace
- storage and Vault paths
- source/adapters
- queue, watcher and scheduler settings
- model and embedding selection
- Qdrant mode, path, URL and collection
- MCP transport and target port
- API providers
- GPU preference
- privacy and indexing boundaries
- backup and retention
- log level and startup behavior

Validate settings before saving and display restart/rebuild requirements.

### 5.12 Logs and Diagnostics

Show:

- structured application and task logs
- recent errors and warnings
- API, database, Qdrant and embedding health
- watcher, scheduler and queue health
- integrity state
- exportable diagnostic report

## 6. Persistent Global Status

Recommended always-visible indicators:

```text
Workspace | API | Memory | Lexical Index | Qdrant | Embedding | Tasks | GPU | Storage
```

Each indicator uses explicit states:

- healthy
- busy
- degraded
- unavailable
- disabled
- configuration required
- unknown

Unknown is preferable to fabricated success or zero.

## 7. Previous UI Migration Matrix

Before retiring any previous UI, record:

| Field | Meaning |
|---|---|
| Existing path | real repository or local path |
| Function | actual behavior |
| Backend dependency | API, file, process or database |
| Tauri destination | existing or planned page |
| Decision | migrate / merge / redesign / retire |
| Missing contract | required API or progress data |
| Acceptance test | parity verification |

Do not copy visual code blindly. Migrate capabilities into one Tauri design system.

## 8. Backend Visibility Contract

Backend services must expose truthful read models for:

- overview and health
- task progress
- memory and knowledge statistics
- lexical and vector indexes
- model and compute state
- source and ingestion state
- storage and backup
- watcher and scheduler
- AI profiles and MCP

Brain Status, Memory Inspector, Vector Center and MCP must use shared statistic sources.

## 9. Development Order

1. finish UI capability audit and migration matrix
2. define shared health, task, vector, model and settings contracts
3. connect Qdrant as the unified `src` SemanticProvider
4. fix Brain Status to use real unified statistics
5. implement Memory Inspector through `8766`
6. implement Vector Center and per-item point state
7. migrate source/conversation views
8. migrate remaining useful local/PySide flows
9. run Playwright/Tauri and backend contract tests
10. freeze and later retire duplicate UI paths after parity

## 10. Acceptance

The UI plan is complete only when:

- one desktop app exposes all formal capabilities
- settings and progress are discoverable
- vector existence and state are visible
- all AI memory access routes to one gateway
- no page depends on the compatibility database as permanent truth
- values are backend-confirmed
- previous UI capabilities have explicit migrate/retire decisions
- compatibility UI can be disabled without losing primary product functionality
