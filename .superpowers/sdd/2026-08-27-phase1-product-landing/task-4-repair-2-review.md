# Task 4 Repair Round 2 — Final Independent Review

Date: 2026-08-28
Branch: `codex/phase1-automatic-memory`
Reviewed HEAD: `08af0218db8b17a6bd065dc450ada609bd814d78`
Product repair range: `d5f902a..b45b1dd`
Evidence/docs range: `b45b1dd..08af021`

## Verdict

- **Spec Compliance: FAIL**
- **Task Quality: NEEDS_FIXES**
- **Final ruling: BLOCKED_AT_REPAIR_CAP**
- **Task 4 acceptance for Task 5: NOT AUTHORIZED**

The final repair closes the two Important findings from the previous review and the
requested polling/onboarding race cases, but the final Task 4 acceptance still has
one Important owner-facing omission and one Minor truthfulness concern. No product
files were modified during this review.

## Findings

### Important I1 — Home does not answer the required update/skip questions

The Task 4 plan requires Home to show this-run `added / updated / skipped / failed`
counts. `desktop/lingji-control/src/pages/OverviewPage.tsx:53` renders only
`本次新增`, `本次复用`, and `本次失败`. There is no `更新` or `跳过` metric, and
the source detail in `MemorySourcesPage.tsx:135` likewise exposes only `新增` and
`复用`. The existing backend `ScanRun` may not provide those fields; that is a
valid reason to show `尚未获得`, not a reason to omit the questions entirely.

This prevents a nontechnical owner from answering one of the five required Home
questions and makes the report's broad “this-run counts” claim incomplete. A
narrow follow-up can add the two UI metrics using existing response fields when
present and `尚未获得` otherwise; no backend, parser, queue, or new feature is
needed. Because this is the final authorized Task 4 repair review, it blocks the
Task 4 acceptance ruling and requires a boundary re-plan rather than another
unapproved repair round.

### Minor I2 — Unknown queue activity is presented as an asserted running state

`desktop/lingji-control/src/pages/OverviewPage.tsx:38` displays `后台自动运行`
when `queue.running` is absent. The same page correctly uses `尚未获得` for most
unknown counts, and the Task 4 acceptance explicitly requires unknown values not
to become fake zero/normal states. A healthy core does not by itself prove that
the queue has an observed running count. This should be changed to a neutral
`尚未获得`/specific unavailable explanation, or be tied to a measured runtime
fact. It is not a release/security blocker, but should be corrected with I1 in
the bounded UI follow-up.

## Repair-2 closures rechecked

- Long transient onboarding failure: fake server injects seven `/sources` failures;
  the rendered flow eventually reaches onboarding, demonstrating retry beyond the
  former six-attempt cap with exponential backoff. No hot-loop behavior is present
  in the hook.
- Disconnect/unmount/success guards: the hook resets retry state on disconnect,
  clears timers on cleanup, and stops retries after a successful check; late
  responses are guarded by mounted/connected refs.
- Delayed navigation: a held source response is released after navigation to
  Activity; the page remains on Activity and does not redirect back to onboarding.
- Source endpoint outage/recovery: with a prior successful snapshot, the rendered
  page shows the offline explanation and preserves the previous source state; after
  restoration, re-read recovers the current state.
- Late ordinary polling errors: `usePollingResource` checks request identity and
  abort state in both success and error paths; the repair smoke covers both stale
  and current aborted-error cases.
- Exact authorization: authorization evidence matches canonical kind/root and, if
  returned, source ID. Picker actions are restricted to Generic AI History and
  ChatGPT export roots.
- Revoked reauthorization: revoked picker sources expose a fresh authorization
  action and the rendered flow successfully reauthorizes them.
- Nine-state rendering/action gating: detected, consent-required, unsupported,
  authorized, scanning, current, degraded, revoked and failed are rendered with a
  visible next step and state-specific allowed/denied actions. Paused is rendered
  under scanning with visible `已暂停` and `继续扫描` copy.
- Authentication: the fake source server rejects missing and wrong
  `X-LingJi-Token`; the browser shim supplies the valid token and the rendered
  flow succeeds only through authenticated requests.
- No premature success: running scans show `扫描中` and no terminal-success copy;
  `已接管` is shown only after completed scan evidence. Authorization copy says it
  is recorded and awaiting the first scan.

## Fresh verification

Executed from `desktop/lingji-control`:

```text
npm run build                         PASS
npm run test:memory-sources           PASS
npm run test:memory-sources-repair   PASS
npm run test:e2e:memory               PASS
npm run test:work-fact                PASS
npm run test:runtime                  PASS
npm run test:inspector                PASS
npx tsx scripts/observation-first-ui-smoke.mjs PASS
npm run test:smoke                    FAIL (pre-existing codex-workspace-smoke:
                                      CurrentWorkPanel.tsx lacks “当前项目”)
npm run test:codex-loop               FAIL (same unchanged baseline)
```

The rendered E2E was run against the fake authenticated 8766-like server and
completed successfully. It exercises the onboarding race, seven transient
failures, outage/recovery, authorization, scan completion, revoke/reauthorize,
retry completion, all source-state cards and action gating. The browser close
phase is slow in this host but exits with code 0.

Repository checks:

```text
git diff --check d5f902a..HEAD           PASS
./.venv/bin/python scripts/check_acceptance_sync.py PASS
./.venv/bin/python scripts/check_local_execution_handoff.py PASS
```

The sync check reports no product-impacting changes relative to the reviewed
documentation head. `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## Scope and environment limits

- No live 8766 server, packaged Sidecar, Artifact, real Desktop release, owner
  data, Production/Vault, Qdrant, or third-party AI application was touched.
- This review authorizes neither release nor owner acceptance.
- The legacy full smoke failure is unchanged and unrelated to Task 4; no test was
  removed, skipped, weakened, or hidden.
- Task 2's stale scheduler cleanup-state quarantine remains unchanged; UI must
  continue to present it as needing restart/check, never as stopped.

## Required next action

Create a narrowly scoped UI follow-up before Task 5: add Home's `更新` and `跳过`
metrics with truthful `尚未获得` fallbacks, replace the unmeasured `后台自动运行`
fallback, add rendered assertions for both, and rerun the Task 4 focused matrix
plus the unchanged smoke baseline. Do not reopen Task 4 Repair Round 2 or expand
backend scope without a new authorized boundary.
