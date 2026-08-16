# PR88 Owner Workbench V4 Implementation Report

> Status: implementation complete; automatic acceptance is authoritative and must pass on the final exact PR Head before merge.
> Branch: `fix/pr88-owner-workbench-v4`
> Base product commit: `1d99d10cdcb151c0a0257f7d0a93937cdb817b49`
> Product PR: #88 (`feature/owner-autopilot-ui-codexpp`)
> Development PR: #102
> M5 status: **NOT ACTIVATED**

## 1. Why V4 exists

V3 passed technical packaging/runtime checks but failed owner-machine UX. The blocking owner observations were:

- “灵机已做什么 / 下一步是什么”不可理解；
- “去处理” could open a page with no real pending object;
- pagination could continue without a proven backend boundary;
- pending-review / memory surfaces could be empty while the home implied work existed;
- automation was visible mainly as counters/status, not as object-level work history;
- permanent memory remained hidden behind engineering-oriented inspector surfaces.

V4 therefore treats the failure as an information-architecture and product-logic failure, not a copywriting or card-layout problem.

## 2. Product contract

V4 implements the repository contract:

> **灵机 = 我的第二永久记忆大脑 + 主动型本地智能助手。**

Daily owner loop:

```text
Discover
  -> Understand
  -> Decide
  -> Act
  -> Verify
  -> Remember
  -> Brief
```

Owner-facing information should explain:

```text
发现了什么？
判断了什么？
做了什么？
记住了什么？
接下来会做什么？
是否需要我？
```

## 3. Research translated into product rules

The implementation does not copy another product skin. It uses these interaction principles:

- stable sidebar + list/detail + disclosure of technical detail;
- background work should return reviewable outcomes instead of requiring constant monitoring;
- inbox/attention items must correspond to a real actionable object;
- a global intent entry should reduce the need to understand internal module routing;
- execution history should preserve the causal chain from work object to result.

These principles were mapped onto LingJi's existing local-first, owner-controlled permanent-memory and permission boundaries.

## 4. Information architecture rebuilt

Primary navigation is now exactly:

```text
首页
记忆
工作
需要我
高级
```

Technical pages such as Qdrant/vector, models, compute, raw jobs, storage, logs and acceptance remain available under Advanced instead of dominating daily use.

### 4.1 首页 / Owner Briefing

The home now prioritizes:

1. `现在需要你吗`
2. `刚刚替你做了什么`
3. `现在正在做什么`
4. `接下来灵机会做什么`
5. `记忆发生了什么变化`
6. `主动发现`

It consumes real Memory Review, Assistant Hub, Codex Current, Memory Inspector, queue and event data. Aggregate technical statistics are collapsed.

### 4.2 记忆 / Permanent Memory

Permanent memory is a primary product surface rather than an advanced database inspector.

The page supports:

- real memory browse/search/filter;
- memory content or safe preview;
- type/status/time;
- source/provenance lookup;
- citations;
- vector/retrieval state;
- evidence-oriented explanation (`记住了什么 / 为什么能相信它 / 来源证据`);
- evidence-gated memory-gap messaging;
- backend-bounded pagination.

Obsidian Vault + Git remains permanent-memory/formal-knowledge authority. No new memory truth source was introduced.

### 4.3 工作 / Work History

The normal work page uses real jobs and Codex activity but presents an owner-readable work history:

```text
发生了什么
灵机做了什么
结果
下一步
```

Raw IDs and technical details are secondary disclosure. A technical failure is not automatically promoted into an owner decision.

### 4.4 需要我 / Owner Attention

This surface contains only real owner-boundary objects:

- a concrete permanent-memory review candidate;
- a concrete assistant-import candidate that requires content permission;
- a concrete irreversible vector rebuild boundary.

No real object ID means no owner action.

## 5. Shared owner decision projector

`desktop/lingji-control/src/ownerWorkbenchModel.ts` centralizes owner-attention semantics so Home and Attention do not invent separate rules.

It provides:

- `buildOwnerAttentionItems`
- `hasReviewConsistencyIssue`
- `ownerSourcesUnknown`
- `ownerAttentionSummary`

Object identity is explicit:

```text
memory candidate -> objectId + memoryId
import candidate -> objectId + candidateId
vector rebuild   -> explicit irreversible-maintenance object
```

If summary state reports pending review but the review endpoint returns no candidate object, the owner UI shows a consistency/degraded state and does not create a fake action.

## 6. Exact-object action routing

A V3 blocker was an action that navigated to a generic page without the promised pending item.

V4 carries the exact `memory_id` from Home/Attention through App routing into `MemoryReviewPage`.

`MemoryReviewPage` directly requests that same candidate and opens it in the detail pane. The owner does not have to search the review list again.

Assistant content authorization similarly posts to the exact discovered `candidate_id` and uses the exact confirmation token required by the existing backend contract.

## 7. Global owner command entry

`Cmd/Ctrl+K` focuses the global entry.

Current intentionally bounded abilities include:

- `记住：...` / `记录：...` -> real `/api/capture/text` submission;
- direct routing to Memory / Work / Attention / Capture.

Unsupported open-ended agent commands are not faked. The UI explicitly states the current capability boundary.

## 8. Truthful pagination

The V3 infinite-next-page blocker is treated as a product correctness issue.

Primary Memory and advanced Inspector consume backend `has_more`. Review and Capture use backend `has_more` or a proven finite `total` boundary. Unknown pagination state must not be presented as proof that another page exists.

`paginationBoundary.ts` defines the strict rule for continued consolidation: a full page alone is not evidence of another page.

## 9. Visual-system rebuild

`WorkbenchV4.css` replaces the previous card-dashboard composition with a calmer desktop workbench:

- stable compact sidebar;
- restrained state color;
- owner briefing hero rather than metric hero;
- dense list/detail structures for memory and work;
- object-level attention cards;
- timeline-oriented outcomes;
- technical runtime facts hidden under disclosure;
- consistent spacing, typography and interaction states;
- responsive behavior for narrower windows.

The visual system is intentionally subordinate to truthful product state. It does not manufacture activity to make the system look busy.

## 10. Executable owner scenarios

`owner-workbench-v4-scenarios.mjs` imports the real shared projector and executes scenarios covering:

1. no owner action;
2. real permanent-memory candidate;
3. real content-permission candidate;
4. irreversible vector rebuild;
5. pending-summary/detail inconsistency;
6. review source unknown;
7. assistant source unknown;
8. automatic work active while owner has no action.

The scenario tests verify exact object identity and owner/unknown/automatic summary semantics.

## 11. Regression and automatic gates

V4 updates and/or adds automatic coverage for:

- modular desktop IA;
- owner briefing;
- object-backed attention;
- exact memory review routing;
- permanent-memory evidence surface;
- work history;
- global owner input;
- assistant privacy boundary;
- pagination end conditions;
- Auto Review SHADOW safety;
- runtime stop/restart semantics;
- macOS arm64/DMG/embedded identity/isolation/window-recovery release contract;
- Windows/Python/MCP/Obsidian/browser regressions.

The final exact PR #102 Head must pass its development gates. After squash merge into the product branch, the new exact product SHA must independently pass the six product-level gates:

```text
tests
P0 Windows Gate
macOS Desktop Gate
Windows Desktop Release Baseline
acceptance-doc-sync
local-execution-handoff
```

No PR-head Artifact is eligible for owner-machine acceptance.

## 12. Safety boundaries preserved

V4 does **not**:

- add a second permanent-memory authority;
- auto-approve Permanent/Core Memory;
- widen AI conversation/content-read permission;
- recursively scan the whole drive;
- automatically perform destructive Production Qdrant rebuild;
- expose credential/token/cookie/Authorization material in daily owner projections;
- change exact-instance Sidecar lifecycle ownership;
- weaken Production/Acceptance physical isolation.

## 13. M5 gate

**M5 remains disabled during PR #102 development.**

A new `LOCAL_EXECUTION_TASK.md` may become ACTIVE only after:

1. PR #102 final exact Head automatic gates pass;
2. PR #102 is merged into the product branch;
3. the merged exact product SHA passes all six product-level gates;
4. new macOS and Windows Artifacts are independently verified to contain that exact product SHA;
5. Artifact hashes are locked into the handoff.

This prevents the owner machine from being used as a substitute for automated product testing.
