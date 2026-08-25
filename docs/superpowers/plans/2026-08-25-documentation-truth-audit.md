# LingJi Documentation Truth Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every tracked document unambiguous about whether it is current authority, supporting guidance, future backlog, historical evidence, or generated data, then align current project progress with code and verification evidence at `ced1128e50d3b3758585573042ea6bcc6f315384`.

**Architecture:** Current facts remain concentrated in `docs/PROJECT_STATUS.md`; code navigation remains in `docs/MODULES/CODE_MAP.md`; acceptance authority remains in `docs/ACCEPTANCE/`; historical implementation and test evidence is retained but explicitly demoted from current-status authority. No new architecture, roadmap, acceptance task, database, API, or product behavior is introduced.

**Tech Stack:** Markdown, Git, Python 3 read-only audit scripts, existing acceptance validators, repository-local tests.

## Global Constraints

- Formal/default branch is `master`; work is isolated on `codex/docs-project-truth-audit` from remote `master` at `ced1128e50d3b3758585573042ea6bcc6f315384`.
- `docs/PROJECT_STATUS.md` is the only detailed current-progress authority.
- `docs/ARCHITECTURE.md` is the stable architecture authority; `docs/MODULES/CODE_MAP.md` owns code entry points and focused tests.
- `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` remains `IDLE`; this work must not activate, download, install, run, or retry an Artifact.
- `docs/TEST_REPORTS/**` and acceptance receipts are historical evidence and must not be deleted.
- Phase 1 remains `SECOND BRAIN COMPLETION`; Opportunity Center remains frozen until final Phase 1 `PASS`.
- Documentation cleanup must not claim Work Fact API, Desktop integration, Capture-to-Memory closure, focused/full/release validation, or owner acceptance as complete.
- No product code, runtime data, Vault, database, Qdrant collection, credentials, logs, generated opportunity records, or owner data may be modified.

---

### Task 1: Freeze the evidence baseline and classification

**Files:**
- Create: `docs/TEST_REPORTS/DOCUMENTATION_TRUTH_AUDIT_20260825.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`

**Interfaces:**
- Consumes: Git HEAD `ced1128e...`, product-status baseline `3d7225f...`, GitHub `master`, current code and tests.
- Produces: one durable audit record and one acceptance entry defining the checks for this documentation-only change.

- [x] **Step 1: Record the exact audit population and categories**

Run:

```bash
git ls-tree -r --name-only -z HEAD
```

Parse the NUL-delimited paths and record the verified total (`403`) and categories: current authority, stable guidance, future backlog, historical implementation/research, historical test/acceptance evidence, generated PEMIS data, owner knowledge/content, and dependency/constraint text. Do not use line-oriented quoted Git paths for this count because non-ASCII filenames can be missed.

- [x] **Step 2: Record the Work Fact evidence delta**

Run:

```bash
git log --oneline 3d7225f58fb5b5a9b035cfd72f92cb2267b48559..HEAD
git diff --name-status 3d7225f58fb5b5a9b035cfd72f92cb2267b48559..HEAD
```

The report must distinguish completed code (`WorkStore` reads, repaired Capture bridge, control adapter, four test files) from pending work (formal route registration, `LocalControlService` integration, Python/TypeScript DTO and response shapes, Outcome/NextAction projection, focused/full/release and owner acceptance).

- [x] **Step 3: Add this change's acceptance entry before authority-document edits**

Add a 2026-08-25 entry at the top of `CHANGE_ACCEPTANCE_LOG.md` requiring:

```text
python3 scripts/check_acceptance_sync.py
python3 scripts/check_local_execution_handoff.py
git diff --check
broken local Markdown link scan
stale-current-reference scan
```

The entry must say this is documentation governance only, makes no product capability claim, runs no Artifact, and does not alter the most recent `FAIL / DO NOT MERGE` result.

### Task 2: Correct the current progress authorities

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Modify: `docs/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 evidence and the four SB-0 progress reports.
- Produces: one non-contradictory current status, code map, and user-visible change history.

- [x] **Step 1: Update the SB-0 status matrix in `PROJECT_STATUS.md`**

Replace the 2026-08-22 all-pending list with exact states:

```text
Work persistence: IMPLEMENTED_NOT_TESTED
Capture bridge contract: IMPLEMENTED_NOT_TESTED
Projection reads: IMPLEMENTED_NOT_TESTED
Control adapter: IMPLEMENTED_NOT_TESTED
Formal 8766 route registration: PENDING
LocalControlService shared integration: PENDING
Python/Desktop DTO and response contract: PENDING
Outcome/NextAction/Memory end-to-end projection: PENDING
Focused/full/release/owner validation: NOT RUN
```

Keep Phase 1 and M5 `FAIL / DO NOT MERGE` unchanged.

- [x] **Step 2: Correct Work Fact ownership and tests in `CODE_MAP.md`**

Document the implemented store/projector/control pieces, the existing four test files, the missing `tests/test_work_projector.py` and `work-fact-smoke.mjs`, the unregistered `work_routes.py`, and `src/control/work_api.py` as an unassembled `/v1/work` draft that is not the formal authenticated 8766 API.

- [x] **Step 3: Append a cautious 2026-08-24/25 changelog entry**

State that SB-0 persistence/bridge/projection/control adapter work landed with contract-test files, while API registration, Desktop contract, end-to-end behavior, execution of tests, and acceptance remain incomplete.

- [x] **Step 4: Verify forbidden completion claims are absent**

Run:

```bash
rg -n 'SB-0: (PASS|COMPLETE)|Phase 1: (PASS|COMPLETE)|Work Fact.*(fully|正式).*完成' docs/PROJECT_STATUS.md docs/MODULES/CODE_MAP.md docs/CHANGELOG.md
```

Expected: no false completion claim.

### Task 3: Repair documentation governance and authority routing

**Files:**
- Modify: `docs/DOCUMENTATION_MAINTENANCE.md`
- Modify: `docs/AI_COLLABORATION_RULES.md`
- Modify: `docs/MEMORY_SYSTEM.md`
- Modify: `docs/VECTOR_DATABASE.md`
- Modify: `docs/AI_MODEL_STRATEGY.md`
- Create: `docs/MODULES/README.md`
- Create: `docs/TEST_REPORTS/README.md`

**Interfaces:**
- Consumes: authority roles from `AGENTS.md` and `docs/DEVELOPMENT_RULES.md`.
- Produces: a single routing model that prevents deleted roadmaps, old branches, old model assumptions, and historical reports from acting as current progress authorities.

- [x] **Step 1: Replace obsolete reading orders and deleted references**

Remove current-governance references to deleted `docs/AI_CONTEXT.md` and `docs/MODULES/UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`. Point agents to the exact minimum sequence in `AGENTS.md`.

- [x] **Step 2: Reduce duplicate technical contracts to routing guidance**

`MEMORY_SYSTEM.md`, `VECTOR_DATABASE.md`, and `AI_MODEL_STRATEGY.md` must defer stable facts to `ARCHITECTURE.md`, runtime/config defaults to code, current status to `PROJECT_STATUS.md`, and future model-routing work to `FUTURE_DEVELOPMENT_TODO.md`. Remove stale branch and provider assertions.

- [x] **Step 3: Add module and test-report directory indexes**

`docs/MODULES/README.md` must name only `CODE_MAP.md` and `FUTURE_DEVELOPMENT_TODO.md` as live routing documents and classify every `P0_*`/`P2_*` file as historical implementation evidence. `docs/TEST_REPORTS/README.md` must state that reports prove a named commit/test run only and never override current status or acceptance receipts.

- [x] **Step 4: Verify current governance no longer references deleted authorities**

Run:

```bash
rg -n 'docs/AI_CONTEXT\.md|UNIFIED_MEMORY_DEVELOPMENT_ROADMAP' docs/DOCUMENTATION_MAINTENANCE.md docs/AI_COLLABORATION_RULES.md
```

Expected: no matches.

### Task 4: Demote historical and generated snapshots without deleting evidence

**Files:**
- Modify: `docs/ACCEPTANCE/AUTOPILOT_PHASE4_ACCEPTANCE.md`
- Modify: `docs/TECH_RESEARCH/MACOS_M5_ACCEPTANCE.md`
- Modify: `docs/MODULES/P0_ENGINEERING_HYGIENE_IMPLEMENTATION.md`
- Modify: every tracked `docs/MODULES/P2_*.md`
- Modify: top-level `docs/*REPORT.md` historical implementation/acceptance snapshots
- Modify: `PEMIS/status/current.md`
- Modify: `PEMIS/dashboard/main.md`
- Modify: `PEMIS/dashboard/by_monetization.md`
- Modify: `PEMIS/dashboard/by_speed.md`
- Modify: `PEMIS/dashboard/by_tag.md`

**Interfaces:**
- Consumes: directory classifications from Task 3.
- Produces: explicit historical/generated-data banners on files most likely to be mistaken for current progress.

- [x] **Step 1: Add a uniform historical-evidence banner**

For module implementation and top-level report files, add at the beginning:

```markdown
> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。
```

Do not rewrite historical test counts, branch names, verdicts, hashes, or acceptance evidence.

- [x] **Step 2: Mark superseded acceptance/research contracts precisely**

`AUTOPILOT_PHASE4_ACCEPTANCE.md` must say it is a retained PR #88 historical contract and cannot activate a task. `TECH_RESEARCH/MACOS_M5_ACCEPTANCE.md` must say its “physical acceptance pending” statement was superseded by the later `COMPLETED / FAIL` receipt.

- [x] **Step 3: Mark PEMIS as frozen generated data**

Change the two apparent current-state entry points from `NORMAL/current` authority language to `FROZEN_GENERATED_SNAPSHOT`, preserve the 2026-06 data, and state that Opportunity Center remains frozen. Add the same non-authority banner to the four dashboard entry files; do not modify or delete the 120 `opp_*.md` data records.

- [x] **Step 4: Verify historical facts were not erased**

Run:

```bash
git diff -- docs/TEST_REPORTS docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

Expected: no historical report/receipt deletion or verdict change.

### Task 5: Validate, review, and prepare the owner-facing status report

**Files:**
- Modify: `docs/TEST_REPORTS/DOCUMENTATION_TRUTH_AUDIT_20260825.md`

**Interfaces:**
- Consumes: final diff and verification outputs.
- Produces: evidence-backed cleanup result and a nontechnical capability/gap/blocker summary.

- [x] **Step 1: Run repository documentation gates**

Run:

```bash
python3 scripts/check_acceptance_sync.py
python3 scripts/check_local_execution_handoff.py
git diff --check
```

Record exact exit results. If pytest is unavailable, record that limitation rather than claiming test execution.

- [x] **Step 2: Run full tracked-document link and stale-reference scans**

Check all 403 baseline tracked document-like files plus the four new audit/governance files for missing conventional Markdown inline links, references to deleted current authorities, and unmarked `current/NORMAL` PEMIS status language. Obsidian `[[wikilink]]` validation is outside this repository-relative scan and must be reported separately. Expected: zero current-authority broken inline links and zero unqualified current-status claims in PEMIS entry files.

- [x] **Step 3: Review the complete diff against the user request**

Verify line by line that the final report answers only:

```text
现在能实现什么
现在不能稳定实现什么
当前最先要补什么
哪些技术基础已经通过，不要重复返工
哪些结论仍需主人真机确认
```

- [x] **Step 4: Commit one documentation-governance change**

After all checks pass:

```bash
git add docs PEMIS
git commit -m "docs: align project progress and historical evidence"
```

Do not push, open a PR, merge, or alter the original acceptance branch without the owner's integration choice.
