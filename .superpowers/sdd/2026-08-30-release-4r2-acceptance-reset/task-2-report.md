# Release 4R2 reset · Task 2 strict canonical measurement contract

## 1. Executive verdict

```text
Task verdict: DONE_WITH_CONCERNS
Quality-gate verdict: FAIL (honest; no pass is inferred)
Product commit: 4ce408b (fix: close the 4r2 measurement contract)
Quality artifact: output/validation/task-2-quality.json
Artifact run ID: quality:bc1812fe64444027:338f5051c43902af:23a516fdfd1d28c7
Artifact canonical code_commit: 23a516fdfd1d28c73a819bfcf10e25ed47878672
```

The implementation closes the C1/I1/I2/I3 evidence blind spots with one immutable,
schema-closed canonical view and fail-closed promotion/activation validation. The
quality CLI result remains `FAIL`, which is valid for this task because the measured
evidence is published honestly and no readiness is promoted from missing evidence.

Concern: the only permitted quality CLI invocation happened before the product commit
and before the final publisher identity fix. Its nested `evidence_details.code_commit`
is the baseline, while the published top-level `code_commit` is `null`. The publisher
fix is covered by GREEN tests and is in `4ce408b`, but the CLI was not rerun because the
brief permits exactly one invocation. This report does not present that artifact as a
final-SHA artifact.

## 2. Scope and boundaries

Baseline: `23a516fdfd1d28c73a819bfcf10e25ed47878672`.

Changed product/test files are limited to:

- `src/automatic_memory/quality_evidence.py`
- `src/automatic_memory/quality_gate.py` (canonical publisher seam only)
- `src/automatic_memory/quality_promotion.py`
- `tests/test_task7o_contract_closure.py`
- `tests/test_task7o_contract_adversarial.py`

Changed authority docs are limited to `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` and
`docs/MODULES/CODE_MAP.md`. No retrieval, ranking, query, filter, promotion policy,
fixture, question, answer, threshold, UI, runtime, vector provider, schema, second
system, Production/Vault, live 8766/8767, Artifact, 100k, full or release work was run
or modified. Automatic activation quarantine is unchanged; low-risk items are never
automatically approved by this task.

## 3. TDD evidence

The required `.venv` did not exist. System Python was `3.12.10`; therefore the equivalent
command was used.

### RED

Command:

```bash
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py --tb=short
```

Recorded result before production edits: `6 failed, 31 passed, 1 warning`.

The six failures reproduced the old blind spots:

| Contract | Adversarial case that failed RED | Mapping |
|---|---|---|
| C1 | Unknown nested key in `import_audit.stable_duplicates` was accepted | Recursive canonical loader was not schema-closed |
| I3 | Protected item reported persisted `active` | Actual persisted status was not checked |
| I3 | Wrong category | Actual category was not checked |
| I3 | Empty reason evidence | Required reason evidence was not checked |
| I3 | `actual_status=active` alias | Actual-status compatibility field was not checked |
| I3 | `status=error` disguised as pending | Contradictory status evidence was not checked |

The C1 direct unknown-field, bool, non-finite, identity/hash and contradiction cases,
and the I1/I2 identity/link cases, were also added in the same adversarial suite; their
pre-existing validators already rejected the covered baseline cases, so they were
recorded as passing RED-suite guards rather than fabricated failures.

### GREEN

After the minimum implementation and publication identity test:

```text
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py --tb=short
41 passed, 1 warning
```

The runner now parses one canonical view, recursively rejects unknown/bool/non-finite/
empty evidence, and compares (rather than trusts) compatibility projections. Promotion
collection scans every imported message relationship before candidate filtering and
rejects empty, duplicate, missing, extra, pending/rejected/error, and orphan identity
evidence. Activation requires actual persisted status, category, and non-empty reason
codes while returning quarantine as `not_applicable` rather than zero-of-N.

## 4. Contract coverage

| ID | Required adversarial coverage | GREEN evidence |
|---|---|---|
| C1 | Unknown top-level/nested fields; duplicate/contradictory views; bool; NaN/Infinity; missing run/commit/hash; exact round-trip | `test_task7o_contract_adversarial.py::test_canonical_loader_rejects_hostile_mutations`, `test_runner_envelope_rejects_contradictory_views`, `test_runner_envelope_rejects_unknown_top_level_field`, `test_canonical_loader_accepts_only_exact_round_trip` |
| I1 | All imported links scanned before filtering; orphan external link fails | `test_measurement_scans_orphan_links_outside_candidate_filter` |
| I2 | Empty/whitespace identity; duplicate outcome/projection/audit/link; missing/extra audit; pending/rejected/error link | `test_promotion_identity_and_links_fail_closed`, `test_promotion_unique_active_link_and_protected_pending_pass` |
| I3 | All five frozen categories; actual status/category/reason; protected active, wrong category, missing reason, actual alias, error-as-pending fail | `test_activation_measurement_uses_actual_status_category_and_reason`, `test_activation_measurement_rejects_false_or_incomplete_truth` |

## 5. Direct Task 2 matrix and static checks

Exact brief matrix:

```bash
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py tests/test_task7n1_scale_admission.py tests/test_task7n2_corruption_retrieval.py tests/test_task7n3_promotion_thin.py tests/test_task7_measurement_repair.py tests/test_task7_quality_scale.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_automatic_memory_end_to_end.py --tb=short
```

Recorded result: `189 passed, 1 warning in 57.13s` (system Python 3.12.10).

Static/handoff command:

```bash
python3 -m compileall -q src tests && git diff --check && python3 scripts/check_acceptance_sync.py && python3 scripts/check_local_execution_handoff.py
```

Recorded result: compileall PASS; diff-check PASS; acceptance sync PASS (`changed files:
6`, `product-impacting files: 2`); local execution handoff PASS.

## 6. The single quality CLI run

Command, run once only:

```bash
python3 scripts/automatic_memory_quality_gate.py --output output/validation/task-2-quality.json
```

The script created and cleaned isolated Acceptance roots. It used the unchanged frozen
fixtures; no owner data, Production/Vault, live service, release, Artifact or 100k run
was used.

```text
Exit: 1
functional_status: FAIL
phase_status: FAIL
run_id: quality:bc1812fe64444027:338f5051c43902af:23a516fdfd1d28c7
corpus fixture SHA256: bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
questions fixture SHA256: 338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

Readiness from the published artifact:

```text
context_baseline=NOT_MEASURED
corruption_isolation=FAILED
gateway_selection=READY
import_audit=READY
mac_release=NOT_MEASURED
mcp_parity=FAILED
owner_review=NOT_MEASURED
production_sentinel=NOT_MEASURED
promotion_provenance=READY
qdrant_degradation=FAILED
reboot_recovery=NOT_MEASURED
scale=NOT_MEASURED
windows_release=NOT_MEASURED
```

Measured status is explicit: `answered_questions=100`, `valid_fact_hits=0/106`,
`citation_hits=0/106`, `mcp_successes=0/100`; baseline/rendered/reduction and activation
accuracy are `null` because they were not measured. Promotion provenance is
`READY`, with `expected=145`, `actual=145`, `active=0`, `pending=145`,
`rejected=0`, `error=0`, and all duplicate/missing/extra counters zero. This does not
approve any memory and does not convert quarantine into activation readiness.

Cleanup inventory from the same artifact:

```text
cleaned=true, root_exists=false, bytes=4445599, directory_count=118,
file_count=160, other_count=0, symlink_count=0, remaining_count=0,
remaining_bytes=0, error=None
```

## 7. Commit and workspace handoff

Product/tests are separate from docs/evidence:

```text
Product/tests commit: 4ce408b
Docs/evidence commit: PENDING (this report is force-added because .superpowers/ is ignored)
```

The final docs commit SHA and clean status are filled in by the docs-only commit that
adds this report. No unrelated tracked changes are included. Ignored interpreter caches,
pytest cache and the retained quality artifact are not product changes.

## 8. Final known concern

`CONCERN-1`: The single CLI artifact predates product commit `4ce408b`; its nested
canonical details identify baseline `23a516f...`, and its top-level publisher projection
has `code_commit=null`. The missing top-level identity is now fixed and directly tested,
but the brief's one-run rule prevents re-running this CLI in this task. Therefore the
implementation is ready for review, while this exact artifact must not be represented as
evidence generated from `4ce408b` without an explicitly authorized new acceptance run.

## 9. Sign-off

```text
Codex executor: Task 2 implementation agent
Owner confirmation: pending
Acceptance date: 2026-08-30
Report branch: codex/owner-real-history-memory-cards
Report commit: pending docs-only commit
```
