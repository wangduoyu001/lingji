# P2-09C Desktop Polling Data Layer

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Provide one reusable polling contract for the Tauri desktop UI and one truthful Brain Status type contract. Status pages should refresh without overlapping requests, cancel obsolete work, preserve the last successful payload after errors, and expose stale state explicitly.

## Polling contract

`usePollingResource<T>` supports:

- `enabled`
- configurable normal interval
- immediate or delayed first request
- manual `refresh()`
- manual `pause()` and `resume()`
- first-load `loading`
- background `refreshing`
- `AbortController` cancellation
- one in-flight request per hook instance
- recursive `setTimeout` scheduling instead of overlapping `setInterval` requests
- exponential failure backoff with a maximum interval
- longer backoff for 401/403 failures
- pause while the document is hidden
- stale calculation based on the last successful timestamp
- retention of the last successful data after a failed refresh

An aborted request is not rendered as a user-facing error.

## Resource state contract

`contracts/resourceState.ts` distinguishes:

- healthy
- busy
- degraded
- unavailable
- disabled
- configuration required
- unknown

A resource can simultaneously contain old data, a refresh error and `stale=true`. Unknown numeric values remain `null`; they are not converted to zero.

## Brain Status contract

`contracts/brainStatus.ts` defines memory, vector, embedding, GPU, processing and warning fields expected from `/api/brain/status`. `normalizeBrainStatus()` tolerates temporarily missing backend fields but preserves the semantic difference between:

- measured zero
- unknown/null
- unavailable status
- stale status

The contract includes fields planned and supplied by P2-09A without fabricating fallback success values.

## Page migrations

### Brain Status

- Fetches through `usePollingResource` every five seconds while active and visible.
- Uses the shared Brain Status normalizer.
- Preserves old data on refresh failure.
- Shows stale/error state.
- Displays unknown GPU utilization as unknown rather than `0%`.

### Jobs

- Polls every three seconds.
- Restarts safely when the status filter changes.
- Cancels obsolete requests.
- Preserves the previous job table during refresh failures.

## Contract handoff

The stable three-file contract head is:

`4222daf432134b8d77d5e7b514c258022d5ed4a8`

It contains:

- `src/hooks/usePollingResource.ts`
- `src/contracts/brainStatus.ts`
- `src/contracts/resourceState.ts`

P2-09D may base its branch on that SHA. Later P2-09C commits only migrate pages and add tests/docs.

## Changed files

- `desktop/lingji-control/src/hooks/usePollingResource.ts`
- `desktop/lingji-control/src/contracts/brainStatus.ts`
- `desktop/lingji-control/src/contracts/resourceState.ts`
- `desktop/lingji-control/src/pages/BrainStatusPage.tsx`
- `desktop/lingji-control/src/pages/JobsPage.tsx`
- `desktop/lingji-control/scripts/polling-data-smoke.mjs`
- `desktop/lingji-control/scripts/run-smoke-suite.mjs`

## Out of scope

Navigation, App shell, Overview visual redesign, Memory Review visual redesign and Auto Review dashboard are owned by P2-09D.

## Known limits

Each mounted page owns its polling instance. A future query cache can coalesce identical resources across multiple simultaneously mounted pages if the desktop shell begins rendering inactive pages concurrently.

## Rollback

Revert the P2-09C commits. No backend, database or user data migration is involved.
