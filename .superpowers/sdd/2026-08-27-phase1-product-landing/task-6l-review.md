# Task 6L Structured Evidence Lexical Wiring — Independent Final Review

- Review date: 2026-08-28 (Asia/Shanghai)
- Review worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Product HEAD reviewed: `54fce7e` (`docs: normalize Task 6L report formatting`)
- Product/test baseline: `9ced68b` (`fix: index structured chat evidence for lexical retrieval`)
- Product documentation: `8983d20` (`docs: record structured evidence lexical wiring`)
- Previous repair review: `81ffaec`
- Scope: read-only product review; no live, Artifact, Production, or Vault data used

## Verdict

- Spec: **FAIL**
- Quality: **NEEDS_FIXES**
- Critical: **0**
- Important: **2**
- Minor: **2**
- Disposition: **REPAIR_ROUND_1**
- Acceptance: **NOT ACCEPTED**; `ACCEPT_FOR_TASK6` requires zero Critical and Important findings.

The lexical bridge is real and uses the existing structured read model, `lingji_memory.db` FTS, Hybrid retrieval, Gateway, ContextPack, and MCP seams. It does not create candidates, active/Core/current memory, promotion calls, or Vault documents. However, the current-query authorization boundary is not closed, and changed automatic snapshots can leave stale active evidence beside the new version. Both are correctness/security blockers for Task 6L.

## Evidence reviewed

The real path was exercised as:

`ConsistentSnapshot -> SnapshotJobRunner -> ExtractionPipeline.process_internal_next -> StructuredReadModelSink -> existing MemoryDatabase.sync_structured_evidence -> MemoryGateway/Hybrid/ContextPack/MCP`.

The implementation stores evidence projections in the existing `memory_documents`/FTS schema with `memory_type=structured_evidence` and `memory_tier=evidence`. The focused lexical tests, extraction/idempotency/retrieval/indexing/context/MCP matrix, runtime/discovery/Obsidian/control-API/worker regression, and direct Gateway/MCP/ContextPack/Obsidian/promotion-quarantine suites were run. Empty/unsupported inputs, role/sequence/time fields, same-source rescan behavior, cross-source identity separation, normal Obsidian rebuild preservation, semantic-provider degradation with lexical results retained, and promotion quarantine were covered by passing tests.

## Important findings

### I1 — Revoke/expired authorization leaks into current retrieval

**Severity:** Important — blocks acceptance.

The automatic authorization registry writes lifecycle state to `lingji_state.db`: `SourceRegistry.revoke()` delegates to `StateDatabase.revoke_automatic_memory_source_atomic()` (`src/automatic_memory/source_registry.py:135-147`, `src/storage/state_db.py:1253-1287`). The structured lexical projection reads lifecycle only from `memory_db.source_records.status` (`src/retrieval/memory_db.py:311-338`), and the automatic adapter creates its structured source with the default active status while carrying the authorized source ID only in metadata (`src/extraction/adapters/generic_ai_history.py:105-113,177-186`). There is no state-to-memory lifecycle bridge or current-query authorization join.

Fresh real-pipeline repro, using a temporary isolated database and formal Gateway, produced one current structured-evidence result before revoke and **one result after revoke**. The StateDB source was `revoked` while the memory source remained `active`. The same repro after setting the StateDB source to `expired` again returned **one current result** while the memory source remained `active`. This is not a test-only row insertion: the message was admitted through the actual snapshot runner and extraction pipeline, then queried through the production Gateway/Hybrid path.

Expected: current retrieval and current ContextPack/MCP responses must exclude revoked/expired source messages (history may retain them with an explicit lifecycle explanation). Actual: the revoked/expired message remains eligible as active current evidence. This is an authorization/data-isolation failure, not a missing-new-feature test gap; the absence of a bridge is the defect.

**Minimum repair boundary:** use the existing StateDB source identity already propagated in structured metadata to update/resolve the existing memory read-model source status at the lifecycle transition, or enforce the existing formal current-query seam against StateDB status. Keep one rebuildable memory index; do not add a second store. Add real-pipeline Gateway, ContextPack, and MCP revoke and expiry regressions, including semantic-degraded retrieval.

### I2 — Content update leaves two active current evidence versions

**Severity:** Important — blocks acceptance unless immutable-snapshot semantics are explicitly changed and tested.

`GenericAIHistoryAdapter` derives `source_scope` from the raw payload digest (`src/extraction/adapters/generic_ai_history.py:104-123`) and consequently derives source, conversation, and message external IDs from that digest (`:119-123,167-185`). A changed file therefore creates a new active structured source/message identity. The existing structured sync marks every active source as an active lexical document (`src/retrieval/memory_db.py:311-345`) and has no supersession/validity transition for the prior payload.

Fresh real-pipeline repro with the same authorized source and one message changed from `ORIGINAL` to `UPDATED` yielded two documents and one FTS hit for each old and new content. The second sync reported the new document as added while the old document remained current. This is distinct from the correctly idempotent byte-identical rescan.

Expected for the requested content-update behavior: stable source/conversation/message provenance with the message updated, or an explicit old-version archival/validity transition so current retrieval cannot return stale content. Actual: both versions are active and current. This can produce stale answers and duplicate current citations.

**Minimum repair boundary:** stabilize automatic snapshot identity independently of payload bytes and upsert changed message content, or explicitly archive/supersede the prior projection within the existing source/read-model/index transaction. Add a real automatic snapshot content-update test covering current and history modes, without introducing another index.

## Minor findings

### M1 — Raw reference is not carried into formal citation relationships

The structured sync entry includes `raw_reference` only inside the list-valued `sources` field (`src/retrieval/memory_db.py:352-355`). `_upsert_document()` copies a fixed scalar relationship set that omits `raw_reference` (`src/retrieval/memory_db.py:724-751`). Hybrid and ContextPack citation builders look for `relationships["raw_reference"]` (`src/retrieval/context_pack.py:155-163`), so formal Gateway/ContextPack citations expose source/conversation/message IDs and hash but not the explicit raw reference. The raw reference remains in the authoritative message row; this is provenance presentation loss, not a new data source or authorization leak.

### M2 — Structured ContextPack section omits role and sequence fields

The lexical result retains role/sequence and the linked raw-evidence path exposes role (`src/retrieval/context_pack.py:217-240`), but the direct structured projection section only copies IDs, hash, and optional raw reference (`:155-178`). A direct structured-evidence ContextPack therefore does not expose the message role/order at the selected section level even though those fields remain in the database and result relationships. Add the fields to the existing citation/section mapping if the public ContextPack contract requires the full message provenance tuple.

## Test and gate results

All commands were run in the review worktree against isolated test fixtures. Exact requested focused aggregate:

```text
55 passed, 1 warning in 0.92s
```

Additional runs:

```text
structured lexical tests: 7 passed, 1 warning
candidate regression matrix: 46 passed
runtime/discovery/Obsidian/control API/worker: 36 passed, 1 warning
direct Gateway/MCP/ContextPack/Obsidian/promotion quarantine: 75 passed
compileall: PASS
git diff --check 81ffaec..HEAD: PASS
python scripts/check_acceptance_sync.py: PASS (report-only current diff)
python scripts/check_local_execution_handoff.py: PASS
```

The passing matrix does not override I1: existing tests exercise read-model status transitions and do not connect StateDB revoke/expiry to the formal current-query path. No live UI or production acceptance task was started; `LOCAL_EXECUTION_TASK.md` remained IDLE. Temporary repro directories were moved to Trash after the repros.

## Required repair-round exit criteria

1. Re-run the real automatic snapshot pipeline and prove revoke and expiry remove affected evidence from current Gateway, ContextPack, and MCP results while preserving explicitly requested history behavior.
2. Prove changed content cannot leave stale and new active current documents for one source/message identity; verify same-source byte-idempotency and cross-source isolation remain green.
3. Preserve the existing `lingji_memory.db`/FTS and semantic snapshot seams, evidence-only tier/type, no candidate/Core/promotion/Vault writes, and transaction/rebuild behavior.
4. Add/update the Task6L acceptance report and tests with the above real-path evidence, then rerun focused, regression, compile, diff, acceptance-sync, and handoff gates.
