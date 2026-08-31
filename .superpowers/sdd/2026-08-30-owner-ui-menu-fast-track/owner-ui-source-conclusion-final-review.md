# Owner UI Source Filter + Conclusion Persistence Final Review

Date: 2026-08-31
Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards`
Reviewed product commits: `8ec447e06a846c3c3edb345ae979b5ee65fb7379`, `4ce1e00acb17bc5e4e4c183f58d30551ef76b101`
Scope: read-only review of source discovery filtering and owner memory conclusion persistence.

## Verdict

```text
Spec: PASS
Quality: APPROVED
Critical: 0
Important: 0
Minor: 0
Mac rebuild: allowed to proceed under the new ACTIVE acceptance task
```

This is an automated/code review disposition only. It does not claim a macOS rebuild,
packaged installation, live 8766 validation, owner observation, release, Phase 1 PASS,
or merge.

## Source discovery filter

- `MemorySourcesApi.snapshot()` preserves the raw `/api/automatic-memory/discovered`
  response, including `not_found` records and their diagnostic fields. The derived
  `sources` list is the ordinary owner-facing projection.
- `mergeSourceFacts()` omits an unauthorised `not_found` candidate from ordinary cards,
  so it cannot expose an authorization action or inflate the visible/found count.
- `available`, `consent_required`, and `unsupported` candidates remain visible.
- A matching authorized lifecycle record is retained even when discovery reports
  `not_found`; `revoked` is projected as `revoked` and does not become a takeover offer.
- The owner-facing source summary now counts `sources.length`, i.e. the visible
  projection, rather than raw discovery length.
- `canonicalSourceKey()` still collapses only macOS lexical `/tmp` ↔ `/private/tmp`
  and `/var` ↔ `/private/var` aliases. Windows path distinctions remain covered.

## Conclusion persistence and fail-closed behavior

- Existing `conclusion`, `current_conclusion`, and `summary` values are copied into
  the existing `relationships_json` projection by `MemoryDatabase._upsert_document()`.
- Precedence is explicit and deterministic: a non-empty value on the entry wins;
  otherwise the corresponding value in `properties` is used. The projector then
  checks fields in `conclusion`, `current_conclusion`, `summary` order.
- The same `OwnerMemoryCardProjector` output supplies list and detail responses, and
  the UI consumes the shared `conclusion` field for both surfaces.
- A conclusion is returned only when bounded evidence exists, every referenced link
  verifies, and no conflict is present. Missing evidence, link mismatch, unavailable
  source reads, or other projection faults remain `None`.
- The repair adds no table, permanent fact source, queue, or architecture boundary;
  it only extends the existing rebuildable relationship projection.

## Verification

Fresh commands on the reviewed tree:

| Check | Result |
|---|---|
| `python3 -m pytest -q tests/test_owner_memory_card_api.py tests/test_owner_memory_card_projector.py` | `36 passed, 1 warning` |
| `npm run test:memory-sources` | PASS |
| `npm run test:owner-ui-menu-fast-track` | PASS |
| `npm run test:e2e:memory` | PASS |
| `npm run test:smoke` | PASS (23 scripts) |
| `npm run build` | PASS (97 modules; existing Vite dynamic-import warnings only) |
| `python3 -m compileall -q src/gateway/owner_memory_cards.py src/retrieval/memory_db.py tests/test_owner_memory_card_api.py tests/test_owner_memory_card_projector.py` | PASS |
| `git diff --check` | PASS |

The focused conclusion tests cover all three persisted fields, entry-over-properties
precedence, list/detail equality, verified evidence, and no-evidence `None`. The source
smoke covers raw not-found filtering, visible status preservation, authorized/revoked
lifecycle retention, visible count wording, and macOS/Windows path-key behavior.

## Historical failure and next acceptance boundary

The prior `6ea11e4` packaged owner observation remains a failure evidence boundary for
duplicate Codex aliases and a displayed `not_found` archive candidate. Its evidence and
root must remain read-only and separate. The next candidate is precisely
`4ce1e00acb17bc5e4e4c183f58d30551ef76b101`, with the new acceptance root
`/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a`, under the task's required
synthetic seed and pending Mac rebuild/full-root Computer Use observation.
