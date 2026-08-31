# Task 1 Report — Bounded evidence backend and selected-resource contracts

## Result

`DONE_WITH_CONCERNS`

Implemented the bounded linked-evidence backend on branch
`codex/owner-memory-detail-drilldown` from base
`2859e378f9b3504776acf08e572deb82eedbdde5`.

## RED evidence

Exact command:

```text
python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py --tb=short
```

Observed baseline result:

```text
3 failed, 63 passed, 1 warning in 2.77s
```

The three failures were the missing `MemoryInspectorFacade.list_memory_evidence`
method, the missing authenticated evidence route (unauthenticated request was
404 rather than 401), and the missing bounded canonical route behavior.

## GREEN evidence

Exact focused command and final result:

```text
python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py --tb=short
..................................................................       [100%]
66 passed, 1 warning in 1.79s
```

Additional verification:

```text
python3 -m compileall -q src tests
git diff --check
```

Both exited successfully.

## Changed files

- `src/sources/service.py`: added `EvidencePage` and bounded evidence paging;
  metadata is authority-filtered first, sorted by UTC occurrence/sequence and
  stable identities, then only the selected page bodies are read. Item and
  page content budgets, truncation, and safe references are enforced.
- `src/gateway/memory_inspector.py`: added the facade paging seam without
  calling legacy unbounded `memory_evidence()`; added optional bounded
  `chunk_limit`, `max_chars`, and `cursor` canonical parameters while retaining
  the existing `{item: ...}` envelope and document fields.
- `src/control/api.py`: registered only the authenticated GET evidence route,
  with `limit` 1–50 and non-negative `offset`; wired bounded canonical query
  parameters on the existing selected-memory route.
- `tests/test_owner_memory_detail_contract.py`: isolated synthetic read-model
  fixture and RED/GREEN contract coverage for ordering, pagination, budgets,
  authority/privacy filtering, safe references, auth, and canonical bounds.

## Commits

- `b46229eb211e0e91a1f0c1c37e934702cd13fe3c` — `feat: add bounded owner memory evidence route`

## Self-review and security boundary

- Ordinary card projection and current-only behavior were not expanded; no
  card content field or unbounded evidence was added.
- The new route is GET-only, authenticated through the existing dependency,
  and has bounded pagination. No DELETE, database, queue, projector, state
  source, or port was added.
- Evidence rechecks viewer privacy/agent scope and requires an active source
  authority. Revoked, expired, restricted-lifecycle, archived, unavailable,
  or otherwise non-active source records are fail-closed before body exposure.
- Raw references are passed through the existing safe-reference sanitizer;
  sensitive metadata, cookies, and arbitrary JSON are not copied into evidence
  items. Canonical detail does not receive card conclusion/freshness/layer/action
  fields.
- The fixture is synthetic and isolated. No live 8766/8767 service, install,
  Artifact, Production/Vault, real chat, real database, or owner data was used.

## Concerns / limitations

- The existing unbounded `SourceQueryService.memory_evidence()` remains for its
  existing ContextPack compatibility caller; the new facade and route never
  call or expose it. A later cleanup must preserve that compatibility boundary.
- The existing focused suite emits its pre-existing Starlette/httpx deprecation
  warning; no new warning was introduced.
- No live, packaged, Desktop, or owner-observation validation was authorized
  for Task 1; those belong to later tasks/acceptance.
