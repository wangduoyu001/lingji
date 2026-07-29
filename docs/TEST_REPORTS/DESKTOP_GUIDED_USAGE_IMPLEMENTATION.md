# Desktop Guided Usage Implementation Report

Status: CODE_COMPLETE / CI_PENDING / OWNER_UI_ACCEPTANCE_PENDING

Pull request: `#56`

Branch: `feature/desktop-guided-usage`

Base: `master@18b99a6909e929df432253686eeaeee3ed9f7024`

## 1. Goal

Make the installed LingJi Desktop understandable before adding more backend capability.

The owner confirmed that controls were responsive but the operating sequence was unclear. The implementation therefore treats comprehensibility as the primary acceptance target.

## 2. Modified files

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/components/PageGuide.tsx
desktop/lingji-control/src/components/UsageGuideDrawer.tsx
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/GuidedUsage.css
desktop/lingji-control/scripts/guided-usage-smoke.mjs
desktop/lingji-control/scripts/run-smoke-suite.mjs
```

## 3. Delivered behavior

- every Desktop page shows a shared usage guide;
- each guide explains purpose, when to use the page, three operating steps and next actions;
- Overview shows a four-step daily workflow;
- sidebar and toolbar expose a persistent “怎么使用” entry;
- the slide-in guide routes common problems to the correct advanced page;
- Overview engineering headings were replaced with owner-facing Chinese labels;
- guidance data is centralized and does not duplicate business logic;
- no backend or data mutation is introduced.

## 4. Data and API impact

```text
Database schema: unchanged
Runtime API: unchanged
Qdrant: unchanged
Embedding: unchanged
Production data: not accessed
Acceptance data: not accessed
```

## 5. Test contract

New static smoke contract:

```text
desktop/lingji-control/scripts/guided-usage-smoke.mjs
```

The contract verifies:

- `GuidedUsage.css` is loaded;
- `PageGuide` wraps formal pages;
- daily-flow language and actions exist;
- persistent help exists in the Desktop shell;
- usage drawer contains daily and advanced flows;
- required style tokens exist;
- the smoke is part of `run-smoke-suite.mjs`.

## 6. Test commands

Expected CI commands:

```text
cd desktop/lingji-control
npm ci
npm run test:smoke
npm run build
```

Repository workflows:

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
```

## 7. Current result

```text
Code implementation: COMPLETE
Smoke contract: ADDED
GitHub CI: PENDING
Real installed UI: PENDING
Owner acceptance: PENDING
Merge: NOT ALLOWED YET
```

This report must be updated with exact workflow run numbers and artifact identity after CI completes.

## 8. Known limitations

- guidance text may require owner wording adjustments after real use;
- this PR does not redesign every detailed feature form;
- it does not repair the separate unavailable `bge-m3` acceptance-environment condition;
- it does not begin Unified Qdrant SemanticProvider work;
- help state is intentionally not persisted because the entry should remain discoverable.

## 9. Rollback

The implementation is UI-only. Reverting the PR removes the guidance components and CSS without data migration, index rebuild or Runtime rollback.

## 10. Next step

1. wait for CI;
2. fix any smoke or TypeScript failure without reducing assertions;
3. build the exact Windows artifact;
4. perform owner-machine UI acceptance;
5. revise wording where the owner still cannot understand the workflow;
6. merge only after explicit owner confirmation;
7. start Unified Qdrant SemanticProvider Integration from the merged master.
