# Phase 1 Task 2 follow-up — Golden evaluation contract

## Result

```text
Product implementation: PASS
Deterministic quality gate: PASS
Real owner/Artifact acceptance: NOT_RUN (LOCAL_EXECUTION_TASK.md is IDLE)
```

Product commit: `746aea9` (`test: define automatic memory quality gate`).
Docs/report commit: `81ef6da` (`docs: record automatic memory evaluation contract`).

## Scope and safety

This change freezes evaluation evidence only. It does not modify retrieval,
ContextPack, MemoryGateway, MCP, promotion, Desktop, adapters, databases, or
queues. The corpus and questions are hand-authored synthetic records with
stable IDs. No network, model, Production, Vault, real conversation, secret,
or owner data was read.

## RED / GREEN evidence

```text
RED command:
./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py
RED result:
2 collection errors; ModuleNotFoundError: src.automatic_memory.evaluation

GREEN command:
./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py
GREEN result:
33 passed in 0.35s

Automatic-memory regression command:
./.venv/bin/python -m pytest -q tests/test_automatic_memory_adapters.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_watcher.py tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py
Result:
184 passed, 3 existing warnings in 9.80s

Compile/diff:
py_compile PASS; git diff --check PASS
```

## Frozen fixture evidence

```text
automatic_memory_corpus.jsonl: 100 records
automatic_memory_questions.jsonl: 100 questions
category counts: stable_preference=20, current_project_decision=20,
superseded_decision=15, cross_session=10, authority_conflict=10,
protected_candidate=10, scope_negative=5, temporal_explanation=5,
context_dedup=5

corpus SHA-256: a5e2b14be25dfdde2d8fdb5eb3971262cdb2ed7f4fdf7dd47960a8a6180c7d4c
questions SHA-256: c35347e2a1c987dd420eee059388eb380f0b7278eee247dd359550df02f82181
```

The parser requires all fields in the declared dataclasses, unique fact,
message, citation, and question IDs, and literal expected/forbidden evidence
IDs. It rejects blank JSONL records, duplicate evidence, missing evidence,
secret-like values, and absolute/path-like values. The evaluator rejects
incomplete or duplicate 100-question runs and does not trust caller-supplied
derived result counts.

## Gate mutation evidence

The focused gate suite covers these independent mutations:

```text
89.999 recall / 90.0 recall boundary       FAIL / PASS
94.999 citation, activation, MCP / 95      FAIL / PASS
89.999 context reduction / 90              FAIL / PASS
one protected false promotion              FAIL
one stale current leak                     FAIL
one duplicate record                       FAIL
one Production write                       FAIL
99 answered questions                      FAIL
mismatched message or role/order counts    FAIL
zero fact/citation/activation/MCP denominator FAIL
missing owner evidence                     BLOCKED
missing reboot evidence                    BLOCKED
measured failure plus missing evidence     FAIL (precedence)
NaN metric                                 FAIL
```

Gate order is deterministic: measured failure first, then missing owner/reboot
evidence or explicit blocked reasons, and only then PASS. Percentages are on a
0–100 scale and the report retains numerator and denominator fields.

## Files and review

Product/test commit `746aea9` contains:

- `src/automatic_memory/evaluation.py`
- `src/automatic_memory/__init__.py`
- `tests/evaluation/fixtures/automatic_memory_corpus.jsonl`
- `tests/evaluation/fixtures/automatic_memory_questions.jsonl`
- `tests/evaluation/test_automatic_memory_quality.py`
- `tests/test_automatic_memory_acceptance_gate.py`

The acceptance-log update and this report are in the follow-up docs commit.
Self-review found no production retrieval or data-source changes, no network
calls, no real-data fixtures, and no threshold relaxation. Existing test-suite
warnings are unchanged and are not introduced by this task.

## Concerns and limits

- This is an automatic contract gate only; no real Artifact, Desktop, owner,
  reboot, Mac, or Windows evidence was run.
- The current local execution task remains `IDLE`, so no local acceptance was
  started.
- The frozen corpus intentionally does not claim retrieval quality; later RAG
  work must consume these expectations without editing them to improve scores.
