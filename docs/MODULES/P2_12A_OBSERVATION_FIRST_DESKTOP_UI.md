# P2-12A Observation-first Desktop UI

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Product principle

LingJi Desktop is an observation surface, not a daily administration console.

The normal owner experience answers four questions:

1. Is LingJi healthy?
2. What is it doing now?
3. What finished or failed recently?
4. Is there anything only the owner can decide?

Routine runtime, retry, polling and recovery work stays automatic. Detailed tools remain available, but they are not primary navigation.

## Primary navigation

The persistent Desktop sidebar contains exactly four entries:

```text
运行状态
活动记录
需要我处理
高级诊断
```

All previous feature pages remain implemented and routable. They move under Advanced Diagnostics rather than being deleted or duplicated.

## Running status

`OverviewPage` now shows:

- overall posture;
- automatic refresh truth;
- current work;
- owner-attention summary;
- six high-value system signals.

It no longer shows routine manual refresh, full provider internals, detailed health checks or scheduler tables.

Those details remain available through Advanced Diagnostics.

## Activity record

`ActivityPage` polls the existing formal APIs:

```text
GET /api/codex/current
GET /api/jobs?limit=80
```

It separates:

- running, queued and retrying tasks;
- recently completed or failed tasks;
- current project, session and activity stage.

The page refreshes automatically and does not require an owner refresh button.

## Owner attention

`AttentionPage` only surfaces matters that the system cannot safely decide and can confirm are still unresolved:

- candidate memories waiting for owner review;
- exhausted failed jobs;
- current health errors;
- vector rebuild requirements;
- low-disk alerts.

Normal retries, queue processing and status synchronization are not presented as owner tasks.

SHADOW metrics and decisions are audit history. The current backend contract does not expose an unresolved/read state, so cumulative SHADOW counts are deliberately not presented as current owner tasks. SHADOW history remains available through Advanced Diagnostics.

## Advanced diagnostics

`DiagnosticsPage` groups all detailed tools into collapsible sections:

```text
系统与运行
记忆与项目
采集与任务
存储与运维
```

The existing detailed pages remain the source of truth. P2-12A only changes discovery and hierarchy.

## Automatic runtime recovery

`useLingJiConnection` now distinguishes:

```text
unexpected offline state
owner-requested stop
```

Unexpected offline state:

- remains visible;
- retries connection automatically after 12 seconds;
- keeps polling runtime status;
- does not require repeated owner clicks.

Owner-requested stop:

- pauses automatic recovery;
- remains visible as an explicit owner pause;
- resumes only when the owner selects `恢复运行`.

## Runtime controls

Normal status no longer presents start, stop and restart as primary actions.

They are placed inside a collapsed runtime-details element:

```text
运行详情
故障工具
恢复与诊断
```

This preserves emergency and development controls without making them part of normal operation.

## Current work panel

`CurrentWorkPanel` now polls every five seconds and shows:

- current summary;
- project and session;
- current stage;
- progress when truthful progress values exist;
- pending owner review count;
- branch, checkpoint and memory index state.

It reports idle truthfully when there is no activity.

## Navigation architecture

```text
PRIMARY_NAVIGATION
ADVANCED_NAVIGATION
NAVIGATION = primary + advanced
```

The sidebar renders only `PRIMARY_NAVIGATION`.

Advanced pages still use the shared `PageId`, router and components. There is no second UI application or duplicate backend contract.

## Safety and authority

P2-12A does not change:

- authenticated loopback-only 8766 access;
- Obsidian Vault + Git authority;
- MemoryReviewService or MemoryLifecycleService authority;
- Auto Review OFF/SHADOW-only boundary;
- Qdrant deletion/rebuild policy;
- model download policy;
- database schema;
- backup or restore authority.

The attention page links to existing owner-confirmed workflows. It does not add automatic approval, rejection, deletion, rebuild or restore.

## Changed files

```text
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/components/RuntimeBoundary.tsx
desktop/lingji-control/src/components/CurrentWorkPanel.tsx
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/pages/ActivityPage.tsx
desktop/lingji-control/src/pages/AttentionPage.tsx
desktop/lingji-control/src/pages/DiagnosticsPage.tsx
desktop/lingji-control/src/DesktopUX.css
desktop/lingji-control/src/ReleaseUX.css
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
```

## Out of scope

P2-12A does not:

- add a new backend activity database;
- invent estimated completion times;
- automatically resolve owner memory decisions;
- invent an unresolved SHADOW state that the backend does not provide;
- remove detailed feature pages;
- merge the P2-11B Sidecar PR;
- claim the missing local P2-11B acceptance report exists;
- implement the updater or rollback workflow.
