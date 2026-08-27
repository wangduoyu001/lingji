# Phase 1 Product Landing — Task 3 Repair Round 2 FINAL Independent Review

Date: 2026-08-27
Branch: `codex/phase1-automatic-memory`
Review target: `843b9cb2174026cbadb40810d3563eee86918c61`
Repair base: `3edbfc8`

## Scope and evidence policy

This was a read-only final capped review. The only filesystem write was this review report. No product, test, acceptance, index, live 8766/8767 service, Artifact/release, Production/configured Vault, owner data, cloud, or external software was used. Synthetic fixtures were created under temporary worktree directories and removed after each probe; no temporary probe directory remains.

Read in full or at the required authoritative sections: `AGENTS.md`, the Phase 1 product-landing Global Constraints, final Task 2 disposition, Task 3 brief, Repair Round 1 and Repair Round 2 rulings, `task-3-review.md`, `task-3-repair-1-review.md`, `task-3-repair-2-report.md`, relevant acceptance authorities, direct source/caller/test files, and `.superpowers/sdd/2026-08-27-phase1-product-landing/review-3edbfc8..843b9cb.diff`.

## Verification

Focused final repair suite:

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round2.py --tb=short
5 passed in 0.65s
```

Unfiltered direct Task 3 and affected-source regression matrix (including the historical Task 2 timing test, with no `-k` exclusion):

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round2.py tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_snapshot.py tests/test_extraction_worker.py tests/test_extraction_idempotency.py tests/test_automatic_memory_adapters.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py tests/test_obsidian_memory_scope.py tests/test_structured_ingestion.py --tb=short
223 passed, 7 warnings in 14.66s
```

The disclosed Task 2 daily-integrity timing test passed in this run, but remains quarantined and is not credited as a Task 3 repair. The warnings are existing HTTPX/Starlette, Pydantic/deprecation, and fixture warnings.

Additional gates:

- `./.venv/bin/python -m compileall -q src tests/test_automatic_memory_repair_round2.py tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py`: **PASS**.
- `git diff --check 3edbfc8..843b9cb`: **PASS**.
- `./.venv/bin/python scripts/check_acceptance_sync.py`: **PASS** (`no product-impacting changes detected` for the current worktree delta).
- `./.venv/bin/python scripts/check_local_execution_handoff.py`: **PASS** (`LOCAL_EXECUTION_TASK.md` remains `IDLE`).
- No listener was present on TCP 8766 or 8767 after the probes.

## Independent behavioral review

### A — Obsidian frontmatter and path boundary: PASS

The direct matrix and an independent temporary-vault probe covered LF, CRLF, UTF-8 BOM+LF, BOM+CRLF, managed-directory explicit `false`/`true`, other-directory explicit `false`/`true`, malformed and unclosed input, and the 8192-byte bound. Explicit `false` won over managed-directory eligibility; malformed/unclosed input was excluded; body sentinels were not consumed. Ordinary no-frontmatter notes consumed only the marker probe and never their body. Symlink and outside-vault decisions remained `symlink` and `outside_vault`.

The implementation is bounded at `src/obsidian/memory_scope.py:158-198`; enumeration remains the existing `src/obsidian/discovery.py:158-160` path and does not introduce a body-reading alternate path.

### B — Automatic identity and idempotency: PASS

An independent full runtime/pipeline probe (not adapter-only) created two separately authorized Generic AI History roots containing byte-identical files with the same conversation/message IDs. Each route-equivalent scan created a durable snapshot job; both jobs reached `completed`; the structured read model contained two sources, two conversations, and two messages, with two distinct `automatic_memory_source_id` values and external IDs. A second scan of the same authorized source reused the existing idempotency row: one durable extraction job and one structured source/conversation/message set remained.

The same probe confirmed the real authenticated in-process `/api/automatic-memory/scan` route returned 200 with a real `work_id`, and the job reached terminal completion without an orphan running scan. A direct/manual `GenericAIHistoryAdapter` request without the automatic-memory option retained its content-derived identity; automatic requests without a usable source ID likewise did not invent a source namespace.

Relevant implementation: `src/extraction/adapters/generic_ai_history.py:103-185`, `src/extraction/pipeline.py:440-500`, `src/extraction/queue.py:610-691`.

### C — Resume, Work Fact, and callback ordering: PASS

Independent deterministic probes used ten files and both 30% and 70% pause points with two worker timing variants:

- worker processed the checkpointed jobs before resume;
- worker processed only after resume.

In both variants the paused scan remained `paused`, the Work Item remained `accepted`, and no terminal Outcome existed while paused. After resume, the durable scan became `completed`; the terminal Work Fact reported `已检查 10 个来源文件`, with no forged zero count, and `_scan_reports` was empty. Queued/reused values reflected actual admission results.

A callback-before-report probe made the extraction worker finish after durable scan finalization but before `_scan_reports` assignment. The callback completed the Work Fact using durable job evidence; the eventual normal flow retained the truthful one-file summary and released `_scan_reports`.

Relevant implementation: `src/automatic_memory/runtime.py:345-376`, `src/automatic_memory/checkpoint.py:245-422`, `src/work/store.py:166-336`.

### D — Evidence identity and full-range review: FAIL (Important I7 below)

The product/test and evidence artifact identities are truthful: `7058da0` and `b83232d`. The final checked-out metadata-only commit is `843b9cb`, confirmed by `git show --stat 843b9cb`; it changes the Round 2 report and acceptance entry. However, the current Round 2 report and acceptance entry do not record `843b9cb` as the metadata correction commit. There is no pending placeholder now, but the final three-commit chain is still under-described.

## Findings

### Important I7 — Round 2 final metadata omits the metadata correction commit

Locations:

- `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-2-report.md:5-7`
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md:1733-1738,1753-1757`

Exact reproduction:

1. `git rev-parse HEAD` returns `843b9cb2174026cbadb40810d3563eee86918c61`.
2. `git show --stat 843b9cb` shows a metadata-only change to the Round 2 report and acceptance log.
3. The report records only `Product/test commit: 7058da0` and `Evidence artifact commit: b83232d`.
4. The acceptance entry records `7058da0` and `b83232d` but has no `Metadata correction commit: 843b9cb` line, including its final report block.

Impact: the evidence package cannot unambiguously map the authoritative Round 2 metadata to the reviewed HEAD or distinguish the evidence artifact commit from the later metadata correction. This fails the explicit D requirement for truthful `7058da0` / `b83232d` / `843b9cb` attribution and prevents a zero-Important final disposition.

Minimal boundary: in a separately authorized metadata-only follow-up, add the exact three-way identity to both authoritative entries: product/test `7058da0`, evidence artifact `b83232d`, metadata correction `843b9cb`. Do not include a pending placeholder and do not self-reference the future review commit. This is documentation/evidence governance only; it must not alter product behavior or reopen a third product repair round.

No Critical finding was confirmed.

## Prior findings and regression boundaries

- I1 revoked/malformed internal snapshot jobs: **PASS**. Direct worker and queue probes ended invalid jobs in terminal `failed` state, emitted lifecycle failure, did not re-lease them, and allowed a valid neighboring job to complete.
- I3 sensitive names and nested directories: **PASS**. Case-folded separator-aware variants (`credentials`, `auth-token`, `cookie`, `private`, token/credential forms) and sensitive nested directories were excluded; safe history files remained eligible; symlink and outside-root files were excluded.
- I5 scan route: **PASS**. Real in-process route dispatch used the composed runtime, returned a real work ID, and no runtime-absent 409 path created a scan. No orphan running scan was observed.
- I6 Work Fact consistency: **PASS**. Work Item source IDs matched the authorized source IDs; terminal Work Item status and Outcome status agreed in completed and failed paths. Resume count behavior is covered under C.
- I8 zero configured-Vault mutation: **PASS**. An independent raw/structured flow left a sentinel configured Vault tree byte-for-byte unchanged while raw evidence and structured source/conversation/message rows persisted.

The full-range diff contains only the existing runtime, Generic AI adapter, bounded Obsidian reader, focused tests, and Task 3 evidence/authority files. No hidden alternate store, parser, queue, API, indexer, UI, retrieval/vector, quality, release, or Artifact implementation was introduced. No Task 2 lifecycle/timing code was changed; the historical timing result remains disclosed/quarantined. No automatic promotion seam (`evaluate`, `promote`, `submit`, `reconcile_incomplete_projections`, or `rebuild_derived_projections`) was invoked by the reviewed paths. No test was deleted, weakened, skipped, or converted to a false pass.

## Final verdict

The four behavioral Repair Round 2 findings pass independently, and no Critical defect was found. The final evidence metadata requirement still has Important I7 open.

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
```

The final repair cap is exhausted; do not authorize a third product repair round. Resolve only the narrowly bounded metadata attribution through an authorized evidence/documentation follow-up before reconsidering the Task 3 final disposition.
