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
