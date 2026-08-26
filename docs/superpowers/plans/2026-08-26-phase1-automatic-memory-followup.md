# Phase 1 Automatic Memory Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining Work Fact consistency defect, prove LingJi's memory quality with a fixed 100-question corpus, unify RAG/ContextPack/MCP, and pass Mac-first release acceptance before Windows parity.

**Architecture:** Keep the existing `lingji_state.db`, `lingji_memory.db`, Qdrant, extraction queue, `MemoryGateway`, authenticated `127.0.0.1:8766` Local Control API, and formal Desktop. Work Fact terminal transitions become one transactional projection used by both live callbacks and crash replay; RAG continues through the existing ContextPack and gateway rather than adding another retriever. Synthetic acceptance fixtures prove quality without reading the owner's real chats.

**Tech Stack:** Python 3.12, SQLite, existing FTS5/Qdrant/HybridRetriever/MemoryGateway/MCP, FastAPI, React/Tauri, Node smoke scripts, pytest, PowerShell 5.1-compatible validation scripts.

## Global Constraints

- The detailed execution authority for remaining Phase 1 work is this plan; `2026-08-26-phase1-automatic-memory.md` remains the completed Tasks 0–7 historical baseline.
- Root agent writes plans, dispatches Luna, checks evidence, adjudicates reviews, and performs final acceptance only. Root does not write product code or repair Luna's implementation.
- Every implementation task uses a fresh `gpt-5.6-luna` implementer, TDD RED/GREEN evidence, one task-scoped commit set, and an independent fresh `gpt-5.6-luna` spec-and-quality review.
- A task may enter at most five reviewed repair rounds. Rounds 1–3 resume the implementer; rounds 4–5 use fresh Luna context. A remaining load-bearing finding trips the breaker and blocks dependent tasks.
- Never add a second database, extraction queue, scheduler, retriever, gateway, API, Desktop, configuration authority, or permanent-memory fact source.
- Never read or modify tokens, cookies, credentials, browser profiles, private app databases, opaque Claude storage, third-party app configuration, or third-party app processes.
- Obsidian ordinary notes remain excluded. Only `_LingJi/Memory Inbox`, `_LingJi/Memory Library`, or `lingji_memory: true` are eligible; `lingji_memory: false` always wins.
- Default retrieval mode is `current`. `superseded`, `invalidated`, and `archived` facts may appear only in explicit `as_of`, `history`, or `why` modes.
- ContextPack hard limit is 12,000 Unicode characters after final rendering, including citation text. No truncation may produce a broken citation or partial record.
- Quality gates are: 100/100 questions executed; valid-fact recall at least 90%; citation accuracy at least 95%; automatic activation accuracy at least 95%; Core/high-risk false promotion 0; stale-current leakage 0; duplicate source/session/message/memory records 0; ContextPack reduction at least 90% against the complete relevant-chat baseline.
- Mac M5 must pass before Windows acceptance begins. Real installation/UI/reboot/owner checks require an `ACTIVE` `LOCAL_EXECUTION_TASK.md`; no Luna or root agent may infer an Artifact from an IDLE task.
- `release` already contains `full`; the same tree must not run `full` immediately before `release`.

---

### Task 1: Work Fact Lifecycle Consistency Closeout

**Purpose:** Replace duplicated callback/replay mutations with one state transition so Desktop cannot show “completed” and an unresolved owner action at the same time.

**Files:**
- Modify: `src/work/store.py`
- Modify: `src/work/capture_bridge.py`
- Modify: `src/control/capture.py`
- Modify only if the shared DTO must expose the resulting state: `src/work/projector.py`
- Modify: `desktop/lingji-control/package.json` (register the existing `scripts/work-fact-smoke.mjs` as `test:work-fact`)
- Test: `tests/test_task8_work_transition_matrix.py`
- Test: `tests/test_task8_extraction_work_lifecycle.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Update: `docs/PROJECT_STATUS.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK8_WORK_TRANSITION_CLOSEOUT.md`

**Interfaces:**
- Add `WorkStore.apply_extraction_transition(work_id: str, phase: Literal["retrying", "completed", "failed"], *, summary: str, evidence: Mapping[str, Any], stage: str = "extraction", retryable: bool = False, occurred_at: str | None = None) -> None`.
- `CaptureWorkBridge.complete_extraction`, `CaptureWorkBridge.record_failure`, the retrying callback in `CaptureControlService._on_pipeline_lifecycle`, and `WorkStore.reconcile_extraction_jobs` must delegate to that method.
- `desktop/lingji-control/package.json` maps `test:work-fact` exactly to `tsx scripts/work-fact-smoke.mjs`; no second smoke implementation is created.
- The method performs one transaction under the existing `StateDatabase` lock. Stable IDs remain `work:<work_id>:extraction.completed`, `work:<work_id>:failed:<stage>`, `next:<work_id>:retrying|completed|failed`, and `owner-failure:<work_id>`.
- State invariants:
  - `retrying`: current next actor `system`; zero unresolved owner actions; no new terminal outcome.
  - `failed` with `retryable=False`: current outcome `failed`; current failure present; exactly one unresolved `owner-failure:<work_id>`; next actor `owner`.
  - `completed`: current outcome `completed`; current failure hidden by projector; zero unresolved owner actions; next actor `system`.
  - Repeating the same transition, replaying it after the callback, or running callback after replay changes no stable ID and creates no duplicate event/action.
  - `occurred_at` is compared as a parsed ISO-8601 instant normalized to UTC; legacy naive timestamps are interpreted as UTC. An older transition cannot regress `completed` to `failed`; equal timestamps use terminal precedence `completed > failed > retrying`; malformed incoming timestamps cannot replace a well-formed current terminal fact.

- [ ] **Step 1: Write a literal table-driven matrix in `tests/test_task8_work_transition_matrix.py` covering new→retrying, new→failed, failed→retrying, failed→completed without reopening `WorkStore`, retrying→completed, repeated failed, repeated completed, callback→replay, replay→callback, restart→replay, and older-failure-after-completed. Assert outcome, visible failure, next actor/action ID, unresolved owner-action count, terminal-event count, and unchanged IDs.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_task8_work_transition_matrix.py`; expect RED because `apply_extraction_transition` is absent and immediate failed→completed leaves one unresolved owner action. Save the exact failing assertions in the task report.**
- [ ] **Step 3: Implement the single transactional transition and replace duplicated terminal writes in bridge, callback, and replay. Do not change queue terminal semantics, duplicate-capture identity, Desktop visuals, source scanning, or memory promotion.**
- [ ] **Step 4: Run the matrix until GREEN, then run `./.venv/bin/python -m pytest -q tests/test_capture_work_bridge.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_fact.py tests/test_work_control_api.py tests/test_work_control_service.py tests/test_task8_work_transition_matrix.py`; require zero failures and no new warning category.**
- [ ] **Step 5: Run `cd desktop/lingji-control && npm run test:work-fact && npm run build`, then `./.venv/bin/python scripts/check_acceptance_sync.py` and `./.venv/bin/python scripts/check_local_execution_handoff.py`. Record exact commands, counts, warnings, and commit SHAs in the report.**
- [ ] **Step 6: Commit product/tests as `fix: unify work fact terminal transitions`, then docs/report as `docs: close task8 work transition gate`.**

**Acceptance:** Task 1 passes only if immediate failed→completed has zero pending actions before any projector read/restart/reconciliation; all matrix permutations converge to identical current facts; independent Luna returns spec compliant and no Critical/Important issue; root reruns the focused matrix and Task 1–7 regression gates.

### Task 2: Fixed 100-Question Golden Corpus and Deterministic Scoring

**Purpose:** Freeze what “good long-term memory” means before tuning retrieval, so implementation cannot move the goalposts.

**Files:**
- Create: `src/automatic_memory/evaluation.py`
- Create: `tests/evaluation/fixtures/automatic_memory_corpus.jsonl`
- Create: `tests/evaluation/fixtures/automatic_memory_questions.jsonl`
- Create: `tests/evaluation/test_automatic_memory_quality.py`
- Create: `tests/test_automatic_memory_acceptance_gate.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK9_GOLDEN_EVALUATION.md`

**Interfaces:**
- `CorpusRecord(fact_id: str, topic_key: str, source_id: str, conversation_id: str, message_id: str, role: Literal["user", "assistant", "system", "tool"], content: str, content_hash: str, occurred_at: str, lifecycle: Literal["active", "superseded", "invalidated", "archived"], supersedes_fact_id: str | None, authority: str, project_id: str, privacy: str, agent_scope: tuple[str, ...], citation_id: str, memory_kind: str, risk: str)`.
- `EvaluationQuestion(question_id: str, category: Literal["stable_preference", "current_project_decision", "superseded_decision", "cross_session", "authority_conflict", "protected_candidate", "scope_negative", "temporal_explanation", "context_dedup"], query: str, mode: Literal["current", "as_of", "history", "why"], as_of: str | None, expected_fact_ids: tuple[str, ...], forbidden_fact_ids: tuple[str, ...], expected_citation_ids: tuple[str, ...], requires_owner_review: bool)`.
- `QuestionResult(question_id: str, recalled_fact_ids: tuple[str, ...], citation_ids: tuple[str, ...], expected_fact_count: int, recalled_expected_count: int, expected_citation_count: int, correct_citation_count: int, context_chars: int, passed: bool, failures: tuple[str, ...])`.
- `EvaluationReport(answered_questions: int, imported_messages: int, expected_messages: int, ordered_role_matches: int, expected_ordered_roles: int, valid_fact_hits: int, valid_fact_total: int, citation_hits: int, citation_total: int, automatic_activation_correct: int, automatic_activation_total: int, valid_fact_recall: float, citation_accuracy: float, automatic_activation_accuracy: float, protected_false_promotions: int, stale_current_leaks: int, duplicate_records: int, baseline_context_chars: int, rendered_context_chars: int, context_reduction: float, mcp_successes: int, mcp_attempts: int, mcp_success_rate: float, production_pollution: int, owner_review_success: float | None, reboot_recovery: float | None, blocked_reasons: tuple[str, ...])`.
- `score_question(question: EvaluationQuestion, corpus_by_fact: Mapping[str, CorpusRecord], recalled_fact_ids: Sequence[str], citation_ids: Sequence[str], *, context_chars: int) -> QuestionResult` rejects duplicate, unknown, extra, or forbidden fact IDs; rejects duplicate/unknown/extra citations; and requires each expected citation to belong to its expected fact. A passing result contains exactly the hand-authored expected fact/citation sets.
- `AutomaticMemoryAcceptanceGate.evaluate(report: EvaluationReport) -> Literal["PASS", "FAIL", "BLOCKED"]`; missing owner/Mac evidence is `BLOCKED`, a measured threshold miss is `FAIL`, and unexecuted questions can never be counted as success.
- Percentages use the 0–100 scale. Gate order is deterministic: any measured failure returns `FAIL`; otherwise any missing external evidence or nonempty `blocked_reasons` returns `BLOCKED`; only then return `PASS`. Measured PASS requires 100 questions, message and role/order counts equal with nonzero denominators, recall `>= 90`, citation/automatic activation/MCP `>= 95`, protected false promotions/stale leaks/duplicates/Production pollution all `0`, context reduction `>= 90`, and owner review/reboot exactly `100` when provided.
- Fixture distribution is exact: 20 stable preferences, 20 current project decisions, 15 superseded decisions, 10 cross-session facts, 10 authority conflicts, 10 protected/Core/high-risk candidates, 5 privacy/project/agent-scope negatives, 5 `as_of/history/why` questions, and 5 ContextPack-length/dedup questions.
- Fixture semantics are mandatory, not labels: every query/content is a distinct natural-language scenario; every superseded/temporal case has old and replacement records joined by `topic_key`/`supersedes_fact_id`; every authority conflict has at least two authority levels; every cross-session case spans at least two conversation IDs; scope negatives vary project, privacy, and agent scope; context-dedup cases contain duplicate evidence joined by `content_hash`. Corpus size is whatever these relationships require and is not forced to 100; only questions are exactly 100.
- All raw counters are strict non-boolean integers with `0 <= numerator <= denominator`; all percentage fields are finite strict numbers in `[0, 100]`. `context_reduction` is computed as `(1 - rendered_context_chars / baseline_context_chars) * 100` from positive baseline and `0 <= rendered <= baseline`, never accepted as an unverified caller-only percentage.

- [ ] **Step 1: Create synthetic, non-personal source conversations and exactly 100 hand-derived, semantically distinct questions using the mandatory relationship shapes above. Every question names expected and forbidden stable IDs; every expected citation belongs to its expected fact; no expected answer is computed by production retrieval code.**
- [ ] **Step 2: Write evaluator and threshold tests first. Run `./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py`; expect RED because evaluator contracts are absent.**
- [ ] **Step 3: Implement deterministic parsing/scoring only. Do not tune retrieval in this task and do not call a network model. Reject non-mapping JSONL rows, unknown/missing/duplicate/extra evidence, fact/citation mismatch, incomplete 100-question runs, bool/floating raw counters, non-finite/out-of-range scores, generic Unix/Windows/UNC absolute paths, and likely keys/tokens/passwords in nested values.**
- [ ] **Step 4: Run focused tests to GREEN and mutation-check every threshold boundary: 89.999/90 recall, 94.999/95 citation/activation/MCP, one protected false promotion, one stale leak, one duplicate, one Production write, 89.999/90 reduction, mismatched message/role counts, zero denominators, 99/100 questions, missing owner evidence, and missing reboot evidence must all prevent PASS with the specified FAIL/BLOCKED precedence.**
- [ ] **Step 5: Commit product/tests as `test: define automatic memory quality gate`, then report/docs as `docs: record automatic memory evaluation contract`.**

**Acceptance:** Exactly 100 valid unique questions; category counts match; malformed or incomplete evidence fails closed; evaluator reports raw numerator/denominator for every percentage; independent Luna confirms fixtures do not mirror production logic or include real owner data.

### Task 3: Unified RAG, ContextPack, MemoryGateway and MCP

**Purpose:** Return current effective memory plus directly relevant raw evidence and authority context, with compact citations and no stale decision leakage.

**Files:**
- Modify: `src/retrieval/context_pack.py`
- Modify: `src/gateway/memory_gateway.py`
- Modify: `src/mcp_server.py`
- Modify only if required by the existing interface: `src/retrieval/hybrid.py`
- Test: `tests/test_automatic_memory_context_pack.py`
- Test: `tests/test_automatic_memory_mcp.py`
- Test: `tests/test_temporal_retrieval_paths.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK9_UNIFIED_RAG.md`

**Interfaces:**
- Extend the existing `ContextPackRequest`; retain `max_chars: int = 12000` and the existing `TemporalQuery` rather than creating a parallel request.
- `ContextPackBuilder.build(...)` returns ordered sections for current effective memory, project authority, and directly relevant raw evidence. Every item contains stable source/conversation/message or memory IDs, observed/effective time, lifecycle state, and an exclusion/why reason when the mode requires it.
- Dedup identity is the normalized tuple `(source_id, conversation_id, message_id, memory_id, content_hash)`; the same evidence may appear once only.
- `MemoryGateway.build_context_pack(...)` and MCP `build_context_pack` pass the same authorization, project, privacy, agent, temporal, and character-limit contract.
- When Qdrant is unavailable, the existing lexical path remains available and the result states semantic degradation; it must not fabricate semantic success.

- [ ] **Step 1: Write failing behavior tests for current/as_of/history/why, project/privacy/agent isolation, authority conflict, source/conversation/message/memory citations, deterministic ordering, duplicate removal, final rendered length 12,000, and Qdrant-unavailable lexical degradation.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_context_pack.py tests/test_automatic_memory_mcp.py tests/test_temporal_retrieval_paths.py`; expect RED on missing unified provenance/length behavior.**
- [ ] **Step 3: Extend only the existing builder, gateway, MCP tool, and—if the failing test proves necessary—hybrid post-filter. Do not add a second ContextPack builder, retriever, API, database, or UI projection.**
- [ ] **Step 4: Run focused tests to GREEN, then `./.venv/bin/python -m pytest -q tests/test_memory_retrieval.py tests/test_permanent_memory_gateway.py tests/test_temporal_current_filter.py tests/test_temporal_retrieval_paths.py`.**
- [ ] **Step 5: Commit product/tests as `feat: unify cited automatic memory context`, then report/docs as `docs: record unified rag evidence`.**

**Acceptance:** Current mode stale leakage 0 across direct builder, gateway, and MCP; identical scope inputs return identical fact/citation IDs; rendered ContextPack is at most 12,000 characters; every returned fact is traceable; lexical degradation is explicit and usable.

### Task 4: Quality, Scale, Crash and Degradation Gate

**Purpose:** Run the frozen evaluator against the real Task 3 retrieval path and prove stability at product scale.

**Files:**
- Modify: `src/automatic_memory/evaluation.py`
- Create: `tests/evaluation/test_automatic_memory_end_to_end.py`
- Create: `tests/performance/test_automatic_memory_100k.py`
- Create: `scripts/automatic_memory_quality_gate.py`
- Modify: `scripts/validate.ps1`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK9_QUALITY_SCALE_GATE.md`

**Interfaces:**
- `run_quality_gate(corpus_path: Path, questions_path: Path, *, output_path: Path) -> EvaluationReport` imports the synthetic corpus through supported adapters, indexes through existing storage, queries through `MemoryGateway`, and writes a machine-readable JSON report under `output/validation/`.
- The 100k generator creates deterministic synthetic messages outside Production/Vault and records seed, counts, hashes, runtime, P50/P95, ContextPack sizes, and cleanup result.
- `scripts/validate.ps1 -Mode focused -Area automatic-memory-quality` runs deterministic functional evaluation. Scale and idle-CPU evidence remain a separately named local acceptance command and are never silently substituted by unit tests.

- [ ] **Step 1: Write the end-to-end test that initially fails against the real Task 3 path; prohibit stubbed retrieval results and assert all EvaluationReport numerators/denominators.**
- [ ] **Step 2: Add a deterministic 100k-message generator and bounded benchmark. The test must skip with an explicit environment reason only when the opt-in scale flag is absent; release validation must enable it.**
- [ ] **Step 3: Implement the gate runner and focused validation registration. Keep all generated data in an explicit temporary Acceptance root and verify Production/Vault hashes are unchanged.**
- [ ] **Step 4: Require 100/100 executed, message import completeness 100%, role/order match 100%, recall at least 90%, citation at least 95%, automatic activation at least 95%, real MCP success at least 95%, protected false promotion 0, stale leakage 0, duplicates 0, ContextPack reduction at least 90%, hot retrieval P95 at most 3 seconds on Mac M5, and single-source corruption/Qdrant outage not blocking other sources or lexical retrieval.**
- [ ] **Step 5: Run focused gate, Task 1–3 regressions, acceptance sync, and local handoff. Commit product/tests as `test: gate automatic memory quality and scale`, then evidence/docs as `docs: record automatic memory quality results`.**

**Acceptance:** Deterministic functional gate PASS on a clean tree; scale report contains exactly 100,000 messages; no Production pollution; all temporary fixtures are accounted for; Mac-only P95 and idle CPU remain `BLOCKED` until measured on Task 6's physical run, never guessed from CI.

### Task 5: macOS Release Candidate and Acceptance Task Preparation

**Purpose:** Produce a same-SHA release candidate and a complete, auditable physical acceptance task without running an IDLE historical Artifact.

**Files:**
- Create: `src/automatic_memory/mac_acceptance.py`
- Create: `tests/test_automatic_memory_macos_gate.py`
- Create or modify: `desktop/lingji-control/scripts/macos-release-smoke.mjs`
- Modify: `scripts/validate.ps1`
- Modify: `docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify only after Artifact identity and hashes exist: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK10_MAC_RELEASE_PREPARATION.md`

**Interfaces:**
- `MacAcceptanceIdentity(product_commit: str, artifact_name: str, artifact_id: str, zip_sha256: str, installer_sha256: str)`.
- `MacAcceptanceGate.evaluate(identity: MacAcceptanceIdentity, evaluation: EvaluationReport, automated_release: Literal["PASS", "FAIL", "BLOCKED"], owner_observation: Literal["PASS", "FAIL", "NOT_TESTED"]) -> Literal["PASS", "FAIL", "BLOCKED"]`.
- Owner observation `NOT_TESTED` always yields `BLOCKED`; a mismatched product/artifact SHA yields `FAIL`; unit tests can never set owner observation to PASS.

- [ ] **Step 1: Write RED tests for exact identity/hash, owner-only observation, Production/Acceptance isolation, no false reboot claim, rejected historical Artifact IDs, and IDLE task refusal.**
- [ ] **Step 2: Implement the gate and release smoke; run focused tests, Desktop build/smokes, and `scripts/validate.ps1 -Mode release` once on the candidate tree. Do not run a separate `full` first.**
- [ ] **Step 3: Freeze product HEAD, build/fetch only the same-SHA macOS Artifact, compute archive/installer hashes, and remote-read the commit/Artifact metadata.**
- [ ] **Step 4: Root reviews the evidence. Only then update `LOCAL_EXECUTION_TASK.md` from IDLE to a new exact `ACTIVE` task containing full SHA, Artifact ID/name, both hashes, cleanup rules, report branch/path, owner-confirmation scope, and forbidden historical Artifact list.**
- [ ] **Step 5: Commit product gate/tests before Artifact creation; put task activation and identity lock in a separate acceptance-authority commit so product HEAD does not move.**

**Acceptance:** Release validation PASS at one immutable product SHA; same-SHA Artifact and hashes remotely visible; no secret/plaintext or owner data in logs; an exact ACTIVE task exists before any installation or UI launch.

### Task 6: macOS M5 Physical Release Acceptance

**Purpose:** Verify the actual installed product, not source code or a dev server, and leave it open for the owner's final observation.

**Files:**
- Read authority: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Write result: `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- Write report at the exact path named by the ACTIVE task
- Update: `docs/PROJECT_STATUS.md`

**Execution contract:**
- Luna executes only the exact ACTIVE task and Artifact. Root independently verifies logs, hashes, IDs, UI evidence, reports, and remote visibility.
- Required scenarios: overlay install without deleting owner data; one Chinese authorization; supported-source discovery; ChatGPT official export import; Codex incremental capture within 30 seconds; missed-event reconciliation; 30% and 70% forced termination/restart; duplicate rescans; single-source corruption; Qdrant outage with lexical degradation; sleep/wake; application restart; backup restore; idle five-minute CPU; Work Fact heartbeat; every visible Desktop control.
- Third-party directory sentinels compare content hash, mtime, permissions, and key config before/after. Natural chat writes are logged separately; LingJi-attributable differences must be 0.

- [ ] **Step 1: Validate task status ACTIVE, full product/Artifact identity, hashes, report branch, cleanup rules, free ports, Acceptance paths, and Production sentinels before installation. Any mismatch is BLOCKED.**
- [ ] **Step 2: Install and launch the real packaged app. Traverse Overview, Sources/onboarding, Activity, Attention, Capture, Memory, settings, and every visible control; verify each action against 8766 facts/files/processes rather than visual toast text.**
- [ ] **Step 3: Execute all source, crash, duplicate, degradation, sleep/wake, performance, backup, and non-interference scenarios. Record measured counts and times, never inferred PASS values.**
- [ ] **Step 4: Keep the release UI open and request the owner's observation. Do not close, merge, clean retained failure evidence, or declare Phase 1 PASS before the owner answers.**
- [ ] **Step 5: After owner PASS/FAIL, complete result/report, push the acceptance branch, remote-read branch/commits/report/result/comment, perform prescribed cleanup, update the receipt, push, and remote-read again.**

**Acceptance:** Automatic gates and exact-instance physical checks PASS; all visible controls have real effects; 100k hot P95 at most 3 seconds; five-minute idle CPU average at most 3%; heartbeat age at most 10 seconds; Production pollution 0; third-party attributable mutation 0; owner explicitly PASS. Otherwise result is FAIL or BLOCKED, never partial PASS.

### Task 7: Windows Parity After macOS PASS

**Purpose:** Implement only platform differences while preserving the Mac-approved data model, API, UI semantics, safety, and acceptance meaning.

**Files:**
- Create: `src/automatic_memory/windows_parity.py`
- Create: `tests/test_automatic_memory_windows_parity.py`
- Create or modify: `desktop/lingji-control/scripts/windows-release-smoke.mjs`
- Modify: `scripts/build_windows_sidecar.ps1`
- Modify: `scripts/validate.ps1`
- Modify: `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK11_WINDOWS_PARITY.md`

**Interfaces:**
- `WindowsParityReport(api_semantics_equal: bool, dto_semantics_equal: bool, power_shell_51_compatible: bool, data_root_outside_c: bool, exact_instance_lifecycle: bool, production_pollution: int, artifact_sha256: str, mac_gate_commit: str)`.
- `WindowsParityGate.evaluate(report: WindowsParityReport, mac_result: Literal["PASS", "FAIL", "BLOCKED"]) -> Literal["PASS", "FAIL", "BLOCKED"]`; any Mac result other than PASS returns BLOCKED without building or installing Windows.

- [ ] **Step 1: After Mac PASS only, write RED tests for Windows paths/events/install detection, PowerShell 5.1 syntax, same 8766/DTO semantics, non-C-drive data, exact-instance shutdown, overlay install, and zero silent writes.**
- [ ] **Step 2: Implement the smallest platform adapters and build-script changes; do not fork the data model, API responses, Work Fact states, or RAG behavior.**
- [ ] **Step 3: Run Windows focused and `release` validation on a Windows host, then NSIS overlay installation and every visible-control smoke using the same acceptance semantics as Mac.**
- [ ] **Step 4: Verify Windows Artifact identity/hash, PowerShell 5.1, non-C-drive data placement, sleep/restart recovery, Production isolation, and third-party non-interference.**
- [ ] **Step 5: Commit product/tests as `feat: add windows automatic memory parity`, then report/docs as `docs: record windows parity acceptance`.**

**Acceptance:** Mac gate commit is PASS and remotely visible; Windows focused/release/NSIS and real UI acceptance PASS; API/DTO/state/citation semantics equal; no C-drive unauthorized writes; Production pollution 0. Without an available Windows host, report BLOCKED and do not weaken the gate.

## Root Final Acceptance

- [ ] Root verifies every task report against its diff and reruns the exact focused commands before moving to the next task.
- [ ] After Tasks 1–5, root dispatches one broad independent Luna review over the remaining-Phase diff and allows one consolidated fix wave only.
- [ ] Root does not claim Mac PASS until Task 6 owner confirmation and remote receipt reread are complete.
- [ ] Root does not dispatch Task 7 until Mac PASS is recorded in the acceptance authority.
- [ ] Final tree runs `release` once, acceptance sync, local handoff, artifact identity verification, and remote branch/commit/report reread.
- [ ] Final user report contains only: what is automatic now; which sources are fully handled; official-source limitations; measured memory/RAG quality; actual blockers and user impact; Mac result; Windows result; the owner's one remaining action.

## Self-Review Checklist

- [ ] Every remaining Phase 1 requirement is assigned to one task and one authoritative report.
- [ ] No task adds a parallel data plane or treats an IDLE local task as executable.
- [ ] Work Fact closure precedes RAG; frozen evaluation precedes RAG tuning; Mac precedes Windows.
- [ ] Every implementation task has exact files, interfaces, RED/GREEN commands, commit boundaries, and measurable acceptance criteria.
- [ ] No placeholder markers, vague future-work wording, unmeasured PASS, or owner-observation automation remains.
