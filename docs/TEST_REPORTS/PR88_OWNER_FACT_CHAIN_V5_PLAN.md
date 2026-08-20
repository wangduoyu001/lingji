# PR88 Owner Fact Chain V5 — Implementation Plan and Self-Review Gate

> Status: IN_PROGRESS
> Product PR: #88
> Development PR: #105
> Branch: `fix/pr88-owner-fact-chain-v5`
> Source failure: `PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17 / FAIL / DO NOT MERGE`

## 1. Problem statement

The M5 failure is not a visual-layout defect. The same real work is not durably identifiable across Capture, Work, Home, Attention and Memory.

Observed broken chain:

```text
Capture submission
-> audit event has capture_id/job_id
-> queue job does not persist capture_id
-> UI reconstructs relationships from titles/relative_path/aggregate state
-> Home/Work/Attention can disagree
```

V5 must make object identity durable before changing presentation.

## 2. Research translated into implementation rules

Current durable-agent systems consistently separate a logical workflow from its individual execution steps and preserve human-approval boundaries instead of inferring them from presentation state. LingJi will apply the same principle without adding a second orchestration framework or a new permanent-memory authority.

Rules:

1. One stable work identity must survive process restart and UI reload.
2. A Capture-created extraction job is the existing authoritative WorkItem; do not create a duplicate work database.
3. `capture_id` must be persisted with the extraction job, not only returned to the caller or written to a best-effort audit event.
4. Job outcome and next actor must be projected from durable job/result state in one shared projector, not independently invented by Home and Work.
5. No WorkItem means no claim that LingJi performed work.
6. No concrete Review/import/rebuild object means no owner PendingAction.
7. A completed job may claim a Memory result only when the durable extraction result identifies the resulting object(s).
8. Unknown/missing evidence must remain unknown, not be converted to success.

## 3. Implementation sequence

### Stage A — durable Capture -> WorkItem identity

- Persist `capture_id` in the extraction payload at enqueue time.
- Keep queue `job_id` as the WorkItem identity.
- Preserve source/capture method without exposing captured body in owner DTOs.
- Add regression tests proving identity survives queue reads and duplicate reuse.

### Stage B — single owner work projection

- Enrich sanitized Capture job projection with `work_item_id`, `capture_id`, readable title, outcome state, next actor/action and result object IDs.
- Do not expose raw payload, absolute input paths, raw snapshots or secret-bearing errors.
- Home and Work must consume the same sanitized projection.

### Stage C — UI convergence

- Work page stops interpreting raw `/api/jobs` rows.
- Home stops using `relative_path` as the primary job-memory join.
- Recent outcome cards must be backed by a real WorkItem.
- Memory links are shown only when a completed WorkItem has durable result references.

### Stage D — automatic proof

Required tests before any M5 handoff:

1. text Capture returns `capture_id + job_id` and the same `capture_id` is present when the queued job is read back;
2. duplicate Capture reuses the same WorkItem without inventing a second completed claim;
3. queued/running/retrying/completed/failed/cancelled states produce deterministic owner narratives;
4. completed result object IDs are exposed without raw/private path leakage;
5. Home and Work use the same projection and cannot disagree about active/completed work;
6. no concrete pending object means no owner action;
7. existing Production/Acceptance isolation, secret boundary, pagination and exact-instance Runtime lifecycle tests remain green.

## 4. Mandatory self-review gate before physical acceptance

A new M5 task MUST NOT be activated merely because CI passes.

Before handoff, the implementation agent must perform and document an independent review covering:

- architecture: no second fact source / no duplicate queue;
- identity: Capture -> WorkItem -> Outcome -> Memory/PendingAction is traceable;
- truthfulness: UI cannot claim work, memory or owner action without a concrete object;
- privacy: no raw body, private absolute path, token/cookie/authorization/credential in owner projections;
- restart durability: relationship does not depend on in-memory maps;
- failure semantics: failed/unknown states stay failed/unknown;
- cross-platform regression: Mac and Windows exact-SHA release gates;
- tests: no deleted/weakened/skipped assertions to obtain green CI;
- documentation: CHANGE_ACCEPTANCE_LOG, implementation report and code map/status updates are synchronized.

Self-review verdict is one of:

```text
PASS_FOR_M5_PREPARATION
FAIL_FIX_REQUIRED
BLOCKED
```

Only `PASS_FOR_M5_PREPARATION`, followed by focused/full/release CI and new same-SHA Mac/Windows artifacts, permits creation of a new `ACTIVE` M5 task.

## 5. Non-goals

- no new permanent-memory authority;
- no new queue/orchestrator framework;
- no automatic Permanent/Core Memory approval;
- no destructive automatic Qdrant rebuild;
- no broad UI redesign before the fact chain is correct;
- no reuse of rejected M5 artifacts.

## 6. Rollback

All V5 changes remain isolated on PR #105. If the fact-chain changes regress capture/extraction, revert the V5 commits while preserving the rejected V4 product branch and its acceptance evidence. Do not alter Production owner data during development.
