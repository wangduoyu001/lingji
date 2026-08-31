# SDD ledger — plan: docs/superpowers/plans/2026-08-29-owner-real-history-memory-cards.md

Base product head: `e410b4a5c884819b06df1fd054b14fe0fd774d70`
Plan/acceptance commit: `68f8581`
Pre-flight review: no task/global-constraint conflicts found.
Owner contract: concise memory cards; exact totals; source/freshness/raw-structured-vector-permanent state; safe confirm/correct/invalidate/archive; original text only on demand.
Task 1: fix round 1/5 (5 addressed, 3 open — effective HOME runtime continuity; automatic adapter trusted-input binding; full sentinel/replay/authorization-action evidence; commits c4541ad..a747ad4)
Task 1: fix round 2/5 (2 addressed, 1 open — API user_home effective-home propagation; commits a747ad4..d50e9ee)
Task 1: fix round 3/5 (last Important addressed — shared effective-home semantics and API-to-runtime proof; commits d50e9ee..30b6857)
Task 1: COMPLETE — independent review PASS; Critical 0, Important 0; real owner data/live app not touched.
Task 2: implementation c180fda reviewed; REPAIR_ROUND_1 — Critical 0, Important 7 (evidence grounding, promotion/lifecycle, per-card vector, provenance, temporal/source-state correctness).
Task 2: fix round 1/5 (7 Important + 2 Minor addressed, 1 Important + 1 Minor open — active terminal event must not fall back to older pending; malformed-vector test reachability; commits c180fda..fddcdf1).
Task 2: fix round 2/5 (terminal/pending fallback addressed; 1 Important remained — structured layer fail-closed with missing canonical projection; commits fddcdf1..2fc6a5b).
Task 2: fix round 3/5 (last structured-layer inconsistency addressed; commits 2fc6a5b..f58d988).
Task 2: COMPLETE — independent review PASS; Critical 0, Important 0, Minor 0; focused 18, targeted 2, direct regression 104 passed.
Task 3: UI/IA contract refined at 9a3e560 — four ordinary menus, advanced diagnostics demoted, concise responsive cards and real-control acceptance.
Task 3: initial implementation 21ad4ae + evidence 179bf3f; independent review REPAIR_ROUND_1 — Critical 0, Important 8, Minor 2. Initial implementation agent exhausted quota after clean commits; no work lost.
Task 3: fix round 1/5 f34b6f9 + f41673f; re-review still FAIL — Critical 0, Important 9, Minor 2. Previous I1-I8/M1-M2 partially/fully addressed, but real projector/action/retention/request-boundary tests exposed remaining gaps. Proceeding bounded round 2, no feature expansion.
Task 3: fix round 2/5 10287c2 + e75d7cf + 82f5cd7; re-review reduced to Critical 0, Important 4, Minor 1 — rendered status/projector evidence, real API-to-service integration, reproducible count, archived dead action, provenance fail-closed. Proceeding bounded round 3 only.
Task 3: fix round 3/5 ae01b24 + b24f1ca; re-review reduced to Critical 0, Important 1, Minor 0 — rendered detail fixture must preserve non-mutation history/not-permanent states instead of falling back to correct. Proceeding tiny round 4 only.
Task 3: fix round 4/5 7ccbc02 + b67d1bb; final independent review PASS/APPROVED — Critical 0, Important 0, Minor 0; focused 85, E2E PASS, 23 smoke PASS.
Task 3: COMPLETE — code and synthetic acceptance only; live Mac/release/owner data remain Task 4.

2026-08-31 live repair: packaged candidate `43009a0d` was observed as
`OWNER_UI_REPAIR_REQUIRED` because Home exposed raw automatic-memory source
titles/English unsupported error and Memory Sources duplicated Codex under
macOS `/tmp` versus `/private/tmp`. Product/tests candidate
`6ea11e491868e227a0c454e87f73ebd92a99b788` repairs only owner presentation and
source-key aliasing. Focused, build, rendered E2E and 23-script smoke are PASS;
new isolated Mac acceptance is pending and is not release/Phase 1 evidence.
