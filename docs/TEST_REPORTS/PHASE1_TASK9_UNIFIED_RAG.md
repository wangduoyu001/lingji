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
