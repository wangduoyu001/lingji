# ARCHITECTURE.md — LingJi Unified Architecture

> Updated: 2026-08-16
> Status: Active architecture contract
> Formal branch: `master`
> Primary authority: this file
> Historical migration detail: `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 1. Product Definition

LingJi is the owner's **second permanent memory brain** and an **active local intelligent assistant**.

Product definition:

> **LingJi = 我的第二永久记忆大脑 + 主动型本地智能助手。**  
> 它长期、可追溯地保存和组织我的数字记忆，同时持续观察我的数字工作环境，主动完成信息收集、整理、关联、检索和决策准备；能安全自动完成的事情自己完成，只有必须由我决定时才打扰我。

This definition has two equally important responsibilities and neither may be reduced to a secondary feature:

1. **Permanent second brain**
   - preserve durable owner memory across individual AI products, models, sessions and devices;
   - keep permanent memory owner-controlled, inspectable, editable, forgettable, portable and source-traceable;
   - distinguish raw source material, working memory and approved permanent/core memory;
   - allow the owner to see what LingJi remembers, why it believes it, where it came from, what conflicts with it and what important information is still missing;
   - use Obsidian Vault + Git history as the permanent-memory and formal-knowledge authority.

2. **Active local assistant**
   - continuously observe approved local digital work environments and connected sources;
   - discover relevant changes without requiring the owner to manually hunt through configuration pages;
   - classify what can be handled automatically, retried, observed, ignored or escalated;
   - perform safe and reversible work automatically;
   - preserve evidence of what was discovered, decided, done and verified;
   - interrupt the owner only for permissions, privacy boundaries, conflicts, irreversible actions or decisions that cannot be made safely.

The primary owner-facing loop is:

```text
Discover
  -> Understand
  -> Decide
  -> Act
  -> Verify
  -> Remember
  -> Brief
```

Every owner-facing state should be explainable in plain language through six questions:

```text
发现了什么？
判断了什么？
做了什么？
记住了什么？
接下来会做什么？
是否需要我？
```

The repository contains compatibility code during migration, but it must not evolve into multiple long-term products.

## 2. Long-Term Ownership

```text
src/
= long-term platform mainline
= capture, extraction, memory gateway, retrieval, MCP, control API, tasks and operations

second_brain/
= compatibility and migration runtime only
= no new primary product features

desktop/lingji-control/
= only primary desktop UI

second_brain/desktop/
= compatibility, acceptance and emergency diagnosis only
```

New memory features, capture contracts, adapters and primary UI pages must be developed in `src/` and `desktop/lingji-control/`, not duplicated in `second_brain/`.

## 3. Data Authority

```text
Permanent memory and formal knowledge text
= Obsidian Vault + Git history

Original imported material
= configurable storage/raw archive

Runtime jobs, processing state and audit events
= lingji_state.db

Rebuildable lexical and metadata index
= lingji_memory.db

Rebuildable semantic index
= Qdrant

Structured source/conversation/message queries
= rebuildable derived read model
```

SQLite indexes, Qdrant and the Structured Read Model are derived, rebuildable data. They are not independent permanent-memory authorities.

`second_brain.sqlite3` remains compatibility data during migration and must not become a second source of truth.

Permanent memory must remain inspectable and attributable. A permanent memory item must be able to expose, when available:

- remembered content
- memory class/type
- source evidence
- confidence or verification state
- created/updated time
- related project/topic/entity
- conflicts or superseding memory
- owner correction / forget history

No derived index may become the only place where an owner's permanent memory exists.

## 4. Current Verified Runtime

```text
Input Sources
  -> src/capture contracts
  -> src/extraction adapters
  -> persistent SQLite extraction queue
  -> raw snapshot
  -> Vault source documents
  -> Structured Read Model
  -> lexical and semantic indexing

Obsidian Vault + Git
  -> lingji_memory.db
       -> FTS5 / BM25 / trigram / metadata
  -> Qdrant SemanticProvider
       -> semantic chunks
  -> HybridRetriever
       -> RRF and metadata weighting
       -> privacy, project, tag, time and Agent Scope
  -> ContextPackBuilder
  -> Unified MemoryGateway
       -> MCP
       -> Local Control API
       -> internal jobs

Tauri Desktop
  -> authenticated Local Control API :8766
```

The following are implemented and focused-tested:

- unified semantic provider wiring in `src`
- Qdrant-backed semantic retrieval with lexical degradation
- Source/Conversation/Message Structured Read Model
- structured ingestion wiring
- Capture foundation contracts
- Memory Inspector Local Control API and Desktop UI

## 5. Retrieval Contract

```text
FTS5 / BM25 / Chinese substring fallback
+
Qdrant semantic search
+
metadata, privacy, time and Agent Scope filters
+
RRF and existing boosts
=
One retrieval pipeline
```

Qdrant failure must not disable lexical retrieval. Unknown vector state must not be fabricated as success or zero.

## 6. Port Contract

```text
8766 = Local Control API and Tauri gateway
8767 = optional MCP Streamable HTTP
stdio = default local MCP transport
8765 = compatibility API only during migration
```

Rules:

- Tauri must use `8766`.
- New product APIs must be added to the Local Control API, not the compatibility API.
- `8765` must not receive new primary product responsibilities.

## 7. UI Architecture

The final primary UI is `desktop/lingji-control/`.

The primary UI is not a system-monitor dashboard. It is the owner's **briefing, memory and action workspace** for the second permanent brain.

The primary daily navigation should converge on these owner concepts:

```text
首页 / Briefing
记忆 / Memory
工作 / Work
需要我 / Attention
高级 / Advanced
```

The daily UI must prioritize, in this order:

1. whether the owner needs to do anything now;
2. what LingJi actually discovered and completed;
3. what LingJi is currently doing;
4. what LingJi will do next;
5. what changed in permanent/working memory;
6. what remains uncertain, conflicted or missing.

The UI must expose truthful read models for:

- owner briefing and attention
- discovered sources and changes
- real work items and execution evidence
- memory browsing and natural-language retrieval
- memory source/evidence inspection
- memory gaps and conflicts
- manual Capture when the owner chooses to add information
- knowledge and Obsidian indexing
- tasks and structured progress
- AI clients and permissions
- opportunity/decision preparation
- advanced vector, model, CPU/GPU, storage, backup, logs and diagnostics

Technical implementation state such as ports, PID, Qdrant, SQLite, embedding dimensions and raw queue internals belongs in Advanced unless it directly degrades an owner-facing capability. In daily UI, technical degradation must be translated into capability language, for example:

```text
语义检索暂不可用，已自动降级为全文检索
```

instead of requiring the owner to understand Qdrant or embedding internals.

### 7.1 Truthful Workbench Projection

The UI must not infer owner-facing actions from unrelated summary counters. A daily workbench projection must be backed by real objects and evidence.

Each owner-facing work item should carry, when applicable:

```text
object_id
source / provenance
discovered_at
what_it_is
why_it_matters
decision
what_was_done
result
current_stage
next_action
next_actor
owner_action_required
owner_action_id
evidence_id
```

No real `owner_action_id` means no clickable "去处理" action may be shown.

### 7.2 Memory Transparency

Memory is a primary product surface, not an advanced diagnostic page.

The owner must be able to:

- browse what LingJi remembers;
- search or ask what LingJi remembers;
- inspect source evidence;
- see confidence/verification state;
- edit or correct a memory;
- forget a memory through the governed permanent-memory path;
- see conflicts and superseded facts;
- see memory gaps that LingJi can justify with evidence.

A knowledge graph may be added later as a secondary visualization, but it must not replace searchable lists, evidence or source inspection.

### 7.3 Active Source Discovery

Approved-source discovery should prefer:

```text
scan safe metadata
-> identify source/tool
-> determine safe automatic capability
-> automatically ingest permitted low-risk metadata/state
-> request permission only before crossing content/privacy/irreversible boundaries
```

Do not require the owner to configure a source manually when LingJi can safely discover and explain it automatically.

PySide6 may remain during migration for acceptance and diagnosis, but it must not receive new competing product features.

## 8. Workspace and Path Contract

Production and acceptance must physically isolate:

- Vault or fixture Vault
- raw archive
- state database
- memory index database
- Qdrant collection or path
- logs
- generated assets
- runtime settings
- backup destination

Path rules:

1. No machine-specific absolute path may be a production default.
2. Paths must derive from Workspace, Runtime Settings, environment detection or explicit owner selection.
3. Environment detection may propose a path but must not silently make it permanent authority.
4. A request header alone does not provide physical isolation.

## 9. Dependency and Test Contract

Before new product stages depend on a package or startup entry:

- dependency ownership must be explicit
- versions must be reproducible
- clean-environment installation must be validated
- startup tests must verify behavior, not compare whole files byte-for-byte
