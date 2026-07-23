# P2-12A Observation-first Desktop UI Test Report

## Branch and validated revision

```text
branch: work/p2-12a-observation-first-ui
validated head: 9c26d3b540e46716a05fac773e42b6b8f228fd0f
pull request: #48
workflow: tests #739
workflow run id: 29973972574
result: SUCCESS
```

## Stack dependency

This branch is based on the current P2-11B Sidecar branch:

```text
work/p2-11b-runtime-sidecar-manager
PR #47
```

P2-12A must not be merged before its base dependency is resolved and the PR is retargeted or integrated through a normal merge/fast-forward workflow. Force push and history rewriting are not required.

## Scope

This report covers:

```text
four-entry primary navigation
observation-first Overview
automatic Activity record
unresolved-only owner Attention inbox
collapsible Advanced Diagnostics
automatic runtime recovery
collapsed runtime maintenance controls
truthful unknown-state presentation
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
- Attention only surfaces owner-required unresolved facts;
- cumulative SHADOW metrics are not presented as current owner tasks;
- failed Attention reads remain unknown instead of being shown as clear;
- Advanced Diagnostics uses collapsible groups;
- Current Work polls automatically and preserves truthful idle/progress states.

## Existing contract updates

The following historical tests were updated without weakening safety guarantees:

```text
native-desktop-ui-smoke.mjs
auto-review-shadow-smoke.mjs
runtime-sidecar-smoke.mjs
windows-release-smoke.mjs
ui-modular-smoke.mjs
tests/test_p2_08_p2_09_integration.py
```

Changes:

- Desktop-only browser boundary is checked in `RuntimeBoundary.tsx` instead of requiring all text inside `App.tsx`.
- Auto Review safety is checked under the primary/advanced navigation model instead of the removed five-group sidebar.
- Sidecar and release tests require automatic startup/recovery while preserving collapsed maintenance actions.
- Combined integration tests require four observation entries and preserve Auto Review OFF/SHADOW-only boundaries.
- Forbidden Auto Review mutation endpoints remain forbidden.

## GitHub Actions results

### Python 3.11

```text
507 passed
11 skipped
0 failed
2 warnings
10.72 seconds
```

### Python 3.12

```text
507 passed
11 skipped
0 failed
2 warnings
11.25 seconds
```

### Windows Python 3.12

```text
507 passed
11 skipped
0 failed
2 warnings
69.22 seconds
```

Warnings are existing dependency deprecations:

- Pydantic class-based config deprecation;
- Starlette `httpx` TestClient deprecation.

No new P2-12A warning was introduced.

### Desktop UI

```text
named smoke suite: PASS (19 scripts)
TypeScript build: PASS
Vite production build: PASS
Tauri configuration validation: PASS
```

### Other repository gates

```text
MCP smoke: PASS
Browser capture smoke: PASS
Obsidian plugin smoke: PASS
```

## Navigation validation

The persistent sidebar contains only:

```text
运行状态
活动记录
需要我处理
高级诊断
```

Validated behavior:

- detailed pages are absent from the persistent sidebar;
- Advanced Diagnostics exposes all previous pages;
- advanced pages provide `返回高级诊断`;
- no detailed page was deleted or duplicated;
- `App.tsx` remains below the modularity threshold.

## Overview validation

Validated source/build contracts:

- no `刷新本机状态` action;
- overall posture remains data-driven;
- current work reports idle when no activity exists;
- progress is displayed only when total progress exists;
- owner-attention summary links to the Attention page;
- provider, scheduler and detailed health internals are absent from the default page.

## Attention validation

The page surfaces only conditions that have current unresolved semantics:

```text
pending memory review
failed jobs after retries
current health errors
vector rebuild required
low disk
```

It deliberately does not treat cumulative SHADOW decisions as current tasks because the backend does not yet expose unresolved/read state.

If the current-review source fails before any successful result, the page shows:

```text
部分待办状态暂时未知
```

It does not display `暂时不需要你处理` for an unknown state.

## Runtime behavior requiring packaged local validation

The following behavior is implemented and statically/compile validated, but still requires a packaged Desktop on the owner machine:

1. Launch LingJi and confirm the core starts without a manual button.
2. Interrupt a managed core unexpectedly.
3. Confirm Desktop displays automatic recovery rather than demanding a start click.
4. Confirm the core reconnects after the 12-second recovery delay.
5. Use collapsed runtime details to stop the managed core intentionally.
6. Confirm automatic recovery remains paused after owner stop.
7. Select `恢复运行` and confirm operation resumes.
8. Confirm an external 8766 service is still not stopped or restarted.
9. Confirm the four-entry hierarchy is visually usable at the packaged window size.

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

```text
docs/MODULES/P2_12A_OBSERVATION_FIRST_DESKTOP_UI.md
docs/TEST_REPORTS/P2_12A_OBSERVATION_FIRST_DESKTOP_UI_TEST_REPORT.md
```

## Current status

```text
CI_VALIDATED_AWAITING_STACK_DEPENDENCY_AND_PACKAGED_LOCAL_ACCEPTANCE
```

The code and repository contracts are validated. The feature is not marked fully complete because:

- P2-11B PR #47 remains unresolved;
- PR #48 is intentionally stacked on #47;
- packaged Desktop interaction has not been recorded in a local acceptance report;
- the claimed P2-11B local Windows report is still not visible in the repository search or PR #47.
