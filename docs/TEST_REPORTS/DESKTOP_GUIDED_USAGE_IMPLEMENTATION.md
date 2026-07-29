# P0-A Start Center Implementation Report

Status: `CODE_COMPLETE / STACKED_CI_VALIDATED / OWNER_UI_ACCEPTANCE_PENDING`

Parent pull request: `#60`

Implementation branch: `work/p0-a-start-center`

Base: `feature/unified-ai-memory-connectors@97a6ae217eb4063af2be1a579518c2c56fe2d44e`

## 1. Goal

Close the P0-A start-center gap without introducing another backend authority.

The installed Desktop must let a first-time owner answer:

1. Which Workspace is active?
2. Which Vault, sources, conversations, messages and memory layers exist?
3. Which AI clients and import sources are available?
4. What was imported recently?
5. What is the single recommended next action?
6. Which known issues are fixed, and which remain open?

## 2. Implementation

Modified or added:

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/components/StartCenterPanel.tsx
desktop/lingji-control/src/components/StartCenterPanel.css
desktop/lingji-control/scripts/guided-usage-smoke.mjs
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
docs/TEST_REPORTS/DESKTOP_GUIDED_USAGE_IMPLEMENTATION.md
```

`OverviewPage` remains the owner-facing start page. Detailed aggregation and routing logic is isolated in `StartCenterPanel` so the page does not become another oversized control component.

## 3. Data ownership

No database, queue, API or status authority was added.

The start center composes existing authenticated read-only contracts:

```text
/api/overview
/api/memory/inspector/status
/api/assistant-hub/status
/api/assistant-hub/connections
/api/codex/current
/api/obsidian/status
```

Authorities remain unchanged:

```text
Workspace and memory/vector state -> Memory Statistics / Inspector
Sources, conversations, messages -> Structured Read Model
AI discovery and connections -> Assistant Hub
Pending memory review -> Codex Current / Memory Review
Vault identity -> Obsidian Service
Recent imports and failures -> Extraction Queue
```

Partial request failure remains visible. Unknown values are not converted to zero, healthy, connected or production.

## 4. Delivered behavior

The first screen now shows:

- Production / Acceptance / unknown Workspace truthfully;
- formal Vault identity and display path;
- sources, conversations, messages, indexed permanent knowledge, Core Memory and vector counts;
- detected AI tools, import-ready sources, configured clients and live-tested clients;
- recent ChatGPT/Codex/import jobs and their real queue state;
- exactly one recommended next action based on current facts;
- pending-review routing;
- verified Windows/runtime/data-protection fixes;
- live Embedding status using owner-facing wording.

`degraded` is displayed as `部分能力待处理`. An inactive Embedding does not turn the whole Desktop into a frightening fake catastrophe; lexical retrieval remains explicitly usable.

## 5. Validation contract

Updated:

```text
desktop/lingji-control/scripts/guided-usage-smoke.mjs
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
```

The contracts verify:

- the start-center component and CSS are loaded;
- all five supporting API paths are present;
- Workspace, Vault, full-memory layers, AI summary, recent imports and known-issue sections exist;
- unknown-state wording is retained;
- Embedding uses truthful owner-facing wording;
- observation-first automatic refresh remains intact;
- responsive start-center style contracts exist.

Required commands:

```text
cd desktop/lingji-control
npm run test:smoke
npm run build
```

Repository gates:

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
```

## 6. Boundaries

```text
Database schema: unchanged
Runtime API: unchanged
Queue behavior: unchanged
Memory lifecycle: unchanged
Qdrant mutation: none
Core Memory mutation: none
Connector write behavior: unchanged
Production data: not accessed
Acceptance data: not accessed
```

## 7. Current result

```text
Code implementation: COMPLETE
Static smoke contract: UPDATED
Stacked tests workflow #1072: SUCCESS
Desktop smoke / TypeScript / Vite / Tauri config: SUCCESS
Python 3.11 / 3.12 / Windows: SUCCESS
MCP / Obsidian plugin / browser capture: SUCCESS
Real installed UI: PENDING
Owner acceptance: PENDING
Merge into PR #60 branch: ALLOWED
Merge into master: NOT ALLOWED UNTIL OWNER ACCEPTANCE
```

## 8. Owner-machine acceptance

The exact packaged artifact must demonstrate:

1. the active Workspace is obvious;
2. official Vault and memory-layer counts are understandable;
3. detected/configured/tested AI states are not confused;
4. recent imports and failures are visible;
5. only one recommended next step is emphasized;
6. Production and Acceptance are visually distinguishable;
7. inactive Embedding is explained without hiding the limitation;
8. all start-center actions route to working pages.

## 9. Rollback

This patch is presentation-only. Reverting the component, CSS, Overview wiring and smoke assertions removes the start center without data migration, index rebuild or connector rollback.
