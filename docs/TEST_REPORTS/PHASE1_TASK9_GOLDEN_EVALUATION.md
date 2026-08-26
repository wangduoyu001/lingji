# Phase 1 Task 2 — Golden evaluation contract repair

## Result

```text
Product/test implementation: PASS
Deterministic quality gate: PASS
Real Artifact/owner acceptance: NOT_RUN (LOCAL_EXECUTION_TASK.md is IDLE)
```

Product/test commit: `e8b620e` (`test: define automatic memory quality gate`).
This repair changes only evaluation code, synthetic fixtures, and their tests;
retrieval, ContextPack, MemoryGateway, MCP, promotion, Desktop, adapters,
databases, and queues are unchanged.

## TDD evidence

The adversarial RED command was run after the new behavior tests were written,
before the evaluator/fixtures repair:

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py
55 failed, 13 passed in 0.67s
```

Failures were the intended missing contracts: corpus relationship fields and
semantic size, identity-aware scoring, raw context counts, strict nested row
validation, and the expanded report shape. After the repair, the same command
produced:

```text
86 passed in 0.54s
```

The automatic-memory focused regression command produced:

```text
238 passed, 3 warnings in 8.77s
```

`py_compile` and `git diff --check` passed. The warnings are existing
Starlette/httpx, duplicate ZIP fixture, and Pydantic deprecation warnings.

## Frozen fixture and semantic audit

```text
automatic_memory_corpus.jsonl: 145 records
automatic_memory_questions.jsonl: 100 questions
corpus SHA-256: bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
questions SHA-256: 338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

Question category counts are exact: stable preferences 20, current project
decisions 20, superseded decisions 15, cross-session facts 10, authority
conflicts 10, protected/Core/high-risk candidates 10, scope negatives 5,
temporal `as_of/history/why` questions 5, and ContextPack dedup questions 5.

The corpus is deliberately larger than 100 because the relationships require
additional evidence:

- Every superseded and temporal question has an old and active replacement
  joined by `topic_key` and `supersedes_fact_id`.
- Every cross-session question expects records from two distinct
  `conversation_id` values.
- Every authority conflict retains both `owner-confirmed` and
  `assistant-suggestion` records.
- Scope negatives vary project, privacy, and agent scope; their expected set
  is intentionally empty and their forbidden fact is literal.
- Every dedup question has primary and duplicate evidence sharing the same
  `content_hash`.

Queries and content are distinct natural-language scenarios; no mechanical
`Synthetic ... N` template remains. Expected fact and citation IDs are
hand-authored in JSONL and never generated from retrieval behavior.

## Validation and gate repair

`score_question` now receives `Mapping[str, CorpusRecord]` identity and rejects
unknown, duplicate, extra, or forbidden facts; unknown, duplicate, extra, or
fact-mismatched citations; and malformed context lengths. Question loading
checks that every expected citation belongs to an expected fact. A passing
result contains exactly the hand-authored expected fact/citation sets.

`EvaluationReport` now stores `baseline_context_chars` and
`rendered_context_chars`. `evaluate_run` requires positive baseline and
`0 <= rendered <= baseline`, then computes context reduction from those raw
counts. The gate independently recomputes and verifies that percentage, so a
forged caller-provided `90.0` cannot pass.

All raw counters are strict non-boolean integers with valid numerator and
denominator relationships. All percentages are strict finite numbers in
`[0, 100]`. Zero denominators, booleans, floats in raw counters, NaN,
Infinity, out-of-range percentages, incomplete runs, duplicate complete
questions, non-mapping rows, nested secret-like keys/values, Unix absolute
paths, Windows drive paths, UNC paths, PEM headers, Bearer values, and
password/token assignments fail closed.

Threshold mutation tests cover recall 89.999/90, citation/activation/MCP
94.999/95, context reduction 89.999/90, one protected false promotion, one
stale leak, one duplicate, one Production write, 99/100 questions, mismatched
message/role counts, zero denominators, missing owner evidence, missing reboot
evidence, and measured-FAIL precedence over BLOCKED.

## Privacy and secret scan

The fixture parser recursively scans every mapping key and nested value. The
focused suite exercises `/root`, `/etc`, `/opt`, `/workspace`, Windows drive
and UNC paths, PEM, Bearer, password, token, and nested `api_token` values.
The repository fixture scan found no path or secret markers and no real owner
data. No network, model, Production, Vault, real chat, credential, or owner
path was read.

## Repair round 2 evidence

New RED tests first failed against the prior implementation on the required
semantic and identity behaviors: `question-041` did not retain both old and
replacement history records; `question-091` used a July as-of date and exposed
the replacement instead of January's old fact; `evaluate_run` lacked the
corpus-first argument; direct forged results bypassed corpus-aware scoring; and
None/non-sequence evidence surfaced as `TypeError` instead of
`EvaluationInputError`.

The repair-round focused RED result was `16 failed, 69 passed`; after the
implementation it was `86 passed`.

The repair makes `evaluate_run(corpus_by_fact, questions, results, ...)` replay
every supplied result through `score_question` and compare the complete
`QuestionResult`. It also detects Windows drive/UNC paths embedded in natural
language such as `backup=C:\\Users\\...` and `see \\\\server\\share\\...`,
including nested values.

## Files and self-review

Product/test commit `e8b620e` contains:

```text
src/automatic_memory/evaluation.py
tests/evaluation/fixtures/automatic_memory_corpus.jsonl
tests/evaluation/fixtures/automatic_memory_questions.jsonl
tests/evaluation/test_automatic_memory_quality.py
tests/test_automatic_memory_acceptance_gate.py
```

Self-review confirms no retrieval or other production subsystem files changed,
no acceptance threshold was weakened, and the corpus is fully synthetic.

## Concerns / limits

The local execution task remains `IDLE`; no Artifact, Desktop, reboot, owner,
Mac, or Windows acceptance was run. This gate constrains later RAG tuning but
does not itself claim real retrieval quality. Existing unrelated warnings
remain as noted above.
