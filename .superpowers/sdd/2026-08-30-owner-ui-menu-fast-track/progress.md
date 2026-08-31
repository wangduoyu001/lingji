# SDD ledger — plan: docs/superpowers/plans/2026-08-30-owner-ui-menu-fast-track.md

Base: 81c813364985a223ce777592649154bbe9778580
Task 1: review FAIL / NEEDS_FIXES — 0 Critical, 6 Important, 2 Minor
Task 1: fix round 1/5 started — source aggregate counts; raw error/port leakage; pending-route coverage; sync/handoff evidence
Task 1: fix round 1/5 (5 addressed, 1 open — scan aggregate mislabeled/limited to list length; commits 7f97839..92cdc76)
Task 1: fix round 2/5 started — replace scan list length with truthful existing aggregate or honest unknown
Task 1: fix round 2/5 (1 addressed, 0 open — trusted completed aggregate or honest unknown; commits 92cdc76..6baf4ee)
Task 1: complete (commits 81c8133..6baf4ee, scoped review clean; 2 original Minors deferred for final review)
Task 2: dispatched — Mac owner UI experience candidate
Task 2: owner observation FAIL — source/pending activation inconsistency; top health mislabeled; null conclusions make cards unreadable
Task 2: repair round 1/5 dispatched — bounded ordinary UI repair only
Task 2: repair round 1/5 review FAIL (0 Critical, 2 Important, 2 Minor)
Task 2: minor (deferred): stale/conflict detail assertions are defined but not executed
Task 2: minor (deferred): hidden cadence coverage does not separately exercise Overview and Attention
Task 2: repair round 2/5 started — manual pause guard and malformed pending-action validation
Task 2: repair round 2/5 (2 addressed, 0 open — manual pause and malformed pending actions; commits 06e9c8d..b299e5b)
Task 2: product repair approved — rebuild exact HEAD and repeat Mac owner traversal pending
Task 1: minor (deferred): technical-string deny assertions are narrower than the full ordinary-view deny list
Task 1: minor (deferred): focused smoke should always close Playwright browser on assertion failure
Task 2: pending — Mac owner UI experience candidate; only after Task 1 PASS/APPROVED

Deferred by owner priority: frozen 100-question/4R2 repair, 100k, Windows and formal release gate remain MEASURED_FAIL / NOT_RELEASE_READY and are not part of this UI round.

## 2026-08-31 · source/conclusion repair final review

Product commits `8ec447e06a846c3c3edb345ae979b5ee65fb7379` and
`4ce1e00acb17bc5e4e4c183f58d30551ef76b101` received a fresh read-only review. Source
discovery keeps raw `not_found` diagnostics while the ordinary projection filters
unauthorized not-found candidates; authorized/revoked lifecycle, visible count, supported
statuses, and macOS alias boundaries are preserved. Existing owner conclusions now survive
the relationship projection with entry-over-properties precedence, shared list/detail output,
and verified-evidence fail-closed gating. No new source/table/architecture was introduced.

Review disposition: `PASS / APPROVED`, Critical 0, Important 0, Minor 0. Fresh evidence:
36 focused Python tests (1 warning), source smoke, owner fast-track smoke, rendered memory
E2E, full 23-script Desktop smoke, build, affected compileall and diff-check all passed.

The prior `6ea11e4` Mac source-page failure remains read-only evidence. The unique next ACTIVE
task is `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A` at exact product commit
`4ce1e00acb17bc5e4e4c183f58d30551ef76b101`, with new root
`/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a`. Mac rebuild, full-root Computer Use,
owner confirmation and final cleanup remain pending. Its seed is fixed at 37 cards (3 history),
13 permanent, 3 conversations, 36 messages and exactly one owner high-risk pending action,
with at least eight varied synthetic conclusions and no manufactured automatic-scan failure pending.

## 2026-08-31 · reviewed redesign candidate

Product/tests commit `43009a0dfdf3cd7b949d871cc9054286f17d607e` is reviewed and ready for a fresh Mac owner-experience run. Current-only card pagination, 20-second offset-preserving refresh, four compact accessible primary labels, Overview scope copy, and Attention confirmation wording are covered by rendered E2E and smoke. RED was the page-two reset (`20 !== 16`); GREEN passed all requested automated validations. Mac acceptance is newly activated as `OWNER_UI_REDESIGN_MAC_43009A0D`, with old failed evidence retained and no release/Phase 1 claim.
