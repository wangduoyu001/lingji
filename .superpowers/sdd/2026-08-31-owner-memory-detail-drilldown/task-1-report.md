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

## Fix Round 1/5 — review closure

Fix base: `2d9d4cbe` (`docs: record bounded evidence backend verification`).

### Review RED

After adding focused regression tests for the three Important findings, the
final valid RED run of `tests/test_owner_memory_detail_contract.py` was:

```text
3 failed, 5 passed, 1 warning in 1.13s
```

The failures were the pre-fix `SELECT *` metadata read, adversarial raw
reference values passing through, and unknown-memory evidence returning 200.
Invalid fixture-only assertions were corrected before recording this RED.

### Fixes

- `SourceReadModel.get_message(..., include_content=False)` now selects an
  explicit metadata projection with bounded preview/length expressions and
  never materializes the full `content` column. The contract fixture traces
  SQL and records that only selected-page rows request full bodies.
- Evidence uses a dedicated strict reference sanitizer. It permits only
  canonical safe `raw:`/`vault:` relative references (and existing sanitized
  HTTP(S) URLs), rejecting JSON/object-like, credential/auth/cookie-bearing,
  traversal, and absolute-outside-root values.
- `MemoryInspectorFacade.list_memory_evidence` performs a lightweight
  `fetch_memory(..., include_chunks=False)` existence check, preserving 200
  empty pages for existing memories with no links and translating unknown
  memory to the established 404 path.
- Added direct regressions for `include_content=False`, invalid timestamps and
  sequences, route/facade unknown-memory 404, SQL projection, page-only body
  reads, and adversarial reference response values.

### Fix GREEN

Exact Task 1 focused command:

```text
python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py --tb=short
.......................................................................  [100%]
71 passed, 1 warning in 1.93s
```

Direct read-model regression command (focused command plus
`tests/test_source_read_model.py`):

```text
78 passed, 1 warning in 2.04s
```

Additional verification remained green:

```text
python3 -m compileall -q src tests
git diff --check
```

### Fix files and identity

Changed in this round:

- `src/sources/read_model.py`
- `src/sources/service.py`
- `src/gateway/memory_inspector.py`
- `tests/test_owner_memory_detail_contract.py`

Fix commit: `b7f4829ff5a342154ec99c62951b4b4349892f86` — `fix: close bounded evidence review gaps`.
The original implementation and report commits remain
`b46229eb211e0e91a1f0c1c37e934702cd13fe3c` and `2d9d4cbe`.

Round 1 remains focused-only: no live services, installation, Artifact,
Production/Vault, real chats, real databases, or owner data were accessed.

## Fix Round 2/5 — prefixed absolute reference closure

Fix base: `4de66920` (`docs: append evidence review closure`). The sole open
finding was that the evidence-only sanitizer still accepted values such as
`raw:C:/Users/owner/private.json`.

### RED

Added a response-level adversarial matrix covering Windows drive paths in both
cases and slash styles, POSIX/UNC forms (`//server/share` and
`\\\\server\\share`), `file:` URI forms, and percent-encoded absolute paths.
The matrix also retains valid `raw:relative/path.json` and
`vault:folder/note.md` references and checks that normal relative names remain
allowed. The pre-fix contract run was:

```text
1 failed, 7 passed, 1 warning in 1.15s
```

The failure was the old sanitizer returning `raw:C:/Users/owner/private.json`.

### GREEN

The evidence strict sanitizer now percent-decodes the prefixed payload before
checking POSIX and `PureWindowsPath` absolute/drive/UNC semantics, traversal,
backslashes, sensitive tokens, and JSON-like values. The broad sanitizer used
by ordinary source APIs is unchanged.

Exact focused + direct read-model command:

```text
python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py tests/test_source_read_model.py --tb=short
........................................................................ [ 92%]
......                                                                   [100%]
78 passed, 1 warning in 2.20s
```

Also passed:

```text
python3 -m compileall -q src tests
git diff --check
```

### Identity

Fix implementation/test commit:
`b7b70468316fbf0bf318cabc0f72ac49cc3b2150` —
`fix: reject prefixed absolute evidence references`.

The report append is committed separately after this entry; previous fix
commit `b7f4829ff5a342154ec99c62951b4b4349892f86` and report commit
`4de66920` remain part of the Task 1 history. No live service, installation,
Artifact, Production/Vault, real chat, real database, or owner data was used.
