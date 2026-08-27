# Task 4 Repair Round 1 — Independent Review

Date: 2026-08-28
Branch: `codex/phase1-automatic-memory`
Reviewed HEAD: `ac73e263a68b49a739881f4be8f6987dc2695e95`
Product repair range: `44b00d3..5201d6ba2a152713610297769acd73b10e88b28f`
Evidence/docs range: `5201d6b..ac73e263a68b49a739881f4be8f6987dc2695e95`

## Verdict

- **Spec Compliance: FAIL**
- **Task Quality: NEEDS_FIXES**
- **Task 4 acceptance for Task 5: NOT YET AUTHORIZED**

The repair closes the original exact-source authorization, revoked reauthorization,
request ownership, post-action snapshot and authentication findings in the normal
production path. Two Important findings remain: first-run onboarding has a finite
retry budget that can stop while the core still reports connected, and the claimed
offline/rendered-state coverage is not actually exercised by the rendered e2e.

## Findings

### Important I1 — first-run source retry stops after six failures while `connected` remains true

`desktop/lingji-control/src/hooks/useMemorySourcesOnboarding.ts:36-43` retries only
while `retryRef.current < 5`; after the sixth failed `Promise.all` the hook returns
without a timer. `useLingJiConnection` marks the app connected after `/api/overview`
and source discovery is a separate request, so a healthy overview plus a source
endpoint that returns 503 for longer than the retry window leaves the app on Overview
for the remainder of the mounted session. No disconnect is required to reset this
state, and no later source check is scheduled. This is contrary to stable first-run
automation: a temporary source-service startup delay can make the required onboarding
appear absent and force manual navigation.

The existing e2e only makes one `/sources` request fail and then succeeds within the
short retry window. The helper smoke checks the pure route decision, not the hook's
long-lived retry lifecycle. Repair should use a bounded exponential retry that keeps
the check pending until success or an explicit offline/disconnect state, or provide a
truthful persistent retry affordance that is reached automatically; it must not hot
loop.

### Important I2 — offline and several claimed rendered behaviors are not proven by a rendered test

The rendered harness `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
requires an authenticated fake server and covers the happy path plus source cards
for the nine source states. It never simulates the page losing the source endpoints,
an offline/connection-error response after mount, or the page's offline retry UI.
The source repair smoke only calls pure helpers (`decideOnboardingRoute`,
`authorizationEvidence`, `actionAvailability`, `ownsRequest`) and does not render
the component. Therefore the report and acceptance log's claim that “offline” and
all rendered action behavior were covered is broader than the evidence.

Add a deterministic rendered outage case: preserve a prior snapshot, make the source
reads fail, assert the visible stale/offline explanation and retry action, then restore
the server and prove recovery. Keep unavailable counts as `尚未获得` and never show
false completion. Also exercise the actual onboarding hook navigation race rather
than only its pure decision function.

### Minor I3 — a paused scan is rendered as “扫描中” with a contradictory next step

`memorySourcesApi.ts:102` maps both `running` and `paused` scans to source state
`scanning`. Consequently `MemorySourcesPage.tsx:154-156` renders a paused source as
“扫描中” and the copy from `describe` says “等待扫描完成，或暂停后稍后继续” even
though it is already paused. The action set correctly exposes `继续`, and the
rendered e2e checks that action, so this is not a lifecycle or authorization failure;
it is nevertheless misleading owner-facing status. Either make paused a distinct
rendered operational label or provide paused-specific copy while preserving the
locked nine source-state model.

### Minor I4 — force-refresh protection is production-safe but not fully generic

`usePollingResource.ts` aborts the prior controller and suppresses late successful
responses through `controller.signal.aborted`; the production `LingJiApi` converts
that abort to `REQUEST_CANCELLED`, which `isAbortReason` recognizes. The current
source-page flow therefore passed the forced-refresh race checks. However, the catch
path does not also check `controller.signal.aborted` or request identity before
publishing a non-standard fetcher's late non-abort error. A custom fetcher that rejects
with an ordinary `Error` after honoring abort could still overwrite the newer state.
This was not reproduced through `LingJiApi` and is not an acceptance blocker for the
current path, but the hook contract would be safer with the same identity guard in
both success and error publication.

## Closed findings rechecked

- I1 transient first-read success path and stale-navigation guard: code-level guard
  verified; the long-lived retry limitation is recorded separately above.
- I2 exact authorization evidence now matches canonical kind/root and, when returned,
  source ID; the old same-kind/different-root predicate is gone.
- I3 revoked sources expose reauthorization, including picker sources.
- I4 nine source cards and impossible-action gating are rendered in the fake-server
  flow; offline coverage remains open as I2 above.
- I5 evidence metadata is no longer pending: report records metadata correction
  `3564abaee0da59408c0b97f1cc02487a0b0e5f84`.
- I6 verified post-action snapshot is held while a forced fresh poll supersedes older
  in-flight work; no stale-success display was observed in the production fetch path.
- I7 the fake server rejects missing and wrong `X-LingJi-Token`, and the rendered UI
  succeeds only with the authenticated Tauri credential shim.

## Fresh verification

Executed from `desktop/lingji-control` unless noted:

```text
npm run build                         PASS
npm run test:memory-sources           PASS
npm run test:memory-sources-repair   PASS
npm run test:e2e:memory               PASS
npm run test:work-fact               PASS
npm run test:runtime                 PASS
npm run test:inspector               PASS
npx tsx scripts/observation-first-ui-smoke.mjs PASS
npm run test:smoke                    FAIL (unchanged codex-workspace-smoke baseline: CurrentWorkPanel.tsx lacks “当前项目”)
npm run test:codex-loop               FAIL (same unchanged baseline)
```

Repository checks:

```text
git diff --check 44b00d3..ac73e263   PASS
python scripts/check_acceptance_sync.py       PASS
python scripts/check_local_execution_handoff.py PASS
```

The full smoke failure is unrelated to this repair and was not weakened or hidden.
No live 8766, packaged Sidecar, Artifact, Production/Vault, owner data, or third-party
application was touched. `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## Scope ruling

No product files were modified during this review. The two Important findings must be
closed or explicitly re-scoped with fresh evidence before Task 4 is reported as
accepted for Task 5. This review does not authorize Artifact, release, or owner
acceptance claims.
