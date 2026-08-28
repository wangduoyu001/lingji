# SDD ledger — plan: docs/superpowers/plans/2026-08-27-phase1-product-landing.md

Plan commits: 39a38d0 (initial), 650f79f (split reset closeout into reviewable Tasks 0–1)
Execution worktree: /Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory
Branch: codex/phase1-automatic-memory
Baseline: tests/test_task4_reset_promotion_transaction.py — 42 passed
Repair cap ruling: the user-authorized plan limit of two repair rounds per task governs over the generic skill cap of five.

Task 0: BLOCKED — implementation commits b909565f1a44709a6d1e6cd922adaf2908b91642..3227a279990e3977b73a8f0ba7463aeed13deeb2; independent review Spec FAIL / Quality Needs fixes.
Task 0: open Important — required transaction/recovery matrix remains incomplete.
Task 0: open Important — compatibility fallback bypasses promotion payload redaction.
Task 0: open Important — ordinary promotion payload serializer persists non-finite floats.
Task 0: breaker ruling — all three are technically verified and load-bearing for automatic memory promotion; plan forbids another repair round, so Tasks 1–9 remain blocked pending owner-approved boundary re-plan.
Task 0: minor (deferred) — direct activation collapses duplicate required refs; stable scanner accepts empty canonical string fields.
Task 0 closeout: one-shot implementation f414a4f09cb92f0c30bc5124e34112263bbce84f closed serialization blockers but independent review rejected durable recovery proof (0 Critical, 2 Important).
Task 0 final disposition: no further repair. Plan commit 5763bc9 introduces owner-review-only quarantine; Tasks 1–9 resume only after that bounded safety fallback independently passes.
Task 0 quarantine result: implementation 03b959a..9bba461 and repair 1330fff..276e60f improved the boundary, but final review retained one Critical in public reconcile for an already-active legacy projection.
Task 0 runtime ruling: state-machine repair cap exhausted. Commit 5c3bed8 moves the safety guarantee to composition: no packaged background automatic evaluate/reconcile/rebuild; explicit authenticated owner approve/reject only. Main Task 1 may resume; Task 2/3 must enforce forbidden-call sentinels.
Task 1: REPAIR_ROUND_1 — implementation 7b549ab63d752177a4572db8f78f4ea6d879f8aa, docs/report edca62e0977a59f7d7185fe49df9c6e58c90e381..1d401cc3c41509eb57a68d12ae551fa97a1e732b; review Spec FAIL / Quality Needs fixes.
Task 1 Critical: unmeasured MCP/context baseline still manufactured into EvaluationReport; Acceptance root/lease admission forgeable; historical rejection coverage deleted instead of migrated.
Task 1 Important: measured failure can downgrade on gate exception; release guard is static only; CLI lacks post-cleanup inventory verification; latent 100k missing symbol; legacy optional raw-report path remains; authority SHAs stale.
Task 1 repair scope: exactly these review findings plus setup-cleanup minor; no 4R2, retrieval, promotion, vectors, UI, Production/Vault or Artifact.
Task 1: REPAIR_ROUND_2 (FINAL) — Repair Round 1 commits 2b99cc5..d1c0185; review Spec FAIL / Quality Needs fixes (1 Critical, 6 Important, 2 Minor).
Task 1 final repair scope: restore exact historical rejection semantics/storage scans; unreadable admission; dangling-symlink cleanup; malformed-gate measured-failure precedence; executable/instrumented release ordering; truthful component SHAs and complete Task1–5 matrix; explicit enum status and cleanup-code allowlist.
Task 1 breaker: no third repair. Any Critical/Important after Repair Round 2 quarantines the quality runner/release gate and must not block composition-level runtime/UI work indefinitely.
Task 1 FINAL BLOCKED — Repair Round 2 product/tests 5f75e3af9b2269519337de68db6a688bd4e654f0, evidence/docs through 956483b2655fca4a386f9a21bf1a3a46c09d2862; final review Spec FAIL / Quality Needs fixes (0 Critical, 2 Important).
Task 1 verified strengths — complete reset matrix 336 passed; admission/cleanup/measured-failure/history/evidence findings closed.
Task 1 remaining Important — actual PowerShell release entry not executable/instrumented on this host; runner-stage exceptions do not always publish fresh truthful NOT_EVALUATED envelopes.
Task 1 final disposition — repair cap exhausted. Quality runner, 4R2, release, 100k and Artifact remain composition-quarantined. Tasks 2–6 runtime/ingestion/Work Fact/UI may proceed without using or claiming this gate. Task 7/8 remain blocked pending a later independent runner-error-envelope/release-entry task.
Task 2 root decisions — heartbeat age is null with explicit unavailable reason (no fake timestamp/daemon); one DB means one canonical state DB path plus one shared queue wrapper, multiple connections to that file allowed; snapshot terminal consumption remains Task 3.
Task 2: REPAIR_ROUND_1 — implementation cbee300f519f66a2a090561a71ea4c21fb1057d7..2200c52c5d0a0d764e4545e25bd29c7431a61ffb; review Spec FAIL / Quality Needs fixes (0 Critical, 4 Important, 1 Minor).
Task 2 repair scope: start/stop exception cleanup and truthful surviving-thread state; live authorized-source attach; executable real packaged composition test; watcher exit verification; never-started pause status.
Task 2 approved minimal file expansion: existing `src/automatic_memory/scheduler.py`, `source_registry.py`, `watcher.py` and `src/extraction/worker.py` may change only to expose/complete lifecycle ownership and dynamic authorization; no discovery, snapshot consumer, adapter, Work Fact, UI or promotion changes.
Task 2: REPAIR_ROUND_2 (FINAL) — Repair Round 1 bc34b9da3427906810a46e32fcccd6d5efe4f680..8e7e07393cd86ec90a84f5a82e561b7801cedd6f; review Spec FAIL / Quality Needs fixes (0 Critical, 2 Important).
Task 2 final repair scope: non-blocking revoke with truthful surviving-watcher evidence/retry; canonical state-path validation for injected registry/scheduler; executable packaged-wrapper subprocess composition test with real lifecycle and only network boundary stubbed.
Task 2 breaker: no third repair. Any remaining Critical/Important after Repair Round 2 triggers runtime composition quarantine and root re-plan.
Task 2 FINAL BLOCKED FOR RELEASE — Repair Round 2 product/tests 593b7d0, evidence/docs through 585b714; final review Spec FAIL / Quality Needs fixes (0 Critical, 1 Important).
Task 2 verified strengths — real packaged startup, canonical state DB/queue, scheduler/worker/watcher ownership, live authorized-source attach, truthful null heartbeat reason, focused 32 passed, broader 167 passed, runtime smoke PASS.
Task 2 remaining Important — after an initially surviving watcher exits, retry can leave a stale scheduler cleanup error and report degraded/cleanup_pending instead of stopped.
Task 2 final disposition — no third repair. Tasks 3–5 may use normal runtime/admission behavior but must show this edge as degraded/needs restart and never as stopped. Exact sidecar process exit is the terminal cleanup boundary. Task 6/release/Artifact remain blocked pending a separate lifecycle closeout.
Task 3: READY — connect metadata-only discovery, safe authorized enumeration, snapshot consumption, existing adapter extraction and truthful Work Fact terminal outcomes. No Task 2 lifecycle repair, UI, promotion background seam, retrieval/vector, quality runner, Artifact or Production/Vault work is in scope.
Task 3: REPAIR_ROUND_1 — implementation bc3636a, evidence/docs 0d7bb84; independent review Spec FAIL / Quality Needs fixes (0 Critical, 8 Important).
Task 3 repair scope — terminalize revoked/invalid internal jobs; keep ordinary Obsidian bodies unread; block sensitive JSON name variants; real repeated-scan/idempotency and truthful queued/reused counts; dispatch /scan through runtime; align Work Fact source/status; correct report SHAs/whitespace; prevent automatic chat Markdown writes to configured owner Vault while retaining raw plus structured rows.
Task 3 owner boundary — configured Obsidian Vault is manual memory UI/input, not automatic AI-chat archive output. No automatic chat snapshot may call VaultExtractionSink or create/update Vault Markdown. No new store/parser/queue/API/indexer is authorized.
Task 3: REPAIR_ROUND_2 FINAL — Repair Round 1 product f2f7312, evidence 4e5d744, metadata correction 95cfc90; review Spec FAIL / Quality Needs fixes (0 Critical, 4 Important).
Task 3 final repair scope — CRLF/BOM frontmatter explicit-deny correctness; cross-source Generic History structured identity namespace with same-source replay stability; truthful 30%/70% resume checked counts; exact three-SHA evidence attribution. No third repair is authorized.
Task 3 Repair Round 2 behavior — product 7058da0, evidence b83232d, metadata correction 843b9cb; final independent review reproduced all behavioral requirements with 223 passed and no Critical behavior finding.
Task 3 final review evidence-only finding — report/acceptance omitted the already-existing metadata correction SHA 843b9cb. Root accepted no third product repair and performed only the authorized evidence attribution follow-up; product Head and behavior remain unchanged.
Task 3: ACCEPTED_FOR_TASK4 — final behavioral matrix 223 passed; product 7058da0, evidence b83232d, metadata 843b9cb, evidence closure 6a17ddb. Independent evidence closure PASS. No Artifact/release claim; Task1/Task2 quarantines remain.
Task 4: READY — implement the one-time Chinese onboarding and truthful source/activity UI using only existing authenticated 8766 Task3 APIs. No backend feature expansion, fake status, static success, Artifact, Production/Vault or live owner acceptance.
Task 4C: IMPLEMENTED_FOCUSED_PASS — bounded Home fact closure based on final Task 4 review `f3d70084e8dfb8a07e2fe46f7e1008e11cdf7c2d`. Product/test commit `4aa0b7841dab76fed5c784008c2449808e3648f2` adds `本次更新`/`本次跳过` with truthful numeric-or-`尚未获得` rendering and removes the unmeasured `后台自动运行` fallback. RED was reproduced by static and rendered assertions; focused UI/runtime/source/inspector/work-fact checks, build and rendered E2E are green. No backend/API/other-page/CurrentWorkPanel/live service or owner data was touched; the unchanged legacy smoke baseline remains disclosed.
Task 4: ACCEPTED_FOR_TASK5 — Task 4C independent review `3eaefc807402cc7bda8cc2e999189b6b483d5434` returned Spec PASS / Quality PASS with no Critical, Important or Minor finding. Chinese onboarding, source authorization/control, truthful scan states, outage recovery, Home five-question facts and unknown-value handling are accepted for Task 5 composition only. No release, Artifact, live 8766, Production/Vault or owner acceptance claim is authorized.
Task 5: READY — make the existing owner workflow understandable and actionable through the current WorkStore, authenticated 8766 routes and Desktop pages. No new memory capability, store, queue, API family, retrieval/vector behavior, Artifact or live owner data is in scope.
Task 5A: IMPLEMENTED_FOCUSED_PASS — Owner Work API foundation. Product/tests `f799b8aed526b52b259a360b7162ceef9b86b0a3` adds bounded history pagination, chronological timeline projection and authenticated idempotent pending-action resolution through the existing WorkStore. RED was 4 behavioral failures; focused backend matrix is 36 passed, 2 warnings. Independent review pending; no UI, Artifact, live 8766, Production/Vault or owner data touched.
Task 5A Repair Round 1: IMPLEMENTED_FOCUSED_PASS — final authorized repair product/tests `5e71cda68edfb86eac99804bc66fbfb6540bcb9c`; RED 3 behavior failures, focused matrix 40 passed/2 warnings, broader Work/Task8/Capture/automatic-memory Work Fact matrix 102 passed/2 warnings. Resolve now atomically removes only the matching stale owner next action and source summaries are readable/distinct with exact IDs secondary. Independent final review required; no UI/Artifact/live service/owner data.
Task 5B: IMPLEMENTED_FOCUSED_PASS — Desktop Activity now reads paged `/api/work/history` with Chinese summaries and folded diagnostics; Attention resolves real pending actions; Memory Review/Inspector expose readable available provenance and real inspection navigation; duplicate legacy Capture is hidden while compatibility route remains; copy feedback and 900px layout are covered. RED was reproduced by the fake-8766 rendered flow; GREEN build, UI smokes, rendered E2E, Task5A backend (40) and broader Work/Task8/Capture (102) regressions pass. No live 8766/Sidecar/Artifact/Production/Vault/owner data; independent review still required.
Task 5B Repair Round 1: IMPLEMENTED_FOCUSED_PASS — review `9272e60fc5fa4b485831e101f5f1a66573f1498d` findings I1/I2 closed. RED reproduced delayed Memory Review loading failure; GREEN now covers honest list/detail loading, stale detail response protection, and strict `_read_candidate()` DTO provenance mapping with unavailable fields rendered as `尚未获得`. UI/build/rendered and Task4/Task5A regressions pass; M1/M2/M3 evidence minors remain disclosed. No backend, live 8766, Sidecar, Artifact, Production/Vault or owner data.
Task 5B final review disposition: `ACCEPTED_FOR_TASK6` / `ACCEPT_FOR_TASK6`; final review commit `bd2ff43`, reviewed product head `8136374`, Critical=0, Important=0, Minor=3 non-blocking evidence gaps. No live 8766, Sidecar, Artifact, Production/Vault or owner data.
Task 6A Lifecycle Closeout: IMPLEMENTED_FOCUSED_PASS — bounded Task2 final-disposition follow-up only. Product/tests commit `15eb4433c9d6c3ba218e89d50bec84987ad35915`; report `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6a-report.md`. Real watcher/event RED reproduced stale scheduler cleanup error after a late natural exit; GREEN clears stale errors on the second stop/retry, serializes concurrent cleanup and preserves degraded truth while a watcher survives. Task2 lifecycle blocker is closed for Task6 composition; independent Task6A review pending, so Task6/release/Artifact remain unclaimed. No live 8766/8767, Sidecar, Artifact, Production/Vault or owner data.
Task 6A Repair Round 1 (final authorized repair): IMPLEMENTED_FOCUSED_PASS — independent review `9ed229461165b748066b9cba3d2ed169af43db56` I1/I2 addressed in product/tests `efde650e77a4ecda7f7266aefe48b29b9e8712de`. Real thread/Cron seams prove failed Cron cleanup is retried, unrelated source errors survive, and start/stop share lifecycle serialization. Repair seams `3 passed`; Task2 broader matrix `171 passed, 6 warnings`; Task3/4/5 matrix `77 passed, 2 warnings`; smoke/static/sync/handoff PASS. This is the final repair; remaining Critical/Important after fresh review means `BLOCKED_AT_REPAIR_CAP`. No live 8766/8767, Sidecar, Artifact, Production/Vault or owner data.
Task 6H Durable Heartbeat: IMPLEMENTED_FOCUSED_PASS — existing StateDB now holds one mutable heartbeat row per scheduler `instance_id + generation`; existing Cron loop wakes at a bounded <=5s heartbeat cadence while reconciliation polling/claim remains on its original cadence. Runtime/API exposes UTC `scheduler_heartbeat_at`, computed age, reason, instance, generation and state; pause continues heartbeat, stop writes stopped, stale/clock-jump/read-write failure is degraded. Active scan Work Facts refresh directly without event rows. RED `3 failed`; GREEN `tests/test_task6h_heartbeat.py` `6 passed`; Task2 lifecycle/API `50 passed, 1 warning`; control/packaged `21 passed, 6 warnings`. Idle measured age <=1s; 0.05s heartbeat over 0.25s produced one claim; Task6 remains NOT_ACCEPTED pending packaged crash matrix and fresh review. No live 8766/8767, Sidecar, Artifact, Production/Vault or owner data.
Task 6H Repair Round 1 (final): IMPLEMENTED_FOCUSED_PASS — independent review `8daf700f4dd5dbea90e32305a67c764420b147d7` I2 closed. Active Work Fact touch failures are isolated per source, persisted as degraded heartbeat reason/last_error, do not kill scheduler/scans, and recover with the next successful refresh; UI DTO/status copy distinguishes degraded/stopped/paused/running/unknown. New RED reproduced false running; GREEN focused `8 passed`, including source isolation and unchanged event count. Packaged crash 30/70 terminal identity mismatch remains an external Task6 gate and was not changed. No live 8766/8767, Sidecar, Artifact, Production/Vault or owner data.

Task 6C Deterministic Crash-Recovery Receipt: PASS_AUTOMATED / READY_FOR_TASK7 —
test-only commit `6eb469fefafe0a33e6ac65f765c7663741883811`; report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6c-report.md`. The
required RED was `1 failed, 1 passed, 1 warning` from the old `2 != 1` terminal
identity race; diagnosis separated the original crash scan from a normal audit
scan and removed dummy-PID/manual-POST race. Two fresh complete packaged runs
were `2 passed, 1 warning` in `265.89s` and `2 passed, 1 warning` in `266.73s`.
All ten scenarios passed raw in both runs. Four dedicated crash receipts (two
clean roots per round) used real sidecar PID kills at 6/20 and 14/20; each
recovered the same scan by startup reconciliation, completed 20/20, had 20 jobs,
zero duplicates, zero queued residue, matching logical identity/raw-hash parity,
and verified process/port/log/temp cleanup. Task6S lexical/Qdrant and Task6H
heartbeat age `<=10s` are included. Focused Task6H/S/A plus scheduler,
checkpoint, lease, cron, startup recovery was `155 passed, 2 warnings`; Desktop,
compile, diff, sync and handoff gates passed. Acceptance-only evidence only:
no release, Artifact, live service, Production/Vault, owner PASS; fresh security
review remains required.

Task 6C Repair Round 1: BLOCKED / NOT_ACCEPTED — fresh review
`3fd8059da4ed10b8a1fcd0581793bd0fb2d177ee` 的 `-x` packaged rerun 在真实
crash/recovery/stop 后发现 `.automatic-memory-*.json` transient marker 仍在
raw 目录（2,640,287 bytes）。现有产品 cleanup 只回收 `.snapshot-owned-*`；
测试 harness 不得 unlink 该 marker 伪造 PASS。未授权产品扩展，未提交未验证
harness 改动，已恢复测试至 `6eb469f`；Task6 不能进入 READY_FOR_TASK7。

Task 6M: IMPLEMENTED_FOCUSED_PASS — new bounded product fix (not Task6C Repair 2).
Product/tests `1901628eee197e3d71d7e070c41c9e586d5468de` bind adapter dispatch markers to existing
extraction queue `job_id + lease_token`, reconcile direct-child
raw regular files at pipeline startup/process/worker stop, preserve active or
unprovable files, and expose cleanup inventory through existing pipeline/worker
status. RED collected before the transient production boundary existed; GREEN
`tests/test_task6m_transient_lifecycle.py` is `8 passed`, including real subprocess
SIGKILL and restart reconciliation; affected snapshot/resume/adapter/worker/runtime/
scheduler regressions are `150 passed, 3 warnings`. No live 8766/8767, Artifact,
Production/Vault or owner data; Task6 remains `IN_PROGRESS / NOT_ACCEPTED` pending
fresh independent review and final validation.
Task 6M independent review: `Spec Compliance FAIL / Task Quality NEEDS_FIXES`,
0 Critical, 5 Important, 2 Minor. Findings: legacy unversioned markers are
permanently preserved (including the known Task6C residue), queued/retrying and
terminal branches delete lease-mismatched markers, queue/DB errors escape before
an existing runtime receipt is exposed, cleanup inventory is not consumed by
Desktop, and the post-fix packaged 30/70 crash gate is not fresh. Path-swap and
failure-cleanup coverage remain Minor evidence gaps. `REPAIR_ROUND_1 authorized`;
Task6 stays `IN_PROGRESS / NOT_ACCEPTED` and
must not be marked `ACCEPTED_FOR_FINAL_VALIDATION`.

Task 6M Repair Round 1: IMPLEMENTED_FOCUSED_PASS — review `b65f81d` I1/I2/I3/I5
and M1/M2 closed in product/tests `4b51392fe448472e9099978ff2528f742dff887b`.
RED was `8 passed, 4 failed`; GREEN lifecycle/runtime was `31 passed, 1 warning`,
Desktop source smoke PASS and Desktop TypeScript/Vite build PASS. Legacy markers
now require exact grammar plus same-directory content-addressed raw hardlink
proof; v1 deletions require queue job input/raw identity proof; queue/SQLite
errors fail closed into existing cleanup receipts; pre-unlink identity changes
are retained; Desktop shows the bounded Chinese cleanup retry notice and hides
paths/job/lease tokens. Affected snapshot/resume/queue/worker/runtime/Work Fact/
adapter/structured/Task6A/6H/6S/Task8 regression matrix is `250 passed, 3
warnings`. I4 fresh packaged 30/70 remains deferred to new Task6V; Task6 stays
`IN_PROGRESS / NOT_ACCEPTED`, with no live/Artifact/Production/Vault/owner data.
Task 6M Repair Round 1 final independent review (2026-08-28): report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-final-review.md`
against docs HEAD `28f798557459b7cd7a1187d462969e43c871450a` and product/tests
`4b51392fe448472e9099978ff2528f742dff887b` is `FAIL / BLOCKED_AT_REPAIR_CAP`
with Critical=0, Important=2 (terminal/queued/retrying WRONG-lease markers can
still be removed; filesystem scan errors are not fully fail-closed/sanitized),
and Minor=2 evidence gaps. Fresh lifecycle/runtime is `31 passed, 1 warning`,
affected regression is `250 passed, 3 warnings`, Desktop smoke/build and the
maintained rendered flow pass. I4 packaged 30/70 remains explicitly deferred to
a new Task6V and is not scored as a repair-product failure. Task 6M remains
`NOT_ACCEPTED`; Task6 remains `IN_PROGRESS / NOT_ACCEPTED`; no further repair is
authorized.

Task 6L independent review (2026-08-28): report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-review.md` at
`880bd8c1beeddfda0b0c76752038ca7da521adfe` is `FAIL / NEEDS_FIXES` with
Critical=0, Important=1, Minor=0. Fresh focused/regression is `218 passed, 2
warnings`; Desktop static/build/rendered, compile, diff, sync and handoff pass.
I1: ordinary low-level queue `get()`/`list()` (plus equivalent raw reads) still
expose plaintext `lease_token` and durable `last_claim_lease_fingerprint`, even
though public Control/Capture/MCP DTOs redact them. Task6L is `NOT_ACCEPTED`;
one bounded Repair Round 1 is authorized. Task6M remains
`FAIL / BLOCKED_AT_REPAIR_CAP`; Task6 remains `IN_PROGRESS / NOT_ACCEPTED`.

Task 6L Repair Round 1 final independent review (2026-08-28): report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-final-review.md`
against reviewed HEAD `d328e58926e0466a912bde8c73fbaa5f64633cf5` and repair
product/tests `2daac0733495798f3e576363a885c28e8c4ce392` is `FAIL /
BLOCKED_AT_REPAIR_CAP`, Critical=0, Important=1, Minor=0. Fresh backend matrix
is `219 passed, 2 warnings`; Task6L focused is `12 passed`; Desktop
static/build/rendered, compile, diff, acceptance sync and local handoff pass.
The field names are absent from ordinary `get/list/list_page/get_by_idempotency_key`
and claim has no public Control/MCP route, but after complete/fail clears the
current token, arbitrary nested result values and `last_error` can still carry
the old plaintext lease token. Task6L remains `NOT_ACCEPTED`; Task6 remains
`IN_PROGRESS / NOT_ACCEPTED`; Task6M historical `FAIL / BLOCKED_AT_REPAIR_CAP`
is unchanged and no further repair is authorized in this round.

Task 6P Queue Persistence Lease Redaction (new bounded task): the Task6L I1 root
cause is addressed at the existing queue persistence seam. RED was `3 failed`;
the shared scrubber now removes only explicit lease keys/aliases, replaces known
token/fingerprint values, and fails closed on cycles, depth, node count, and
oversize values without repr serialization. complete/fail/cancel-running scrub
before clearing current lease in one transaction; enqueue/force payload/options
and pipeline/MCP/process summaries, callbacks, and logs reuse the boundary.
Task6P focused is `5 passed`; queue/worker/pipeline regressions are `77 passed,
2 warnings`; expanded Task6L/M/P/runtime/Control/MCP/structured/Work matrix is
`241 passed, 2 warnings`. Desktop source/static/build/rendered, compile,
diff-check, acceptance sync, and local handoff pass. Task6L/M dispositions are
preserved; independent review remains required and Task6 stays
`IN_PROGRESS / NOT_ACCEPTED`.

Task 6P independent review (2026-08-28): report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-review.md` against
reviewed HEAD `815a3bb5c0d245f6f33a984e7349e927b0090418` and product/tests
`19525638ba3f33223fac005aa258f33dd2eb6091` is `FAIL / REPAIR_ROUND_1_AUTHORIZED`,
Critical=0, Important=1, Minor=0. Fresh Task6P focused is `5 passed`; expanded
backend is `279 passed, 3 warnings`; Desktop source/rendered/build, compile,
acceptance sync and local handoff pass. I1 remains: pipeline lifecycle callbacks
receive the internal claimed job with plaintext `lease_token`; direct execute
callbacks also pass explicit nested lease keys unchanged. At most one bounded
lifecycle projection repair is authorized. Task6P remains `NOT_ACCEPTED` and
Task6 remains `IN_PROGRESS / NOT_ACCEPTED`; Task6L/M historical dispositions,
packaged 30/70, live, Artifact, release, Production/Vault and owner acceptance
are unchanged.
Task 6P Repair Round 1: product/tests `924ac0c433a5d1029cce456cec1e6f24ef7dc7ba`
closes review I1 at the sole `_notify_lifecycle` boundary. Callback job/result/error
now receive fresh bounded safe projections with explicit lease-key value collection;
custom-object scrub failures fail closed without rolling back terminal queue state.
Ordinary, automatic, direct execute success/failure callbacks are covered. Task6P
focused is `10 passed`; expanded matrix is `354 passed, 2 deselected, 6 warnings`
after excluding two pre-existing structured-evidence fixture failures. Task6
remains `IN_PROGRESS / NOT_ACCEPTED` pending fresh independent review.

Task 6P Repair Round 1 final independent review (2026-08-28) is recorded in
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-final-review.md`:
`FAIL / BLOCKED_AT_REPAIR_CAP`, Critical=0, Important=1, Minor=0. Fresh focused
is `10 passed`; affected backend is `266 passed, 7 warnings`; complete pytest
without deselection is `1359 passed, 11 skipped, 7 failed`. The two existing
structured-evidence `vault_path` fixture failures reproduce on both repair tree
and base `d61acdf`. Desktop source/repair/build/rendered, compile, diff, sync and
handoff pass. I1: arbitrary unbounded explicit lease-key values are collected
and globally substituted in callback正文, so `lease_token: "a"` over-redacts
ordinary text. Task6P remains `NOT_ACCEPTED`; Task6 remains
`IN_PROGRESS / NOT_ACCEPTED`; no further repair is authorized.

Task 6V packaged closeout (2026-08-28): after product HEAD
`684398e2b56447203ff6b77b4e93cae2c07b38f2` fixed terminal
`snapshot-owned` cleanup, the existing acceptance harness was tightened for
transient/raw inventory, natural identity/status parity, measured process and
port cleanup, lease-barrier startup recovery, and deterministic rendered
readiness. No `src/` or Desktop product code changed. Two independent complete
packaged invocations each passed `2 passed, 1 warning` (294.47s and 295.59s),
covering ten scenarios and real 30%/70% crash/restart roots. Task6Q/H/S/A plus
Task2–5 focused regression passed `376 passed, 3 warnings`; Desktop build,
smokes, rendered E2E, compile, diff, acceptance sync and local handoff passed.
Task6 automated disposition is now `AUTOMATED_ACCEPTED / READY_FOR_TASK7` only;
release, Artifact, live 8766/8767, Production/Vault and owner acceptance are
not run, and `LOCAL_EXECUTION_TASK.md` remains `IDLE`.
