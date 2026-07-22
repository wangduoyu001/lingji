# P2-10C Memory Workspace UI

## Goal

Turn LingJi's memory-facing pages from API-shaped administration screens into a coherent desktop memory workspace.

This phase refines four owner-facing flows:

```text
人工记忆审核
Auto Review SHADOW
记忆检查器
项目与对话
```

It does not change backend authority, API behavior, database schema or memory lifecycle rules.

## Design principles

### Owner authority stays visible

The interface must make it obvious that:

- AI proposes memory changes;
- Auto Review only explains and scores;
- the owner is the only actor who approves, edits, rejects, archives or manually creates long-term memory.

### Evidence before action

Potentially destructive or durable actions appear only after the owner can see:

- source Session;
- source Message;
- proposal reason;
- similar Core Memory;
- affected Agents;
- content hash;
- edited content;
- required reject reason.

### Desktop workbench, not browser tables

The core pages use stable desktop workbench patterns:

```text
queue / list
selected detail
facts and provenance
sticky or grouped actions
empty-state guidance
```

Large tables are not used as the primary interaction model for memory review.

## Artificial Memory Review

`MemoryReviewPage.tsx` is organized as:

```text
Owner authority hero
Candidate inbox and filters
Selected candidate detail
Provenance and similarity
Editable memory content
Approve / edit-approve / reject action dock
Manual Core Memory creation
Core Memory integrity and archive tools
```

The existing optimistic content-hash contract remains unchanged.

The following behavior is preserved:

- `expected_content_hash` is sent through the API layer;
- stale candidate changes return conflict guidance;
- rejection requires a reason;
- archive does not physically delete the file;
- manual creation remains owner-confirmed.

## Auto Review SHADOW

`AutoReviewPage.tsx` is now a shadow decision workspace rather than a raw decision table.

It contains:

```text
Mode and safety posture
Decision inbox
Selected explanation
Rule and evidence list
Local AI summary
Owner feedback
Read-only candidate evaluation
```

Safety boundaries remain unchanged:

- `ACTIVE` is unsupported;
- mutation count should remain zero;
- no approve, reject, delete, execute or active endpoints exist in the Desktop page;
- the page cannot mutate long-term memory.

## Codex Project and Session Workspace

`CodexWorkspacePage.tsx` now uses a three-part desktop workspace:

```text
Project rail
Session browser
Selected Session detail
```

Below that, the owner sees:

```text
Live activity timeline
Context Pack builder
```

Session detail intentionally shows structured summaries rather than full conversation transcripts.

The Context Pack builder preserves:

- project and optional Session scope;
- task query;
- character budget;
- copy-to-clipboard behavior;
- Memory Inspector shortcuts.

## Memory Inspector

The Memory Inspector keeps its existing source -> conversation -> message -> memory model.

This phase refines its visual behavior:

- truthful status cards;
- dedicated filter surface;
- clearer three-column evidence browser;
- stronger active and restricted states;
- desktop detail drawer;
- readable message, memory, citation and vector metadata.

No inspector query or mapping contract is changed.

## Shared visual system

`LocalMemoryLoop.css` now contains reusable memory workspace patterns:

```text
workspace hero
workspace counters
panel headings
candidate and Session cards
selected states
fact grids
provenance blocks
action docks
project rail
activity timeline
Context Pack result
Auto Review decision cards
```

`MemoryInspectorPage.css` owns the evidence-browser and detail-drawer presentation.

The implementation reuses the P2-10B global Desktop variables and does not add another component library.

## Changed files

```text
desktop/lingji-control/src/pages/MemoryReviewPage.tsx
desktop/lingji-control/src/pages/CodexWorkspacePage.tsx
desktop/lingji-control/src/pages/AutoReviewPage.tsx
desktop/lingji-control/src/pages/LocalMemoryLoop.css
desktop/lingji-control/src/pages/MemoryInspectorPage.css
desktop/lingji-control/scripts/memory-workspace-ui-smoke.mjs
desktop/lingji-control/scripts/run-smoke-suite.mjs
```

## Architecture guarantees

Unchanged:

```text
Desktop -> authenticated 8766 API only
No direct SQLite access
No direct Qdrant access
No direct Ollama access
No database schema changes
No new settings store
No new credentials store
No second_brain changes
Auto Review remains OFF / SHADOW
Owner remains the only memory mutation authority
```

## Out of scope

This phase does not:

- change memory review API semantics;
- add automatic approval;
- add automatic rejection;
- add permanent deletion;
- redesign ingestion, models, storage or settings pages;
- package or install the Windows application;
- modify backend memory data.
