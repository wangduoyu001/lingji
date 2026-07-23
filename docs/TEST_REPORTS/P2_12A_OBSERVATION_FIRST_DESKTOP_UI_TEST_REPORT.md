# P2-12A Observation-first Desktop UI Test Report

## Branch

```text
work/p2-12a-observation-first-ui
```

## Stack dependency

This branch is based on the current P2-11B Sidecar branch:

```text
work/p2-11b-runtime-sidecar-manager
```

P2-12A must not be merged before its base dependency is resolved or the branch is rebased through a normal fast-forward/merge workflow. Force push and history rewriting are not required.

## Scope

This report covers:

```text
four-entry primary navigation
observation-first Overview
automatic Activity record
owner-only Attention inbox
collapsible Advanced Diagnostics
automatic runtime recovery
collapsed runtime maintenance controls
```

## Static contract test

```text
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
```

The smoke verifies:

- exactly four primary navigation items;
- detailed tools are absent from primary navigation;
- all advanced pages remain routable;
- Desktop sidebar renders `PRIMARY_NAVIGATION` only;
- advanced pages return to Advanced Diagnostics;
- runtime controls are inside a collapsed details element;
- unexpected offline state schedules automatic recovery;
- owner-requested stop pauses recovery;
- Overview has no routine manual refresh action;
- Activity is automatic and separates current/recent work;
- Attention only surfaces owner-required conditions;
- Advanced Diagnostics uses collapsible groups;
- Current Work polls automatically and preserves truthful idle/progress states.

## Existing smoke updates

The following historical tests are updated without weakening their safety guarantees:

```text
native-desktop-ui-smoke.mjs
auto-review-shadow-smoke.mjs
```

Changes:

- Desktop-only browser boundary is now checked in `RuntimeBoundary.tsx` instead of requiring all text inside `App.tsx`.
- Auto Review safety is checked under the new primary/advanced navigation model instead of requiring the removed five-group sidebar.
- Forbidden Auto Review mutation endpoints remain forbidden.

## Complete Desktop smoke suite

The named Desktop smoke suite increases from 18 to 19 scripts.

Required result:

```text
19/19 PASS
```

## TypeScript and frontend build

Required commands:

```text
npm ci
npm run test:smoke
npm run build
```

The build must confirm:

- all new `PageId` values are routed;
- `RuntimeBoundary` props are type-safe;
- `DesktopShell` receives owner-stop and auto-recovery state;
- Activity and Attention polling contracts compile;
- no duplicate navigation ID exists;
- production Vite output succeeds.

## Runtime behavior checks

Required owner-side checks after a packaged build exists:

1. Launch LingJi and confirm the core starts without a manual button.
2. Interrupt a managed core unexpectedly.
3. Confirm Desktop displays automatic recovery rather than demanding a start click.
4. Confirm the core reconnects after the recovery delay.
5. Use the collapsed runtime details to stop the managed core intentionally.
6. Confirm automatic recovery remains paused.
7. Select `恢复运行` and confirm operation resumes.
8. Confirm an external 8766 service is still not stopped or restarted.

## Navigation behavior checks

1. Sidebar contains only:
   - 运行状态
   - 活动记录
   - 需要我处理
   - 高级诊断
2. Detailed pages are absent from the persistent sidebar.
3. Advanced Diagnostics exposes all previous pages.
4. An advanced page shows `返回高级诊断`.
5. No detailed page is deleted or duplicated.

## Overview behavior checks

1. No `刷新本机状态` button is visible.
2. Overall posture remains truthful.
3. Current work reports idle when no activity exists.
4. Current work displays progress only when total progress is known.
5. The owner-attention summary links to the Attention page.
6. Provider, scheduler and detailed health internals are not on the default page.

## Attention behavior checks

The page must surface only owner-required conditions:

```text
pending memory review
SHADOW owner review
blocked SHADOW decision
failed jobs after retries
health errors
vector rebuild required
low disk
```

It must not turn ordinary queue, retry, polling or completed tasks into owner actions.

## Safety impact

```text
Auto Review ACTIVE enabled: no
Memory mutation added: no
Automatic Qdrant rebuild/delete: no
Automatic model download: no
Automatic backup restore: no
Browser control entry: no
General JavaScript shell: no
Database schema change: no
second_brain change: no
```

## Documentation gate

Required documentation:

```text
docs/MODULES/P2_12A_OBSERVATION_FIRST_DESKTOP_UI.md
docs/TEST_REPORTS/P2_12A_OBSERVATION_FIRST_DESKTOP_UI_TEST_REPORT.md
```

## Current status

```text
TESTS_ADDED_AWAITING_GITHUB_ACTIONS
```

The feature must not be marked complete until:

- all GitHub checks pass;
- P2-11B dependency is resolved;
- packaged Desktop interaction is verified locally;
- the local report records actual results rather than planned checks.
