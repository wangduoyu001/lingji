# Task 4 independent review — Chinese source onboarding

Date: 2026-08-28
Branch: `codex/phase1-automatic-memory`
Reviewed product range: `8f94a1e..2dc03e6`
Reviewed evidence head: `77413ee86087abf25f00b6e183306bea2b07a548`

## Verdict

- **Spec Compliance: FAIL**
- **Task Quality: NEEDS_FIXES**
- **Repair Round 1: REQUIRED**

There are no Critical security findings in this review. The source page is implemented and the main happy path is functional, but two user-visible authorization/onboarding correctness defects block acceptance. The evidence/report also requires a metadata-only correction after product repair; that correction must not be counted as a product repair.

## Findings

### Important I1 — transient first-read failure permanently suppresses first-run onboarding

`desktop/lingji-control/src/App.tsx:21-35` sets `onboardingChecked.current = true` before the parallel `/sources` and `/discovered` requests resolve. The rejection handler does not reset it, and later effect runs return immediately. Therefore one temporary 8766/network failure while the app is connected can leave the user on Overview for the entire App session, even though no successful source check occurred. The dependency `page` also captures the initial `overview` value in the asynchronous callback, so a user navigating away before the request resolves can be navigated back to `memory_sources` unexpectedly.

This contradicts the stated “first successful connected source check” behavior and the acceptance requirement that first-run authorization is reliably reachable. The e2e only exercises successful first reads and cannot detect this race. Repair should mark the check complete only after both reads succeed, and guard the redirect against the current page/session state.

### Important I2 — authorization confirmation is not bound to the selected source root

`desktop/lingji-control/src/pages/MemorySourcesPage.tsx:77-85` verifies authorization with `next.sources.some((item) => item.kind === source.kind && ...)`, ignoring the selected folder/root and returned `source_id`. With two candidates of the same kind, an already-authorized first root can satisfy the predicate after the second root’s authorization response, even if the second root was not persisted or the response was otherwise stale. A direct probe of the shipped merge/evidence behavior produced two same-kind roots and showed that a kind-only authorization predicate returns true for the old authorized source.

The request does send the selected root (`memorySourcesApi.ts:131-142`), but the UI’s success evidence must prove the exact canonical kind/root (and preferably returned source identity), not merely any source of that kind. This is required for trustworthy “已授权” feedback when multiple inbox/export directories are present.

### Important I3 — revoked state promises reauthorization but exposes no reauthorization action

`memorySourcesApi.ts:67-70` tells the owner for `revoked`: “如需继续，请重新授权。” However `MemorySourcesPage.tsx:128-130` permits authorization only for `detected`, `consent_required`, or `degraded`; `revoked` is excluded. The revoked card therefore has no `授权`/`选择文件夹并授权` button while its next step requires exactly that action. This leaves the user at a dead end and violates the fixed action/next-step contract.

The repair should either expose reauthorization for a revoked discovered candidate (with a fresh grant and exact root) or change the copy to an actually available next step. The current e2e does not cover revoked state.

### Important I4 — acceptance evidence does not prove the required rendered state/action coverage

Task 4 Step 1 requires visible next steps and disabled impossible actions for every source state. The report/`CHANGE_ACCEPTANCE_LOG.md` record the source smoke as covering all nine states and action evidence, but `desktop/lingji-control/scripts/automatic-memory-sources-smoke.mjs` only exercises DTO merge/helpers and request payloads; it does not render `MemorySourcesPage` or assert button visibility/disabled state. The rendered e2e covers one Generic Inbox happy path, one running scan, one failure/retry path, and navigation. It does not render or exercise offline, expired, unsupported Claude, revoked, paused/resume, same-kind multi-root authorization, or failed-action handling. These gaps do not prove all nine states and action affordances.

This is an evidence/quality defect, not a reason to expand product scope. Add deterministic rendered assertions for each state and the two authorization races, or narrow the report claims. A skipped/untested state must remain explicitly unverified.

### Important I5 — report metadata is incomplete at the evidence head (metadata-only)

At reviewed HEAD `77413ee`, `.superpowers/sdd/2026-08-27-phase1-product-landing/task-4-report.md:5-6` records product/test `2dc03e6` correctly but says `Evidence/docs commit: pending`, although the report itself and synchronized docs were committed by `77413ee`. As with prior task evidence rules, this is a documentation-only correction after the product head is fixed; it is not a product repair and must not be used to claim a new implementation result. The corrected report should record the exact evidence/docs SHA without self-reference (or use a subsequent metadata commit, if required by the repository convention).

### Minor I6 — action refresh can briefly project an older in-flight snapshot

`MemorySourcesPage.tsx:51-56` obtains an independent fresh snapshot for verification and then calls `resource.refresh()`. `usePollingResource.refresh()` returns an existing in-flight request rather than forcing a post-action request. If polling began before a mutation, the UI state can be replaced by that pre-mutation response while the success message is already shown; the normal polling cadence eventually repairs the display. This is a bounded consistency issue, but a post-action refresh should supersede/cancel the stale request or apply the verified snapshot directly.

### Minor I7 — fake rendered server does not enforce the authentication header

`desktop/lingji-control/tests/e2e_owner_memory_flow.mjs` supplies a token through the Tauri credential shim, and production `LingJiApi` adds `X-LingJi-Token`; however the fake HTTP server accepts requests without checking that header. The test therefore proves route usage, not the authentication contract. Add an assertion in the fake server or a focused API contract check; this is not a product security failure in the reviewed source.

## Passing checks and observed results

Executed from `desktop/lingji-control`:

```text
npm run build                         PASS
npm run test:memory-sources           PASS
npm run test:e2e:memory               PASS
npm run test:work-fact                PASS
npm run test:runtime                  PASS
npm run test:inspector                PASS
npm run test:smoke                    FAIL (pre-existing codex-workspace-smoke assertion)
npm run test:codex-loop               FAIL (same pre-existing assertion)
git diff --check 8f94a1e..77413ee    PASS
```

The full smoke failure is the unchanged assertion in `codex-workspace-smoke.mjs` that `CurrentWorkPanel.tsx` contains `当前项目`; Task4 does not modify `CurrentWorkPanel.tsx` or its Work Fact behavior. The focused source/e2e/build checks are fresh and pass, but they do not close I1–I5.

## Scope and environment limits

- Review was read-only for product files; no backend, queue, parser, retrieval, vector, promotion or Task2/3 code was changed.
- No live 8766, packaged Sidecar, Artifact, Production/Vault, owner data, or third-party application was touched; `LOCAL_EXECUTION_TASK.md` remains `IDLE`.
- No product merge or release conclusion is authorized by this review.
