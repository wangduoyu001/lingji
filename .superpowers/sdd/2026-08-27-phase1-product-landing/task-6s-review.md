# Task 6S Query-Time Source Authority + Evidence Versions — Independent Final Review

- Review date: 2026-08-28 (Asia/Shanghai)
- Review worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Reviewed HEAD: `bbdc037` (`docs: record Task6S authority and evidence versions`)
- Product/test commit: `5fb2966` (`feat: enforce structured source authority and versions`)
- Scope: independent read-only review; only this review file is added; no live 8766/8767,
  Artifact/release, Production, Vault, owner data, or product/test modifications

## Verdict

Spec: **FAIL**
Quality: **NEEDS_FIXES**
Critical: **0**
Important: **3**
Minor: **0**
Disposition: **REPAIR_ROUND_1**
Acceptance: **NOT ACCEPTED**

The intended StateDB query-time guard, automatic-source version identity, supersession
metadata, and lexical fallback are present and pass the focused and formal retrieval
matrices. The current-evidence boundary is not closed on all existing composition seams:
the base Hybrid cache can bypass a supplied authority resolver, a source-model rebuild
can leave an active orphan projection, and ContextPack linked evidence can bypass the
resolver entirely. These are current structured automatic-evidence isolation defects,
not cosmetic coverage gaps.

## Verified strengths

- `lingji_state.db` is the only authorization input to `SourceAuthorityResolver`; absent,
  unknown, revoked, expired, unavailable, locked, and malformed authority are denied.
  Ordinary non-automatic memories and ordinary Obsidian notes are not denied.
- Formal Gateway composition injects the resolver into the enhanced Hybrid retriever;
  formal Gateway search, ContextPack and MCP search use that composition. One resolver
  read covers the source IDs in a result set, and implicit current/why queries do not use
  a timeless cache key.
- The existing `lingji_memory.db`/`memory_documents`/FTS projection stores deterministic
  source/conversation/message/content-hash identities. Changed content archives the old
  active row with `valid_to`, `superseded_by`, `supersedes`, and a reason; same-byte replay
  is a no-op; cross-source identities remain independent.
- Ordered raw replay restores v1/v2 evidence, current/history/as_of behavior is covered,
  and Qdrant failure retains lexical results. No new database, table, retriever, queue,
  promotion seam, Core-memory write, or permanent authority was introduced by Task6S.

## Important findings

### I1 — Base Hybrid cache returns current evidence before authority re-check

**Evidence:** `src/retrieval/hybrid.py:139-144` returns a cache hit before the
`filter_current()` call at `:167-171`. Explicit `current`/`why` queries with `as_of` are
cacheable. The enhanced formal retriever applies a second final filter, but the public
base `HybridRetriever` still has this bypass when a StateDB resolver is supplied.

Isolated reproduction with a temporary SQLite source and the base retriever:

`first 1 second 1 revision 2`

The first search was authorized; the source was then revoked while a failing projection
listener kept the memory-index revision unchanged; the identical explicit current query
returned the cached result after revoke. This violates the requirement that current/why
authority be checked for every query and that cache not retain expired/revoked authority.

**Minimum repair boundary:** either never cache current/why results, or perform the
StateDB authority check on every cache hit (and preserve call-local truthful diagnostics),
including the base/direct Hybrid public path. Add a regression with explicit `as_of`,
revoke/expiry, unchanged derived-index revision, and a supplied resolver.

### I2 — Structured projection leaves active orphan evidence after source-model rebuild

**Evidence:** `src/retrieval/memory_db.py:398-480` only upserts rows currently returned
from `source_records`/`message_records`; the old removal loop was removed and `removed`
remains zero. This is correct for retaining superseded history, but it does not reconcile
an active projection whose source/message row disappeared during a read-model rebuild.

Isolated reproduction with the real automatic pipeline:

`before 1`
`after 1 [('active', '<authorized automatic source id>')]`

After `SourceReadModel.rebuild([])` and `sync_structured_evidence()`, the structured
source/message rows were gone but the old active `memory_documents` row remained current.
Because StateDB still reported the automatic source authorized, the query-time resolver
allowed the orphan result. This makes a derived index effectively authoritative and can
reveal stale evidence after a supported source/read-model rebuild.

**Minimum repair boundary:** reconcile missing active structured identities during the
existing rebuild/sync transaction by archiving them (or otherwise excluding them from
current) while retaining superseded/history rows and all existing content-hash/version
metadata. Prove rebuild/replay restoration and current exclusion without adding a store.

### I3 — ContextPack linked-message evidence bypasses source authority

**Evidence:** `src/retrieval/context_pack.py:192-243` calls
`SourceQueryService.memory_evidence()` for every selected memory and appends
`raw_message_evidence` without invoking `SourceAuthorityResolver`. The source query
service at `src/sources/service.py:220-261` applies privacy/project checks but not the
StateDB automatic-source decision.

Isolated temporary-root reproduction linked an automatic message to an ordinary memory,
revoked the automatic source, and built a current ContextPack:

`[('retrieved_memory', 'ordinary-anchor', None),
 ('raw_message_evidence', 'ordinary-anchor', '<automatic message id>')]`

The structured search result itself is denied, but the linked raw message is still added
to the current ContextPack. This violates the stated ContextPack composition boundary
for revoked/expired automatic structured evidence. The link can be created by existing
message-memory linking/promotion-compatible seams; no new database or API is required.

**Minimum repair boundary:** reuse the injected resolver on linked messages, batch-check
all automatic source IDs for the ContextPack invocation, and exclude denied linked
evidence while retaining ordinary linked evidence and truthful diagnostics. Preserve
viewer/project/privacy and history/as_of semantics.

## Automated verification

All tests used pytest temporary roots. No live service, Artifact, release, Production,
Vault, owner data, or real 8766/8767 was used.

| Verification | Result |
|---|---|
| Task6S tests + structured lexical tests | `17 passed, 1 warning` |
| Critical structured/extraction/retrieval/context candidate matrix | `57 passed, 2 warnings` |
| Formal Gateway/MCP/ContextPack/Obsidian/promotion matrix | `75 passed, 2 warnings` |
| Automatic-memory/structured/queue/runtime regression | `226 passed, 3 warnings` |
| Packaged Qdrant helper | `1 passed, 1 deselected, 1 warning` |
| `python -m compileall -q src tests/test_task6s_source_authority_versions.py` | PASS |
| `git diff --check 5fb2966^..bbdc037` | PASS |
| `./.venv/bin/python scripts/check_acceptance_sync.py` | PASS (`product-impacting files: 0`) |
| `./.venv/bin/python scripts/check_local_execution_handoff.py` | PASS |

The passing matrices prove the intended normal, revoke/expiry callback, version,
history/as_of, Qdrant-degraded, and ordinary-memory behavior. They do not cover the
three current-evidence bypasses above.

## Boundary and cleanup confirmation

- `HEAD` and product/test identity match the requested `bbdc037` / `5fb2966` pair.
- Worktree was clean before this report; no product or test file was modified.
- `LOCAL_EXECUTION_TASK.md` remains `IDLE`; no live/Artifact/Production/Vault action was
  started. Temporary reproduction roots were isolated under `/private/tmp` and were not
  left in the repository.
- Promotion, Vault, Core, Qdrant production data, and owner data were not mutated by the
  review.

## Final disposition

Spec: **FAIL**
Quality: **NEEDS_FIXES**
Critical: **0**
Important: **3**
Minor: **0**
Disposition: **REPAIR_ROUND_1**
Acceptance: **NOT ACCEPTED**

`ACCEPT_FOR_TASK6` is not allowed while any Important finding remains. The repair should
stay within the existing StateDB authority, MemoryDatabase projection, Hybrid/Gateway/
ContextPack composition, and source-query viewer boundaries; do not add a second DB,
retriever, queue, API, or permanent-memory source.
