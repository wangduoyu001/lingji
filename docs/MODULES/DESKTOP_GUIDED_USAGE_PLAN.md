# Desktop Guided Usage Plan

Status: IMPLEMENTED_IN_PR_56 / CI_PENDING / OWNER_ACCEPTANCE_PENDING

Branch: `feature/desktop-guided-usage`

Pull request: `#56`

Base commit: `18b99a6909e929df432253686eeaeee3ed9f7024`

## 1. Problem

The installed Desktop controls respond, but the owner cannot reliably understand:

- what each page is for;
- which page should be used first;
- what sequence should be followed after submitting content;
- what a successful action looks like;
- when advanced diagnostics are actually needed.

This is a usability and product-guidance defect, not a dead-control defect.

## 2. Product decision

Desktop usability is the highest product priority before further backend expansion.

The formal daily path is:

```text
运行状态
→ 投喂资料
→ 查看活动记录
→ 审核候选记忆
→ 仅在存在待办时处理异常
```

Advanced diagnostics remain available, but they must not be presented as the normal daily workflow.

## 3. Architecture

The guidance layer is centralized instead of copied into every page.

```text
PageId
→ PageGuide configuration
→ shared PageGuide component
→ owner-facing purpose / timing / steps / next actions
```

Persistent help uses:

```text
DesktopShell
→ UsageGuideDrawer
→ daily flow and diagnostic routing
```

The Overview page additionally exposes the four-step daily workflow as direct navigation cards.

## 4. Code entry points

- `desktop/lingji-control/src/components/PageGuide.tsx`
- `desktop/lingji-control/src/components/UsageGuideDrawer.tsx`
- `desktop/lingji-control/src/pages/OverviewPage.tsx`
- `desktop/lingji-control/src/components/DesktopShell.tsx`
- `desktop/lingji-control/src/GuidedUsage.css`
- `desktop/lingji-control/scripts/guided-usage-smoke.mjs`

## 5. Scope

Implemented:

- page-level usage explanation for all formal Desktop pages;
- clear “when to use this page” text;
- three-step operating guidance;
- primary and secondary next-step navigation;
- four-step daily workflow on Overview;
- persistent help entry in sidebar and toolbar;
- slide-in guide for daily tasks and advanced-diagnostic routing;
- owner-facing Chinese labels on the Overview page;
- smoke-test contract.

Not included:

- backend API changes;
- database or schema changes;
- Qdrant or Embedding changes;
- automatic product walkthrough telemetry;
- deletion or hiding of existing advanced pages;
- full visual redesign of every feature page.

## 6. Validation

Required automated checks:

```text
npm run test:smoke
npm run build
GitHub tests workflow
P0 Windows Gate
Windows Desktop Release Baseline
```

Required owner-machine acceptance:

1. install the exact PR artifact;
2. confirm the Overview daily flow is immediately understandable;
3. open each primary page and confirm the guide explains purpose and next action;
4. open the persistent “怎么使用” drawer from sidebar and toolbar;
5. use the guide to navigate through one complete workflow;
6. report any confusing wording or missing step before merge.

## 7. Rollback

This feature is isolated to React components, CSS and smoke tests.

Rollback can remove:

- `PageGuide.tsx`;
- `UsageGuideDrawer.tsx`;
- `GuidedUsage.css`;
- the `PageGuide` wrapper in `AppPages.tsx`;
- help-entry changes in `DesktopShell.tsx`;
- the daily-flow block in `OverviewPage.tsx`;
- `guided-usage-smoke.mjs` and its suite entry.

No data migration or backend rollback is required.

## 8. Next phase

After owner acceptance and merge, proceed to:

```text
Unified Qdrant SemanticProvider Integration
```

The next phase must preserve this UI guidance layer and expose real semantic, vector and embedding states through the existing formal Desktop and 8766 API.
