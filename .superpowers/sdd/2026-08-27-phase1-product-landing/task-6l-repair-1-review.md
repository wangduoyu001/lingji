# Task 6L Structured Evidence Lexical Wiring — Repair Round 1 Final Review

- Review date: 2026-08-28 (Asia/Shanghai)
- Review worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Reviewed HEAD: `1bbb4772f54405b305c90642d6d3cbde78f7b572`
- Repair product/test commit: `5258ecef98e2b58dfb9c12af585a4fbd44c260dd`
- Initial review: `c69afdc`
- Scope: independent read-only review; no product/test changes, live service, Artifact,
  Production, Vault, owner data, or real 8766/8767

## Verdict

```text
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 4
Minor: 1
Disposition: BLOCKED_AT_REPAIR_CAP
Acceptance: NOT ACCEPTED
```

The repair correctly wires the existing structured read model to the existing
`lingji_memory.db`/FTS, Gateway, Hybrid, ContextPack and MCP paths. Explicit revoke and
explicit expiry transitions pass the added focused tests; stable automatic source identity,
same-byte idempotency, citation fields, promotion quarantine and Vault non-write boundaries
also pass. The authorization bridge is not fail-closed for natural expiry, projection
failure, or an in-flight write racing revoke. Changed content is replaced in place and the
old content is not available in `history`, contrary to the requested v1→v2 contract.

## Review evidence

The inspected path is:

```text
StateDB / SourceRegistry
  -> AutomaticMemoryRuntime lifecycle listener
  -> SourceReadModel + memory_documents status projection
  -> Hybrid / Gateway / ContextPack / MCP current filtering
```

The lexical projection remains evidence-only (`memory_type=structured_evidence`,
`memory_tier=evidence`). It does not call promotion or write Obsidian. `raw_reference`,
role, sequence, source/conversation/message identity and content hash are present in the
formal citation path, as asserted by the passing focused tests.

## Important findings

### I1 — Natural grant expiry does not project into the memory index

**Severity:** Important — blocks acceptance.

`StateDatabase.list_automatic_memory_sources(now=...)` changes an authorized source to
`expired` (`src/storage/state_db.py:931-953`), and `SourceRegistry.list_sources()` returns
that result without calling `_notify_lifecycle()` (`src/automatic_memory/source_registry.py:177-182`).
The new projection is only notified by explicit `register`, `revoke`, and `set_status`
events (`src/automatic_memory/source_registry.py:61-68, 135-175`), or during runtime start
(`src/automatic_memory/runtime.py:182-195`). Thus a running runtime can observe StateDB
`expired` while the structured source and evidence document remain `active`.

Independent isolated repro using a real temporary Generic AI History pipeline and formal
Gateway:

```text
before 1
listed expired state expired
after 1
```

Expected: after the grant naturally expires, current Gateway/Hybrid/ContextPack/MCP
results are empty while history/as_of remains available. Actual: current evidence remains
searchable until restart or an explicit `set_status(..., "expired")` notification.

Required fix: make the natural expiry transition invoke or atomically include the existing
read-model projection, or add an equivalent current-query authority check. Preserve the
single rebuildable index and explicit history behavior.

### I2 — Projection exceptions are swallowed and leave current evidence active

**Severity:** Important — blocks acceptance.

`SourceRegistry._notify_lifecycle()` catches every observer exception and continues
(`src/automatic_memory/source_registry.py:61-68`). The lifecycle observer is the only new
StateDB-to-`lingji_memory.db` bridge; therefore a locked/corrupt/unavailable memory DB or
any projection exception can commit revoke in StateDB while leaving an active lexical
document in the current result set.

Independent isolated repro injected a projection failure after a real pipeline import:

```text
state revoked current 1 memory_status active
```

Expected: failure must fail closed (current result withheld) and be truthfully observable,
or the authorization transition must remain pending until the existing index is safely
projected. Actual: the authoritative source is revoked but current evidence is still
returned. The existing observer isolation semantics protect authorization commit but do
not protect the current retrieval security boundary.

Required fix: introduce durable/error-visible projection handling or a fail-closed current
read guard; do not silently treat an unprojected revoke as safe.

### I3 — Revoke can race an in-flight structured upsert and be undone

**Severity:** Important — blocks acceptance.

`SourceRegistry.revoke()` commits StateDB and then invokes the listener in a separate
transaction (`src/automatic_memory/source_registry.py:135-147`). Structured ingestion
upserts the source/read-model rows and then runs lexical sync in separate work
(`src/extraction/structured_sink.py:63-89`). `_upsert_source()` accepts the incoming
`StructuredSource.status` and updates the existing read-model source status. An in-flight
authorized write can therefore run after the revoke projection and write `active` back.

Independent isolated repro used a barrier immediately before the real read-model upsert,
revoked the source, then released the upsert:

```text
pipeline_alive False state revoked read_model active current 1
```

Expected: once revoke linearizes, no later in-flight write may make that source current;
raw/structured evidence may remain for history. Actual: StateDB is `revoked`, but the
read model and current Gateway result are active. This is a cross-database lifecycle race,
not merely a missing test.

Required fix: serialize/linearize lifecycle projection with structured writes, or condition
the write/project status on the current StateDB authority and re-project after a transition.
Add a real threaded revoke-vs-upsert regression.

### I4 — v1→v2 replacement does not preserve v1 in history

**Severity:** Important — blocks the stated update contract.

The stable automatic namespace correctly keeps source/conversation/message identity stable
(`src/extraction/adapters/generic_ai_history.py:104-131`). However, the existing
`message_records` upsert updates content in place (`src/sources/read_model.py:1271-1301`),
and `sync_structured_evidence()` uses one deterministic `memory_id` per message and
replaces its FTS chunks (`src/retrieval/memory_db.py:295-430`). No immutable old message
version or archived old lexical projection is created.

Independent isolated repro output:

```text
current_v1 0
current_v2 1
history_v1 0
history_v2 1
```

Expected: current returns only v2 and history retains v1 with explicit provenance/lifecycle;
same-byte replay remains a no-op and cross-source identities remain independent. Actual:
current returns only v2, but history has no v1 content at all. The repair tests assert only
that stale v1 is absent from current, so they do not prove the required history contract.

Required fix: retain immutable version evidence (or archive the prior projection with
validity/supersession metadata) while keeping one rebuildable index and stable identity
relationships.

## Minor finding

### M1 — Packaged helper does not prove fallback on packaged-ingested evidence

The requested packaged Qdrant helper passes, but
`tests/integration/test_automatic_memory_packaged_flow.py::_formal_qdrant_fallback()` uses
a pre-seeded Vault fact and injects a failing semantic provider in-process. It does not bind
the hit to an automatic-memory packaged ingestion identity. The direct Task6L focused test
does exercise a real pipeline-ingested structured message with a failing semantic client,
so this is a packaged-evidence coverage limitation rather than a separate product defect.

## Automated verification

All commands ran against isolated pytest fixtures in this worktree:

| Verification | Result |
|---|---|
| `tests/test_structured_evidence_lexical.py` | `9 passed, 1 warning` |
| structured/extraction/retrieval/context matrix | `57 passed, 1 warning` |
| candidate/source/temporal matrix | `46 passed` |
| runtime/discovery/Obsidian/worker matrix | `36 passed, 1 warning` |
| formal Gateway/MCP/ContextPack/Obsidian/promotion matrix | `75 passed` |
| packaged Qdrant lexical helper | `1 passed, 1 warning` |
| `python -m compileall -q src tests/test_structured_evidence_lexical.py` | PASS |
| `git diff --check c69afdc..HEAD` | PASS |
| `python scripts/check_acceptance_sync.py` | PASS |
| `python scripts/check_local_execution_handoff.py` | PASS |

The passing explicit revoke/expiry test proves the callback path, not natural expiry,
projection-error handling, or revoke/upsert concurrency. The Qdrant direct focused test
keeps the same pipeline-ingested structured evidence under semantic failure and reports
`semantic=degraded` / `reason_code=semantic_query_failed`; its citation includes raw
reference, role and sequence. No promotion seam, Vault Markdown write, candidate/Core
memory write, live endpoint, Artifact, Production, or owner data was used.

## Scope and cleanup

- Product HEAD and repair commit match the requested exact identities.
- No product or test files were modified during this review.
- Temporary repro roots under `/private/tmp/lj-review-*` were removed after inspection.
- Worktree was clean before adding this report; only this report is intended for the review
  commit.
- Task6 authority remains `IN_PROGRESS / NOT_ACCEPTED`; Task6H heartbeat, packaged crash
  matrix and owner/live acceptance remain outside this review.

## Final disposition

```text
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 4
Minor: 1
Disposition: BLOCKED_AT_REPAIR_CAP
Acceptance: NOT ACCEPTED
```

`ACCEPT_FOR_TASK6` is not allowed because Important findings remain. A further product
repair round is not authorized by this review boundary; the listed defects must be handled
under a newly approved task/repair scope.
