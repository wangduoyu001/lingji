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

Recorded result (rerun after final publication-identity GREEN): `190 passed, 1 warning
in 57.20s` (system Python 3.12.10).

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
Docs/evidence commit: 1df49dd (initial docs/report commit)
Report identity update commit: 848f72c (docs-only metadata update)
```

The report identity update is a docs-only follow-up because the report must record the
already-created docs commit without claiming a hash before Git creates it. No unrelated
tracked changes are included. Ignored interpreter caches, pytest cache and the retained
quality artifact are not product changes.

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
Report commit: 1df49dd (initial report; metadata update 848f72c)
```

## 10. Repair Round 1 (independent review closure)

The independent review `task-2-review.md` identified C1/I1/I2/I3 contract gaps. M1
remains deferred. This repair changed only the canonical quality contract, measurement
runner/loader, focused adversarial/closure tests, and this evidence record. It did not
change retrieval, ranking, query/filter behavior, promotion policy, fixtures, UI/runtime,
vector provider, schema, or activation quarantine. Low-risk outcomes remain
`pending_owner_review`; no automatic approval was added.

### 10.1 TDD RED and GREEN

The first adversarial RED was run before the production repair:

```text
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py --tb=short
15 failed, 45 passed, 1 warning in 4.97s
```

The 15 failures were evidence for every required repair contract: C1 (3 blank/duplicate
intentional-hash-group cases and 4 run/fixture-hash/commit consistency cases), I1
(orphan projection and malformed active-link relationship identity), I2 (missing service
candidate identity), I3 (wrong-but-self-consistent category, arbitrary reason,
StateDB/service status disagreement, StateDB/service category disagreement), and the
missing per-outcome truth artifact.

After the minimal repair, the focused GREEN was:

```text
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py --tb=short
60 passed, 1 warning in 4.78s
```

The brief's direct matrix was then run before the final product commit:

```text
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py tests/test_task7n1_scale_admission.py tests/test_task7n2_corruption_retrieval.py tests/test_task7n3_promotion_thin.py tests/test_task7_measurement_repair.py tests/test_task7_quality_scale.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_automatic_memory_end_to_end.py --tb=short
210 passed, 1 warning in 60.37s
```

The repair now has one canonical view: recursive unknown fields, booleans/non-finite
values, blank or duplicate identities, duplicate projections under strict type equality
(`True` is not `1`), and contradictory/empty/orphan evidence fail closed. All projection
rows and all imported relationship rows enter validation, including empty/malformed
identities. Missing `promotion_memory_id` and service `candidate_id` remain failures;
neither can be synthesized from content hashes. Actual persisted StateDB status/category/
reason is read and cross-checked against the service return and allowed category/reason
contract. The artifact publishes 145 strict per-outcome truth records as well as
aggregate counts.

Static checks before committing the product/tests were:

```text
python3 -m compileall -q src tests && git diff --check
PASS
```

### 10.2 Final product commit and artifact disposition

Product/tests were committed separately before the authorized quality run:

```text
Product/tests commit: 272fbeb1252cfedf59906eb189de475f481c0eec
```

The prior `output/validation/task-2-quality.json` is retained as
`INVALID_HISTORICAL_ARTIFACT`: its top-level `code_commit` is null and its nested
identity/run ID points to baseline `23a516fdfd1d28c73a819bfcf10e25ed47878672`. It was
not overwritten and must not be used as evidence for the repair commit.

### 10.3 The single authorized post-fix quality run

With all focused GREEN/direct-matrix checks complete and the final product SHA fixed,
the newly authorized isolated run was executed exactly once. The old artifact above was
not rerun or replaced.

```text
python3 scripts/automatic_memory_quality_gate.py --output output/validation/task-2-quality-repair1.json
Exit: 1
functional_status: FAIL
phase_status: FAIL
```

The honest failure was the isolated snapshot's existing generic-history adapter parse
failure (`No approved extraction adapter for source type: generic_ai_history`; malformed
JSON was reported at line 1 column 3). The new artifact is structurally canonical and
identity-consistent:

```text
run_id: quality:bc1812fe64444027:338f5051c43902af:272fbeb1252cfedf
top-level code_commit: 272fbeb1252cfedf59906eb189de475f481c0eec
evidence_details.code_commit: 272fbeb1252cfedf59906eb189de475f481c0eec
corpus fixture SHA256: bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
questions fixture SHA256: 338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
artifact: output/validation/task-2-quality-repair1.json
```

The canonical loader accepted the artifact and its 145 per-outcome truth records.
`readiness_from_envelope` and `load_quality_readiness` then correctly returned
`BLOCKED_4R2_REQUIRED` for scale admission because the measured functional status is
FAIL; this is the formal fail-closed readiness result, not an artifact identity or
schema parse failure. Readiness from the artifact is:

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

Measured quality is explicit: `answered_questions=100`, `valid_fact_hits=0/106`,
`citation_hits=0/106`, and `mcp_successes=0/100`; baseline/rendered/reduction and
activation accuracy are null because they were not measured. Promotion provenance is
`READY`, with `expected=145`, `actual=145`, `active=0`, `pending=145`, `rejected=0`,
`error=0`, all duplicate/missing/extra counters zero, and `outcomes=145`. This does
not approve any memory or alter quarantine.

Cleanup from this same isolated run was complete:

```text
cleaned=true, root_exists=false, bytes=4599425, directory_count=118,
file_count=160, other_count=0, symlink_count=0, remaining_count=0,
remaining_bytes=0, error=None
```

### 10.4 Repair handoff and boundaries

After the quality run, only this report and acceptance evidence are changed. The final
docs/evidence commit is the docs-only commit containing this section. Product/tests and
docs/evidence therefore remain separate commits; the final clean-tree SHA is recorded in
the handoff below.

Not run in this repair: 100k/full/release/Artifact, live ports 8766/8767, Production or
Vault, owner data/real chats, Desktop/UI, retrieval/ranking/query/filter changes, or any
promotion-policy change. No second quality CLI run was made.

```text
Repair verdict: DONE
Product/tests commit: 272fbeb1252cfedf59906eb189de475f481c0eec
Docs/evidence commit: this docs-only commit (exact SHA in final handoff)
Report branch: codex/owner-real-history-memory-cards
Acceptance date: 2026-08-30
```

## 11. Repair Round 2 (final bounded canonical-only closure)

The scoped review `task-2-repair-1-review.md` left original C1/I3 and introduced C2,
I5, I6, and I7. I1/I2/I4 were not rewritten. M1 remains deferred. This round changed
only the canonical evidence contract and formal scale loader plus the three permitted
test files. Retrieval, ranking, query/filter, fixtures, UI/runtime/vector/schema, and
promotion policy were not changed; automatic activation remains quarantined.

### 11.1 TDD RED and GREEN

New adversarial tests were written first and run before the production changes:

```text
python3 -m pytest -q tests/test_task7o_contract_adversarial.py tests/test_task7o_contract_closure.py tests/test_task7n1_scale_admission.py --tb=short
11 failed, 71 passed, 1 warning in 7.10s
```

The RED failures covered C1/I6 (schema-version and stable-duplicate measured integer
types), I3/I7 (forged non-pending status, arbitrary reason, duplicate decision identity),
C2 (legacy compact envelope), and I5 (full canonical provenance rejected by the old
scale schema). The test mutations were real canonical/loader inputs; no skip or lowered
assertion was used.

Minimal GREEN for the same three files:

```text
python3 -m pytest -q tests/test_task7o_contract_adversarial.py tests/test_task7o_contract_closure.py tests/test_task7n1_scale_admission.py --tb=short
82 passed, 1 warning in 6.82s
```

The brief direct matrix was green before the final product commit:

```text
python3 -m pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py tests/test_task7n1_scale_admission.py tests/test_task7n2_corruption_retrieval.py tests/test_task7n3_promotion_thin.py tests/test_task7_measurement_repair.py tests/test_task7_quality_scale.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_automatic_memory_end_to_end.py --tb=short
228 passed, 1 warning in 58.02s
```

The canonical loader now requires `schema_version` to be the exact integer `1`, and
every measured integer/counter (including all `stable_duplicates`) is a non-negative
integer, never bool/float/non-finite. The legacy compact scale path is removed: formal
admission requires `evidence_details` and complete per-outcome promotion truth. The
scale promotion validator requires exactly the same full provenance fields as the
canonical schema, including `active`, `pending`, `rejected`, `error`, and `outcomes`.
Canonical per-outcome records require unique non-empty memory and decision identities,
the allowed category set, all expected/service/durable statuses equal to
`pending_owner_review`, and reason codes from the production measurement allowlist with
the existing durable redaction-set relation. No low-risk record can become auto-approved.

Static checks before product commit:

```text
python3 -m compileall -q src tests && git diff --check
PASS
```

### 11.2 Final product and previous artifact disposition

Product/tests were committed before the authorized Round2 quality run:

```text
Product/tests commit: 8ccc3d44b1f921dec9b1b0a93fc71afdfd7dad99
```

The retained artifacts are explicitly not interchangeable:

```text
output/validation/task-2-quality.json
  INVALID_HISTORICAL_ARTIFACT (top-level code_commit=null; baseline identity)
output/validation/task-2-quality-repair1.json
  PREVIOUS_REPAIR_ARTIFACT (canonical for product commit 272fbeb1252cfedf... only)
output/validation/task-2-quality-repair2.json
  CURRENT_ROUND2_ARTIFACT (canonical for product commit 8ccc3d44...)
```

No historical artifact was overwritten.

### 11.3 The single authorized Round2 quality run

After all RED/GREEN/direct-matrix checks and final product commit, the root agent's
one-run authorization was used exactly once:

```text
python3 scripts/automatic_memory_quality_gate.py --output output/validation/task-2-quality-repair2.json
Exit: 1
functional_status: FAIL
phase_status: FAIL
```

The isolated frozen run reported the existing generic-history adapter parse failure:
`No approved extraction adapter for source type: generic_ai_history`; the adapter also
reported malformed JSON at line 1 column 3. This is an honest measured FAIL, not a
canonical identity failure. The new artifact identity is:

```text
artifact: output/validation/task-2-quality-repair2.json
run_id: quality:bc1812fe64444027:338f5051c43902af:8ccc3d44b1f921de
top-level code_commit: 8ccc3d44b1f921dec9b1b0a93fc71afdfd7dad99
evidence_details.code_commit: 8ccc3d44b1f921dec9b1b0a93fc71afdfd7dad99
corpus fixture SHA256: bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
questions fixture SHA256: 338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

`CanonicalFunctionalEvidence.from_runner_payload()` accepted the artifact and all 145
per-outcome truth records. `readiness_from_envelope()` and `load_quality_readiness()`
then returned `BLOCKED_4R2_REQUIRED` because measured functional status is FAIL; this
is the expected formal scale fail-closed result after canonical parsing. Readiness is:

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

Measured quality is explicit: `answered_questions=100`, `valid_fact_hits=0/106`,
`citation_hits=0/106`, and `mcp_successes=0/100`; baseline/rendered/reduction and
activation accuracy are null because they were not measured. Promotion provenance is
`READY`, with `expected=145`, `actual=145`, `active=0`, `pending=145`, `rejected=0`,
`error=0`, all duplicate/missing/extra counters zero, and `outcomes=145`. This leaves
all records pending owner review and does not alter activation quarantine.

The same isolated run cleaned its Acceptance roots completely:

```text
cleaned=true, root_exists=false, bytes=4591233, directory_count=118,
file_count=160, other_count=0, symlink_count=0, remaining_count=0,
remaining_bytes=0, error=None
```

### 11.4 Final handoff and unrun boundaries

After the quality run, only this report and acceptance evidence are changed. Product/
tests and docs/evidence are separate commits. No second Round2 quality CLI was run.

Not run: 100k/full/release/Artifact, live 8766/8767, Production/Vault, owner data or
real chats, Desktop/UI, retrieval/ranking/query/filter changes, or promotion-policy
changes. No low-risk auto-approval was introduced.

```text
Repair Round 2 verdict: DONE
Product/tests commit: 8ccc3d44b1f921dec9b1b0a93fc71afdfd7dad99
Docs/evidence commit: this docs-only commit (exact SHA in final handoff)
Report branch: codex/owner-real-history-memory-cards
Acceptance date: 2026-08-30
```
