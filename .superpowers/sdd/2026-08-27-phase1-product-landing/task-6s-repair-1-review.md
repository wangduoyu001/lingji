# Task 6S Repair Round 1 — Final Independent Read-Only Review

- Review date: 2026-08-28 (Asia/Shanghai)
- Review worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Reviewed HEAD: `284a838b7bfdf45094e6ba34738de2a597e8abeb`
- Repair product/test commit: `9692cf7dd74d1f1f7e29a0f255e1d4e41ccdbef6`
- Initial review: `1816d361542a86141eeb28de0d88c66899aa0ce1`
- Scope: final independent read-only review; only this report is added. No product/test
  files, live 8766/8767, Sidecar, Artifact/release, Production, Vault, or owner data
  were modified.

## Verdict

```text
Spec: PASS
Quality: ACCEPTED
Critical: 0
Important: 0
Minor: 0
Disposition: ACCEPT_FOR_TASK6
Task6S: ACCEPTED_FOR_TASK6
```

The three Important findings from `1816d361` are closed within the approved repair
boundary. Current/why evidence is never served from a warm cache, including explicit
`as_of`; source-read-model rebuilds atomically archive active orphan structured
projections while retaining history; linked ContextPack evidence uses the same batch
StateDB authority resolver. Ordinary history, Obsidian documents, promotion/Vault
boundaries, and Qdrant lexical degradation remain intact.

## Repair findings rechecked

### I1 — Current/why cache authority bypass: CLOSED

`HybridRetriever` no longer caches either `current` or `why` mode. This includes
explicit `as_of` combinations, so every invocation reaches the existing StateDB-backed
`SourceAuthorityResolver`. A warm-cache → revoke check returned no current result, and
natural expiry and StateDB unavailable/locked checks remained fail-closed with truthful
diagnostics. History and explicit `as_of` temporal behavior remained passing.

### I2 — Active orphan projection after read-model rebuild: CLOSED

`MemoryDatabase.sync_structured_evidence()` reconciles active `structured_evidence`
rows against source/conversation/message identities returned by the rebuild. Missing
identities are archived in the same SQLite transaction, with `valid_to` and
`invalidating_reason`; FTS/history remains available. The rebuild test observed zero
current results and an archived history result. The orphan query only targets
`memory_type='structured_evidence'`, and ordinary Obsidian documents were not archived.

### I3 — Linked ContextPack evidence bypass: CLOSED

`ContextPackBuilder` collects linked messages, resolves automatic source IDs from the
existing `SourceReadModel`, performs one batch `authorize_source_ids()` call, and only
then appends `raw_message_evidence`. Revoked/expired/unavailable StateDB authority does
not append automatic linked evidence; ordinary linked evidence remains compatible.
The same `MemoryGateway` composition is used by MCP `search_memory` and
`build_context_pack`, preserving source/conversation/message/content-hash identity and
viewer/project/privacy/temporal checks.

## Automated verification

All tests used isolated pytest temporary roots. No live or owner data was used.

| Verification | Result |
|---|---|
| Repair review-3 boundary tests (cache, orphan, linked evidence) | `3 passed, 1 warning` |
| Task6S + structured lexical tests | `20 passed, 1 warning` |
| Direct Task6S/Task6L/context/retrieval/MCP 59-case matrix | `59 passed, 1 warning` |
| Gateway/MCP/ContextPack/Obsidian/promotion 75-case matrix | `75 passed, 1 warning` |
| Automatic-memory/structured/queue/runtime broad regression | `269 passed, 3 warnings` |
| Task7 temporal/cache regression | `16 passed` |
| Packaged Qdrant lexical fallback helper | `1 passed, 1 deselected, 1 warning` |
| `python -m compileall -q src tests/test_task6s_source_authority_versions.py` | PASS |
| `git diff --check 1816d361..9692cf7` | PASS |
| `python scripts/check_acceptance_sync.py` | PASS (`product-impacting files: 0`) |
| `python scripts/check_local_execution_handoff.py` | PASS |

The broad automatic-memory run was intentionally wider than the historical 226-case
regression set and had no failures. The repair itself changes only the existing
retrieval/context/projection seams plus its focused regression tests; no new database,
table, queue, API family, retriever, promotion path, or permanent-memory source was
introduced.

## Boundary and cleanup

- Worktree was clean before this report; product/test diff is exactly the approved
  `9692cf7` repair (`context_pack.py`, `hybrid.py`, `memory_db.py`,
  `source_authority.py`, and its Task6S test).
- `LOCAL_EXECUTION_TASK.md` remains `IDLE`; no Artifact/release, live endpoint,
  Sidecar, Production/Vault, or owner-data action was started.
- Test temporary roots were isolated and no temporary reproduction files were left in
  the repository. No product or test modification was made during review.

## Final disposition

```text
Reviewed HEAD: 284a838b7bfdf45094e6ba34738de2a597e8abeb
Product/test commit: 9692cf7dd74d1f1f7e29a0f255e1d4e41ccdbef6
Critical: 0
Important: 0
Minor: 0
Verdict: ACCEPT_FOR_TASK6
Task6S: ACCEPTED_FOR_TASK6
Task6 overall: remains IN_PROGRESS / NOT_ACCEPTED pending its independent Task6H,
packaged crash, live/Artifact, and owner-acceptance gates.
```
