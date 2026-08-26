# Phase 1 Task 3 — Unified RAG Evidence

日期：2026-08-26
分支：`codex/phase1-automatic-memory`
产品提交：`163fa5d` (`feat: unify cited automatic memory context`)

## 结果

Task 3 focused and scoped regression gates pass. This report covers only the
unified ContextPack / MemoryGateway / MCP retrieval contract; it does not claim
the 100-question quality gate, release, owner acceptance, or Windows parity.

## TDD evidence

The required focused command was first run after adding the missing-provenance
test and produced:

```text
20 passed, 1 failed
AssertionError: 'linked_pending' == 'missing'
```

The implementation then changed provenance to `missing` unless the shared
SourceReadModel exposes an actual `message_memory_links` row. Linked evidence
upgrades the item to `structured` without inventing a citation.

## Verification

Focused command:

```text
./.venv/bin/python -m pytest -q \
  tests/test_automatic_memory_context_pack.py \
  tests/test_automatic_memory_mcp.py \
  tests/test_task7_timeline_retrieval.py
```

Result: `23 passed`.

Scoped regression command:

```text
./.venv/bin/python -m pytest -q \
  tests/test_automatic_memory_context_pack.py \
  tests/test_automatic_memory_mcp.py \
  tests/test_task7_timeline_retrieval.py \
  tests/test_memory_retrieval.py \
  tests/test_permanent_memory_gateway.py \
  tests/test_source_service.py \
  tests/test_memory_capability_contract.py
```

Result: `47 passed, 1 existing Pydantic deprecation warning`.

`git diff --check`: PASS.

## Contract coverage

- `current`, `as_of`, `history`, and `why` use the existing `TemporalQuery`.
- Current memory, project-authority memory, and linked raw message evidence are
  ordered deterministically and carry stable memory/source/conversation/message
  identifiers where those identifiers exist.
- Agent, privacy, and project scope are applied by the existing
  `SourceQueryService`; direct builder and gateway produce identical scoped
  identity lists.
- Duplicate evidence uses the normalized
  `(source_id, conversation_id, message_id, memory_id, content_hash)` identity.
- Rendered Markdown, headers, metadata, and citations are bounded to 12,000
  characters without emitting a partial citation.
- Missing semantic capability and semantic query failure are separate,
  call-local diagnostics; lexical results remain usable and exception text is
  not returned.
- The builder is wired to the existing SourceReadModel/SourceQueryService in
  bootstrap. No second database, retriever, permission implementation, or MCP
  backend was added.

## Frozen evaluation inputs

The Task 2 fixtures were read-only and unchanged:

```text
automatic_memory_corpus.jsonl    bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
automatic_memory_questions.jsonl 338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

## Not run / not claimed

No Artifact, Production, Vault, real AI application, real MCP client, Desktop
UI, Mac M5 owner acceptance, 10万-message performance test, or Windows test was
run. `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` remains `IDLE`; those gates must
be activated and verified by the root agent in later tasks.

Documentation commit: this report and the acceptance-log update are committed
separately from the product commit. The report intentionally does not embed a
self-referential SHA.

## Repair round 1

Independent review identified four important contract defects: implicit
current/why cache reuse across a time boundary, core memories bypassing
memory-type/tag filters, provenance being upgraded by an invisible link, and
why details not reaching rendered MCP Markdown. New regression tests were
written first. Their exact first run was:

```text
22 passed, 4 failed
```

The failures were the four named behaviors. The cache test initially used a
non-matching CJK FTS term; it was corrected to a matching synthetic term and
the test remained RED until the cache fix was applied. This repair report
cannot reconstruct the exact first-round RED output from the previous product
commit; that limitation is recorded rather than backfilled.

Product repair commit: `1a36296` (`fix: harden unified rag evidence`).

Repair focused command:

```text
./.venv/bin/python -m pytest -q \
  tests/test_automatic_memory_context_pack.py \
  tests/test_automatic_memory_mcp.py \
  tests/test_task7_timeline_retrieval.py
```

Result: `28 passed`.

Scoped regression command:

```text
./.venv/bin/python -m pytest -q \
  tests/test_memory_retrieval.py \
  tests/test_permanent_memory_gateway.py \
  tests/test_task7_timeline_retrieval.py \
  tests/test_source_service.py \
  tests/test_memory_capability_contract.py
```

Result: `40 passed, 1 existing Pydantic warning`.

The registered MCP-path regression uses a real MemoryGateway and proves
current stale exclusion plus why explanation in Markdown. Implicit current and
why cache entries are bypassed so wall-clock validity is always reevaluated;
explicit historical queries remain cacheable. Core sections now apply the same
memory type/tag contract. Provenance is upgraded only after visible,
scope-filtered evidence is actually returned. Why rendering emits only bounded
safe IDs and reasons, never arbitrary path/source metadata.

Fixture hashes remain unchanged:

```text
automatic_memory_corpus.jsonl    bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
automatic_memory_questions.jsonl 338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

`git diff --check` and `git diff 90832a1..HEAD --check`: PASS after removing
the report's pre-existing Markdown trailing spaces. Acceptance sync and local
handoff remain required below and were rerun before the repair documentation
commit.

## Repair round 2

Scoped review found that the production-exported enhanced retriever's bounded
short-Chinese fallback existed only on `search()`. ContextPack used inherited
`search_with_diagnostics()`, so a short query could work in direct search but
disappear from ContextPack, Gateway, and MCP.

New RED tests covered ordered identity parity for `current`, `as_of`,
`history`, and `why`, semantic absent/throwing diagnostics, ContextPack and
Gateway evidence, and the registered MCP path. Exact first run:

```text
12 passed, 3 failed
```

The three failures were the parity assertion, semantic-failure fallback
assertion, and registered MCP short-Chinese evidence assertion. The parity test
iterates all four temporal modes; its single failure represents the inherited
diagnostics result being empty for the short query.

Product repair commit: `e23cac5` (`fix: unify enhanced retrieval diagnostics`).

The existing enhanced fallback was moved behind one call-local helper used by
both `search()` and `search_with_diagnostics()`. The base retrieval path now
supports suppressing its internal `why` attachment so the enhanced path adds it
exactly once after fallback fusion. No mutable diagnostic state or second
retriever was introduced.

Focused verification:

```text
./.venv/bin/python -m pytest -q \
  tests/test_automatic_memory_context_pack.py \
  tests/test_automatic_memory_mcp.py \
  tests/test_task7_timeline_retrieval.py
```

Result: `31 passed`.

Scoped verification:

```text
./.venv/bin/python -m pytest -q \
  tests/test_memory_retrieval.py \
  tests/test_permanent_memory_gateway.py \
  tests/test_task7_timeline_retrieval.py \
  tests/test_source_service.py \
  tests/test_memory_capability_contract.py
```

Result: `40 passed, 1 existing Pydantic warning`.

The Task 2 frozen fixture hashes remain unchanged. `git diff --check` and
`git diff 90832a1..HEAD --check` pass. Artifact, UI, Production/Vault, Mac M5,
and Windows acceptance remain unrun.
