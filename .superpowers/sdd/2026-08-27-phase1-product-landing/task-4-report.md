# Phase 1 Product Landing — Task 4 Report

Date: 2026-08-27
Branch: `codex/phase1-automatic-memory`
Original product/test commit: `2dc03e6` (`feat: add automatic memory source onboarding`)
Review: `44b00d3` (`docs: record task four independent review`)
Repair product/test commit: `5201d6ba2a152713610297769acd73b10e88b28f` (`fix: close automatic memory landing review findings`)
Evidence/docs commit: pending (metadata-only correction follows)

## Verdict

`IMPLEMENTED_FOCUSED_PASS` for the Chinese automatic-memory source onboarding and observation projection slice. This is a code-level and deterministic fake-server result only. It is not packaged Artifact, release, real 8766, Production/Vault, or owner acceptance.

The independent review repair round is also `IMPLEMENTED_FOCUSED_PASS` for I1–I4, I6 and I7. The unrelated `CurrentWorkPanel` baseline remains unchanged.

## Scope delivered

- Added `memory_sources` PageId/navigation entry in the primary observation area and `MemorySourcesPage` backed only by existing authenticated Task 3 endpoints.
- Added typed DTO mapping and canonical kind/root merge. Backend `available` is shown as `detected`; only a completed terminal scan is shown as `current`/“已接管”. Running/paused, failed, revoked, unsupported, consent-required, degraded and expired states have explicit Chinese next steps.
- Added real endpoint actions for authorize/revoke/scan/pause/resume/retry and scan detail. Authorization uses generated grant ID, current ISO time, exact selected root, source kind/root, and `owner_confirmed=true`. Generic Inbox and ChatGPT use the existing Tauri folder picker; no free-form path input exists.
- Added one-time, session-scoped onboarding routing after the first successful connected source check. It does not use localStorage and does not re-hijack navigation after the check.
- Updated Home to answer discovered sources, authorized/current sources, current activity, this-run counts and memory/pending state. Missing backend counts render `尚未获得`; model/vector technical cards remain in diagnostics surfaces.

## TDD evidence

The first implementation test run was a behavioral RED because the production API module did not yet exist:

```text
npm exec -- tsx scripts/automatic-memory-sources-smoke.mjs
ERR_MODULE_NOT_FOUND: .../src/pages/memorySourcesApi.ts
```

The contract smoke then covered canonical merge, all nine UI states, unknown counts, expired copy, action payloads, stale-action verification, terminal scan evidence and no premature terminal success. Rendered coverage uses a fake authenticated 8766-like HTTP server and existing system Chrome.

Repair-round RED/GREEN:

- RED before repair: `automatic-memory-sources-repair-smoke.mjs` failed with `ERR_MODULE_NOT_FOUND` for the not-yet-exported repair helpers; the rendered flow failed at the revoked source because no reauthorization button was present.
- GREEN after repair: `npm run build`, `npm run test:memory-sources-repair`, and `npm run test:e2e:memory` all passed. The rendered harness now proves transient onboarding retry, stale-navigation protection, exact same-kind/root authorization evidence, revoked reauthorization, all nine source states plus offline/expired/unsupported/paused/failed action gating, verified post-action rendering, request ownership, and authenticated token rejection.

## Verification

```text
cd desktop/lingji-control
npm run build                         PASS
npm run test:memory-sources           PASS
npm run test:e2e:memory               PASS
npm run test:work-fact                PASS
npm run test:runtime                  PASS
npm run test:inspector                PASS
npm run test:memory-sources-repair   PASS
npm run test:smoke                    FAIL (pre-existing codex-workspace-smoke baseline: CurrentWorkPanel.tsx lacks “当前项目”; all earlier/new scripts pass)
```

The rendered harness proves first-run redirect, picker-only authorization, scanning progress without terminal-success copy, terminal completion counts, one simulated failure, retry completion, and no second onboarding hijack after navigating away and back.

`git diff --check` passed before the product commit. Acceptance sync and local handoff are run after this evidence/docs commit.

## Files changed

Product/test commit `2dc03e6`:

- `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`
- `desktop/lingji-control/src/pages/memorySourcesApi.ts`
- `desktop/lingji-control/src/pages/memorySourcesTypes.ts`
- `desktop/lingji-control/src/App.tsx`
- `desktop/lingji-control/src/AppPages.tsx`
- `desktop/lingji-control/src/navigation.ts`
- `desktop/lingji-control/src/pages/OverviewPage.tsx`
- `desktop/lingji-control/src/styles.css`
- `desktop/lingji-control/src/types.ts`
- `desktop/lingji-control/scripts/automatic-memory-sources-smoke.mjs`
- `desktop/lingji-control/scripts/run-smoke-suite.mjs`
- `desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`
- `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- `desktop/lingji-control/package.json`

Repair product/test commit `5201d6ba2a152713610297769acd73b10e88b28f`:

- `desktop/lingji-control/src/hooks/useMemorySourcesOnboarding.ts`
- `desktop/lingji-control/src/hooks/usePollingResource.ts`
- `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`
- `desktop/lingji-control/src/pages/memorySourcesApi.ts`
- `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- `desktop/lingji-control/scripts/automatic-memory-sources-repair-smoke.mjs`
- `desktop/lingji-control/scripts/run-smoke-suite.mjs`
- `desktop/lingji-control/package.json`

Evidence/docs commit also updates `docs/MODULES/CODE_MAP.md`, `docs/PROJECT_STATUS.md`, `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`, and this report.

## Boundaries and known limitations

- `LOCAL_EXECUTION_TASK.md` is `IDLE`; no live 8766 server, packaged Sidecar, Artifact build/install, real UI, owner data, Production/Vault, or third-party client action was performed.
- Playwright used the already installed `/Applications/Google Chrome.app`; no browser was downloaded.
- The complete legacy smoke suite remains blocked by the unrelated existing `codex-workspace-smoke.mjs` assertion. This task did not alter Task 3 Work Fact/CurrentWorkPanel behavior or weaken that test.
- Full smoke reaches that unchanged baseline after the new repair smoke and all preceding UI/runtime/observation checks pass. No test was removed, skipped, or weakened.
- Task 2 stale scheduler cleanup-state behavior remains unchanged; the UI presents degraded runtime as “需要重启/检查”, never “已停止”.
- No automatic promotion seam, backend/API expansion, database, queue, parser, retrieval or vector change was made.
