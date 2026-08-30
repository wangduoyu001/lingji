# Task 3 — Frozen 100-question diagnostic report

## Verdict

```text
Decision: MEASURED_FAIL
Product/tests commit: 191ffd6 (test: add frozen automatic memory oracle)
Report commit: docs/evidence commit containing this report
Quality artifact: output/validation/task-3-frozen-quality.json
Quality artifact SHA256: 80503dc3c27ffbc981636623334faedbe3b290df82961a4b3babab9e83a58e01
```

The oracle and runner integration are implemented and tested. The frozen run does not meet the
existing acceptance thresholds; no retrieval or product repair was attempted.

## Fixture audit

The audit verified 145 corpus rows and 100 questions. Existing corpus/question fields were compared
against baseline `3cb45340de5afe1d8451aed41eece940954c0db3`: all existing fields were unchanged
(145/145 and 100/100). No query, wording, category, mode, expected fact/citation, forbidden fact,
threshold, or source content was changed.

Only metadata provable from the corpus was added:

- corpus `sequence` (0 for each independent conversation; all 145 conversations are unique);
- question expected source/message identities (106 each);
- disallowed source/message identities (100 each);
- expected answer atoms (106);
- explicit negative expectation (5 questions);
- `mcp_expectation=strict_parity` and `max_chars=4000` for all questions.

| Fixture | Count | SHA-256 |
|---|---:|---|
| corpus | 145 | `2a3ea2c14af9e1705a39673efb50826579f35b484f9d6c5442cb40f5f8f2347a` |
| questions | 100 | `35000a5cc56de84ef3caa82114a1b9168e46c1d3b31fd89ba0f2a740ce6f9e31` |

Question categories: stable_preference 20, current_project_decision 20, superseded_decision 15,
cross_session 10, authority_conflict 10, protected_candidate 10, scope_negative 5,
temporal_explanation 5, context_dedup 5. Modes: current 94, history 3, as_of 2, why 1.

## TDD evidence

The required RED command was attempted first:

```text
./.venv/bin/pytest -q tests/test_task7p_frozen_oracle.py tests/evaluation/test_automatic_memory_end_to_end.py --tb=short
```

It exited 127 because this worktree has no `.venv`. The equivalent system pytest then produced the
expected pre-implementation collection failure: `ModuleNotFoundError: src.automatic_memory.quality_oracle`.

After implementation:

- focused oracle + end-to-end: `28 passed, 1 warning`;
- direct Task7 matrix: `236 passed, 1 warning`;
- compileall, `git diff --check`, acceptance sync, and local handoff: PASS.

The oracle enforces a closed observation/result schema, ordered immutable identities, citations,
answer atoms, mode/as-of, the 12,000-character hard cap, forbidden evidence counts, explicit
fallback reasons, atomic per-question checkpoints, and run/fixture/commit checkpoint identity.
The quality runner calls the existing `MemoryGateway` and formally registered production
`create_mcp_server`; it does not add a retrieval path or an LLM judge.

## Exactly one frozen quality run

Command:

```text
python3 scripts/automatic_memory_quality_gate.py --output output/validation/task-3-frozen-quality.json
```

The artifact was generated around 2026-08-30 17:05 Asia/Shanghai, exited 1, and is bound to
`code_commit=3cb45340de5afe1d8451aed41eece940954c0db3` with run identity
`quality:2a3ea2c14af9e170:35000a5cc56de84e:3cb45340de5afe1d`. The artifact has 100 top-level
`question_diagnostics` records and no `question_results` field. It was not overwritten and the CLI
was not run again after product/tests commit.

| Measure | Result | Threshold/status |
|---|---:|---|
| questions executed | 100 | required 100 |
| exact valid facts | 0/106 | 0%; required >=90%, FAIL |
| citation accuracy | 0/106 | 0%; required >=95%, FAIL |
| formal MCP parity | 0/100 | 0%; required >=95%, FAIL; all `retrieval_empty` |
| forbidden false positives | 0/100 | <=5%, PASS |
| duplicate records | 0 | required 0, PASS |
| Gateway calls / empty responses | 100 / 100 | path observed; retrieval misses |
| context baseline | NOT_MEASURED | required measurement missing |
| semantic degradation | FAILED | semantic query failed; no retrieval change |
| corruption isolation | FAILED | attempted 2, completed 1, failed 1, continued 1 |
| Production pollution | null / NOT_MEASURED | required measurement missing |
| automatic Core writes | 0 active; 145 pending owner review | no automatic Core write observed |

Artifact per-question buckets are `retrieval=95` and `provenance=95`; the five explicit negative
questions pass. The aggregate formal MCP parity measurement records 100 failures with reason
`retrieval_empty`. The final product/tests commit additionally maps a parity failure to the `mcp`
bucket, verified by focused tests; because the frozen CLI was intentionally not rerun, that later
mapping is not substituted into the historical artifact.

Failed question IDs (IDs only; no private text):

```text
question-001, question-002, question-003, question-004, question-005,
question-006, question-007, question-008, question-009, question-010,
question-011, question-012, question-013, question-014, question-015,
question-016, question-017, question-018, question-019, question-020,
question-021, question-022, question-023, question-024, question-025,
question-026, question-027, question-028, question-029, question-030,
question-031, question-032, question-033, question-034, question-035,
question-036, question-037, question-038, question-039, question-040,
question-041, question-042, question-043, question-044, question-045,
question-046, question-047, question-048, question-049, question-050,
question-051, question-052, question-053, question-054, question-055,
question-056, question-057, question-058, question-059, question-060,
question-061, question-062, question-063, question-064, question-065,
question-066, question-067, question-068, question-069, question-070,
question-071, question-072, question-073, question-074, question-075,
question-076, question-077, question-078, question-079, question-080,
question-081, question-082, question-083, question-084, question-085,
question-091, question-092, question-093, question-094, question-095,
question-096, question-097, question-098, question-099, question-100
```

## Cleanup and out-of-scope boundaries

The runner cleanup inventory is `cleaned=true`, `root_exists=false`, `remaining_count=0`,
`remaining_bytes=0`, with 260 files and 119 directories removed from the temporary Acceptance root.
Production DataRoot, Vault, live ports 8766/8767, Artifact, and owner data were not accessed.

Because fact recall, citation accuracy, MCP parity, context baseline, semantic degradation, and
corruption isolation fail or are not measured, the correct threshold conclusion is
`MEASURED_FAIL`, not `READY_FOR_100K`. No 100k/full/release run occurred. A future bounded repair
plan may address only these measured buckets; this task does not change retrieval/ranking/filter,
promotion policy, runtime/UI, vector provider, data model, or fixture truth.

## Repair Round 1 — C1/C2 and I1-I5

The prior artifact `output/validation/task-3-frozen-quality.json` is **INVALID as
post-commit evidence**. It was generated by the earlier command at approximately
2026-08-30 17:05 Asia/Shanghai and is bound to `code_commit=3cb45340de5afe1d8451aed41eece940954c0db3`,
not the repaired product commit. It was retained and not overwritten. No prior
diagnostic or fixture truth was promoted into the repaired artifact.

Fixture truth was re-audited before the repair. The corpus/questions counts remain
145/100, with the same hashes (`2a3ea2c14af9e1705a39673efb50826579f35b484f9d6c5442cb40f5f8f2347a`
and `35000a5cc56de84ef3caa82114a1b9168e46c1d3b31fd89ba0f2a740ce6f9e31`), category counts
20/20/15/10/10/10/5/5/5, modes current 94/history 3/as_of 2/why 1, and max_chars 4000
for every question. No wording, facts, expected/disallowed identities, atoms, mode, budget,
threshold, or difficulty was changed.

### TDD and repaired contracts

The repair RED run was:

```text
python3 -m pytest -q tests/test_task7p_frozen_oracle.py tests/evaluation/test_automatic_memory_end_to_end.py --tb=short
```

It produced exactly `6 failed, 29 passed, 1 warning`. The failures covered the
non-canonical published diagnostic view, missing/forged runtime provenance, non-exclusive
primary buckets, checkpoint budget/semantic tampering, and question-level exception handling.

The product/tests commit is `bf0ab0a4f9b5291ccf96078cbfe33b6b9a979c92`. Before the frozen run,
the focused/direct and Task2 canonical/scale/reset regression set passed:
`121 passed, 1 warning`.

Diagnostics now have one canonical nested stream:
`evidence_details.diagnostic_evidence = {schema_version, question_diagnostics, grouped_metrics}`.
The strict loader rejects unknown fields, unknown frozen question IDs/categories, duplicate rows
or identities, contradictory passed/failure state, multiple primary buckets, and grouped counts
whose primary-bucket sum differs from failed questions. Each failed question has exactly one
primary bucket; secondary causes remain in its `failures` details. Gateway and MCP forbidden
evidence is joined and deduplicated per question.

The atomic checkpoint wrapper schema is version 1 with exactly
`schema_version`, `run_id`, `code_commit`, `fixture_hashes`, `question_id`,
`question_contract_hash`, and `result`. The result has the closed diagnostic schema used by the
canonical stream. Loading revalidates run/fixture/commit identity, the complete frozen question
contract (including same-ID truth), category/mode/as_of and passed identity semantics, and
`used_chars <= question.max_chars <= 12000`; saving uses a temporary file, fsync, and atomic
replace. The formal runner loads a matching checkpoint before invoking Gateway or MCP and stores
one bounded fallback diagnostic for each Gateway/MCP/adapter exception while continuing the loop.
The observation adapter only derives identity from actual runtime section fields and an explicit
runtime binding; caller fact/citation IDs and expected fixture rows cannot fill missing identity.
Opaque fixture hashes are only compared to observed opaque hashes; SHA-256 content hashes are
only compared to SHA-256 hashes.

### Unique post-commit frozen run

Exactly one post-commit CLI was run, after the product/tests commit, with a new output path:

```text
python3 scripts/automatic_memory_quality_gate.py --output output/validation/task-3-repair-postcommit-quality.json
```

It exited 1 with `functional_status=FAIL`, `frozen_questions=100 categories=9`.
Artifact SHA-256 is `6ca53a3640f9492d3036a0c20890c3dfd0f3a493746fb8757892d788870ca108`.
The top-level artifact has no second `question_diagnostics`/`grouped_question_metrics` view;
the canonical loader parsed all 100 nested rows and 9 grouped metrics. Its identity is:

```text
code_commit=bf0ab0a4f9b5291ccf96078cbfe33b6b9a979c92
fixture_hashes.corpus=2a3ea2c14af9e1705a39673efb50826579f35b484f9d6c5442cb40f5f8f2347a
fixture_hashes.questions=35000a5cc56de84ef3caa82114a1b9168e46c1d3b31fd89ba0f2a740ce6f9e31
run_id=quality:2a3ea2c14af9e170:35000a5cc56de84e:bf0ab0a4f9b5291c
```

The real metrics are:

| Metric | Result | Threshold/conclusion |
|---|---:|---|
| questions | 100/100 | required 100, PASS |
| valid facts | 0/106 | >=90%, FAIL |
| citations | 0/106 | >=95%, FAIL |
| formal MCP parity | 0/100 | >=95%, FAIL; 100 `retrieval_empty` observations |
| forbidden false-positive questions | 0/100 | <=5%, PASS |
| primary diagnostic buckets | retrieval 95, mcp 5 | 100 failed = 95 + 5, no duplicate counting |
| context baseline | not measured | required, FAIL |
| semantic degradation | failed | measured failure |
| corruption isolation | failed | measured failure |

The 95 retrieval-primary failed IDs are `question-001` through `question-085` and
`question-091` through `question-100`. The 5 MCP-primary failed IDs are
`question-086` through `question-090`. No question passed; no provenance-primary,
temporal-primary, fallback-primary, context-primary, import-primary, or forbidden-positive
question was observed in this run. The artifact's `readiness_from_envelope` correctly refuses
scale admission for this measured-fail result; canonical functional loading succeeds, and the
threshold conclusion is `MEASURED_FAIL`, not `READY_FOR_100K`.

The production MCP registration was exercised through `src.mcp_server.create_mcp_server` and
its registered `build_context_pack` tool. The isolated runner cleanup inventory records
`cleaned=true`, `root_exists=false`, `remaining_count=0`, `remaining_bytes=0` (260 files and
119 directories removed). The output artifact is intentionally retained as the sole post-commit
evidence; temporary acceptance data/checkpoints were removed.

No 100k/full/release run, live 8766/8767 service, Production/Vault/owner data, retrieval/ranking/
filter/promotion-policy repair, fixture truth change, UI/runtime/vector-provider/data-model change,
or second quality CLI run occurred after this artifact was generated. No product/tests changes were
made after the unique post-commit run.
