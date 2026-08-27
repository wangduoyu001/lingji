# Phase 1 Product Landing — Task 3 Repair Round 1 Independent Review

Date: 2026-08-27  
Branch: `codex/phase1-automatic-memory`  
Review target: `95cfc90b33e450723def1440616c3e8a7f48f34d`  
Repair base: `53c4ce0`  
Product/test commit: `f2f7312`  
Evidence artifact commit: `4e5d744`  
Metadata correction commit: `95cfc90`

This was a read-only review of the repair range and direct regression boundaries. No product, test, acceptance, index, live 8766/8767, Artifact/release, Production, configured Vault, or owner data was touched. Synthetic fixtures used below were temporary and cleaned after each probe.

## Verdict

Spec compliance: **FAIL**  
Task quality: **NEEDS_FIXES**

The repair closes I1, most of I2, I3, the ordinary two-scan case in I4, I5, I6, and I8. It does not meet the required zero-Critical/Important threshold because I4 still has cross-source and resumed-scan count defects, I2 has a CRLF explicit-deny bypass, and I7 does not clearly attribute the final metadata correction SHA.

## Materials and scope checked

- Read `AGENTS.md` in full.
- Read the phase plan sections covering Global Rules, the final Task 2 disposition, Task 3, and the Task 3 Repair Round 1 ruling.
- Read `task-3-review.md`, `task-3-repair-1-report.md`, the `53c4ce0..95cfc90` review/package diff, `docs/PROJECT_STATUS.md`, relevant `docs/MODULES/CODE_MAP.md`, all current acceptance authority files, and direct source/caller/test files.
- Reviewed only the repair range and its regression boundaries. No unrelated promotion, quality-runner, release, UI, or vector architecture was reopened.

## Verification run

Focused repair and directly affected tests:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py --tb=short
36 passed, 1 warning
```

Unfiltered direct matrix (runtime, packaged API, scheduler, resume, snapshot, idempotency, adapters, Work Fact, Obsidian, control API, and repair tests):

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_snapshot.py tests/test_extraction_idempotency.py tests/test_automatic_memory_adapters.py tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_obsidian.py --tb=short
204 passed, 7 warnings
```

The historically disclosed Task 2 timing test `test_daily_integrity_job_runs_without_event` passed in this run (both alone and in the scheduler module). It remains a preserved, quarantined Task 2 timing boundary and is not counted as repaired by Task 3. No new failure was found in the direct matrix.

Additional gates:

- `./.venv/bin/python -m compileall -q src tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py`: pass.
- `git diff --check 53c4ce0..95cfc90`: pass.
- `./.venv/bin/python scripts/check_acceptance_sync.py`: pass (`no product-impacting changes detected` for the committed tree).
- `./.venv/bin/python scripts/check_local_execution_handoff.py`: pass; local task remains `IDLE`.

## Findings

### Important I4 — cross-source structured identity is still collapsed

Location: `src/extraction/adapters/generic_ai_history.py:110-177`, `src/extraction/pipeline.py:479-481`, `src/sources/read_model.py:914-931`.

Reproduction used two separately authorized `generic_ai_history` roots containing byte-identical supported files with the same conversation/message IDs. Both scans produced two durable `automatic_memory_snapshot` jobs, but the read model contained exactly one source, one conversation, and one message. The generic adapter derives `source_scope` from input bytes and creates source/conversation/message external IDs from that scope; the automatic request payload includes `source_id` only for authorization, not as identity material. The read model then upserts the same external identities.

Impact: two authorized sources cannot be distinguished in structured retrieval/provenance; a source can silently overwrite or merge another source's content. This violates the I4 requirement that cross-source identity not collapse and the source/conversation/message identity boundary.

Minimal repair: carry the authorized source identity into the existing structured identity material or otherwise namespace each adapter bundle by the actual source, while preserving repeated scans of the same source as idempotent. Add a two-source same-content regression that asserts two source/conversation/message sets and their source IDs remain distinct.

### Important I4 — resumed scan projects a false zero count

Location: `src/automatic_memory/checkpoint.py:327-350,424-443`, `src/automatic_memory/runtime.py:345-364`.

Reproduction created one authorized source with one file, ran the existing `SnapshotJobRunner` with `crash_at="30%"`, waited for the inserted extraction job to reach `completed`, then resumed the same paused scan. The paused `ScanRun` returned `queued=0,reused=0`; the resulting Work Fact was:

```text
扫描完成，已检查 0 个来源文件（新增 0，复用 0）
```

while the queue contained one completed snapshot job. On resume, the runner counts the already checkpointed path in `completed_before` but does not carry that count into `ScanRun`; `_maybe_finalize_scan_work` uses `queued + reused` whenever a report exists, replacing the callback's temporary job-count evidence with zero.

Impact: a legitimate recovery can tell the owner that no source files were checked, violating truthful lifecycle/count reporting and the explicit I4 no-false-zero requirement.

Minimal repair: carry checked/recovered/unchanged count through the existing scan report contract, or calculate it from the durable scan manifest, and make Work Fact projection use that count. Add a pause/resume Work Fact assertion in addition to the existing two-new-scan assertion.

### Important I2 — CRLF frontmatter bypasses `lingji_memory: false`

Location: `src/obsidian/memory_scope.py:158-178`, especially lines 160-164 and 172-175.

Reproduction wrote `_LingJi/Memory Inbox/false.md` with bytes `---\r\nlingji_memory: false\r\n---\r\nSECRET`. `discover_memory_paths()` returned an eligible `authorized` decision, and `enumerate_authorized_files()` returned the file. `_read_frontmatter()` reads the first four bytes and accepts only `b"---\n"` (or the corresponding BOM/LF form), so `b"---\r"` is treated as no frontmatter. The same opening-marker problem affects BOM+CRLF.

Impact: the highest-priority explicit deny is ignored for normal Windows/CRLF notes inside a managed directory, allowing a deliberately excluded note into automatic-memory ingestion. This violates the required BOM/CRLF and `lingji_memory:false` fail-closed boundary.

Minimal repair: normalize/recognize `---\r\n` and BOM+CRLF while retaining the 8192-byte bound; add managed CRLF tests for false, true, malformed, and unclosed frontmatter and assert body bytes are never read.

### Important I7 — final metadata correction SHA is not clearly recorded

Location: `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-1-report.md:5-6`, `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md:1708,1730`.

The exact history is three commits: product/test `f2f7312`, evidence artifact `4e5d744`, and metadata correction `95cfc90`. The report and acceptance entry currently name only `4e5d744` as the evidence/docs commit; neither clearly says that `95cfc90` is the final metadata correction commit. The checked-out target is `95cfc90`, so the current evidence identity is under-described even though the stale `pending` placeholder itself is gone.

Impact: a reviewer cannot unambiguously map the final report/acceptance metadata to the reviewed HEAD and distinguish the evidence artifact from its later correction. This fails the explicit I7 exact-SHA truthfulness requirement.

Minimal repair: preserve the three-way identity explicitly in the authoritative report and acceptance entry: product/test `f2f7312`; evidence artifact `4e5d744`; metadata correction `95cfc90`. Do not self-reference a future review commit.

## Prior finding disposition

### I1 — PASS with direct malformed/authorization probes

`process_internal_next`, `process_job`, and `process_pending` now terminal-fail malformed, missing, revoked, and inactive internal snapshot jobs through `queue.fail(..., terminal=True)`, distinguish malformed `ValueError` from authorization `PermissionError`, emit the failed lifecycle callback, and do not repeatedly re-lease the job. A temporary queue probe showed both `process_job` for a missing source and malformed payload ending `failed`; `process_pending` processed the invalid job once and reported no pending work afterward. The valid ordinary job in the same batch completed, so no starvation was observed.

### I2 — PARTIAL; bounded reads pass, CRLF deny fails

The bounded opening-marker/frontmatter implementation passed ordinary-note no-body reads, explicit-true bounded reads, managed false LF reads, BOM/LF handling, and malformed/unclosed frontmatter fail-closed checks. The CRLF managed-deny case is the Important defect above.

### I3 — PASS

Case-folded separator-aware filtering excludes `credentials.json`, `AUTH-token.json`, `cookie.json`, `private.json`, and `auth_token.json`, while retaining `safe-history.json`. Nested sensitive directories are pruned, symlinks and outside-root paths remain rejected, and no new allowlist store was introduced.

### I4 — FAIL

The nominal real two-scan same-source test passes: two terminal scans, one extraction job, `queued=1` followed by `queued=0,reused=1`, and one structured source/conversation/message set. However, the two Important residuals above show that the proof is incomplete for cross-source identity and recovery/resume counts.

### I5 — PASS for the repair boundary

The authenticated scan route now requires a composed runtime and dispatches `runtime.scan_now`; absent runtime returns 409 without creating a scan. The direct route test verifies a real `work_id` response from the runtime. Pause/retry/resume remain the existing registry transitions and preserve their truthful paused/running/authorization-denied behavior. No orphan running scan was observed in the route probe.

### I6 — PASS for covered terminal transitions

Automatic scan WorkItems use the actual source ID and stable `automatic-memory:{scan_id}` identity. Existing `WorkStore.apply_extraction_transition` updates WorkItem status atomically with completed/failed/retrying outcome projection. Focused tests and the real same-source flow agree on source ID and terminal status. The resume count defect is tracked under I4, not misattributed to I6.

### I7 — FAIL

The prior stale `pending` values and trailing whitespace are fixed, and `git diff --check 53c4ce0..95cfc90` passes. The final three-SHA attribution is nevertheless incomplete as described above.

### I8 — PASS for the stated no-publishing boundary

The automatic internal consumer validates source/raw/hash/path metadata, invokes the existing adapter and structured read-model sink, and sets Vault/index publishing unavailable. It does not call `VaultExtractionSink.write_batch`/`write_document`, does not create an alternate Vault/store, and leaves the configured Vault tree unchanged in the raising-sink/sentinel test. Raw content-addressed evidence and structured source/conversation/message rows persist; no automatic promotion seam or false Vault/vector success was observed. Structured retrieval remains available through the existing read model where already supported; Task 7 vector work is out of scope.

## Regression and boundary review

- The repair diff changes only the existing checkpoint/model/path policy/runtime/scheduler/API/pipeline/queue/Obsidian/WorkStore surfaces plus focused tests and evidence docs. No new parser, store, queue, API, indexer, config center, UI, or retrieval implementation was added.
- The five quarantined automatic-promotion seams (`evaluate`, `promote`, `submit`, `reconcile_incomplete_projections`, `rebuild_derived_projections`) were not invoked by the repaired runtime/worker/scheduler paths; the existing sentinel isolation tests remain green.
- Task 2 lifecycle/timing code was not changed. The scheduler `integrity_seconds` clamp remains in the pre-existing code; its historically disclosed timing test passed in this run, so no new regression was found and the historical edge is not credited as repaired.
- The forced fast-worker ordering probe deliberately delayed runner cleanup and observed lifecycle callback before `_scan_reports` assignment. The eventual Work Fact summary was corrected to `新增 1，复用 0`; this specific race did not produce a separate defect in the tested normal one-file flow.
- No test deletion, assertion weakening, skip conversion, live service start, Artifact/release action, or real Vault/owner-data access occurred.

## Required disposition

Because Important findings remain, the required result is:

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
```

The repair cap should not be silently extended. A narrowly scoped follow-up must address CRLF frontmatter handling, cross-source identity namespace, resumed-scan checked counts, and explicit three-SHA metadata attribution, then rerun the direct matrix and this independent review.
