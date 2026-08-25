# P2-09D Desktop UX and Auto Review SHADOW Dashboard

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Make LingJi's desktop control center easier to navigate and make Auto Review observable without weakening owner authority. The UI groups related tools, collapses sensitive connection controls, presents truthful runtime states, and exposes SHADOW decisions with their explanations.

## Five navigation groups

The previous flat list is organized into:

1. Overview
2. Memory and projects
3. Capture and processing
4. Models and runtime
5. Operations and settings

Auto Review appears beside manual memory review so the distinction between suggestion and authority is visible.

## Connection panel

The top bar shows a compact connection summary. API URL and token inputs are hidden until expanded. The token remains part of the existing local connection flow and is not copied to a new store.

## Overview

The Overview cards now surface:

- system/runtime state;
- pending/running/retrying jobs;
- memory document/chunk/revision counts;
- vector state, count, dimension and rebuild warning;
- active/configured embedding model;
- compute mode/device;
- LingJi storage and disk free space.

Unknown values display as unknown. Stale memory/vector snapshots receive an explicit warning. Status colors are based on returned state rather than the mere presence of an object.

## Manual review authority

The manual Memory Review page contains a visible authority notice. Approval, edited approval, rejection, archive and manual Core Memory creation remain on that page and still use existing owner-confirmed endpoints.

## Auto Review SHADOW dashboard

The dashboard polls the authenticated 8766 API through the P2-09C data layer:

- status;
- metrics;
- decision history.

It displays:

- OFF/SHADOW mode;
- mutation-enabled anomaly state;
- decision and AI-assessment counts;
- owner-review and blocked counts;
- actual mutation count, expected to remain zero;
- rule findings, risk score/level and concise local-AI assessment;
- audit-only owner feedback.

A candidate ID can be evaluated in SHADOW by reading the existing candidate and posting it to the evaluation endpoint. The page states that this writes only a decision/audit suggestion.

## Deliberately absent controls

The dashboard provides no control for:

- approve;
- reject;
- merge;
- delete/forget;
- append evidence;
- promote to Core Memory;
- execute decision;
- enable ACTIVE.

If the backend ever reports ACTIVE or mutation enabled, the UI renders an error rather than presenting it as a normal operating mode.

## Polling behavior

The page reuses `usePollingResource` from P2-09C. It pauses while hidden, prevents overlapping requests, backs off after failures, preserves the last successful data and marks stale state.

## Changed files

- `desktop/lingji-control/src/App.tsx`
- `desktop/lingji-control/src/AppPages.tsx`
- `desktop/lingji-control/src/navigation.ts`
- `desktop/lingji-control/src/types.ts`
- `desktop/lingji-control/src/DesktopUX.css`
- `desktop/lingji-control/src/pages/OverviewPage.tsx`
- `desktop/lingji-control/src/pages/MemoryReviewPage.tsx`
- `desktop/lingji-control/src/pages/AutoReviewPage.tsx`
- `desktop/lingji-control/src/pages/autoReviewTypes.ts`
- `desktop/lingji-control/scripts/auto-review-shadow-smoke.mjs`
- `desktop/lingji-control/scripts/run-smoke-suite.mjs`

## Dependencies

This branch is stacked on P2-09C and reuses its polling/status contracts. The dashboard API becomes functional when P2-08A/P2-08B are integrated.

## Rollback

Revert the P2-09D commits. No Python, database, memory, Obsidian or Qdrant migration is involved.
