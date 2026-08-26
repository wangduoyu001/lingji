# Task 4 / 4R1 report

## Status

`DONE`: Task 4R1 round-5 final findings are closed in product commit
`5be8d92997a3945dd7d83732a0350cac340c5320`.  This is a measurement and
provenance repair, not a retrieval-quality pass.  The rejected initial draft
remains explicitly marked `TDD_ORDER_NOT_MET` because it was not RED-first.
No open Task 4R1 finding remains.  The fixed 100-question run still measures
product `FAIL` (fact recall `0.0%`, citation accuracy `0.0%`, duplicate
records `5`); 4R2 evidence is `NOT_MEASURED`, so functional and full
acceptance gates were not called and the envelope remains
`functional_status=NOT_EVALUATED`, `phase_status=NOT_EVALUATED`.

## Round-5 RED/GREEN evidence

RED was authored and run on base `338641a` before the final repair:

```text
Command: ./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_round5_final_red.py
Result: 6 failed, 1 warning in 4.68s
```

The six failures were the six final findings: invalid Gateway identity was
silently skipped; import audit lacked duplicate-hash/order truthfulness;
sentinel unavailability became numeric zero; active promotion omitted current
evidence; 4R2 fields were not quarantined in the envelope; and the review
record still lacked round-5 status.

GREEN after the product repair (the review-record assertion is included after
the docs commit) is:

```text
Command: ./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/evaluation/test_automatic_memory_gate_integrity.py tests/evaluation/test_automatic_memory_end_to_end.py tests/test_auto_memory_promotion.py
Result: 63 passed, 1 warning
```

The focused regression command also includes `git diff --check` and is kept as
the required round-5 verification scope.  The preceding takeover evidence is
preserved exactly: base `f9bf190`, code commit `8743356`, RED `7 targeted
defects failed, 2 baseline safety checks passed`, and GREEN `9 passed` in
`test_task4r1_takeover_red.py`; the earlier product/docs commits are
`8743356` and `cf4f220`.

## Gateway-vs-selector root cause

One frozen run was instrumented at both boundaries without changing fixtures,
queries, retrieval code, or scoring:

```text
Gateway boundary: gateway_calls=200, gateway_empty=200, gateway_items=0
Selector boundary: selector_calls=100, selector_selected=0
```

The 200 Gateway calls are 100 direct calls plus 100 MCP parity calls.  Every
direct response had a well-formed empty `sections` list, so this was a genuine
Gateway retrieval miss (Gateway vacuum), not a selector dropping eligible
sections.  The repaired selector records an empty response as a miss, while
readiness is `READY` only after all 100 direct calls and selector executions
complete with valid identities.  Unknown, missing, malformed, duplicate, or
extra evidence fails closed.  The frozen query text is passed verbatim and
selection is built from the pre-query adapter/read-model identity map; expected
or forbidden IDs are never consulted.

## Import and promotion evidence

`ImportedEvidenceAudit` now compares adapter-produced external source,
conversation, message, sequence, role, content hash, and persisted row order
without sorting away order defects.  It counts missing/extra rows and both
duplicate external IDs and duplicate content hashes.  The frozen run observed
`actual=145`, `expected=145`, `missing=0`, `extra=0`,
`duplicate_external_ids=0`, `duplicate_content_hashes=5`, and
`ordered_external_id_matches=0`; import readiness is therefore false.

Promotion evidence is reset per call and attached only after projection and
all message links finish.  Only resolved SourceReadModel message primary IDs
are linked.  Generic unique source/conversation/message/evidence references
resolve fail-closed; ambiguous/unresolved/read-model errors produce an error
outcome, and a later link failure unlinks earlier links and removes the
rebuildable projection.

## Sentinel and 4R2 boundaries

The configured `vault` root is absent in this test environment.  Sentinel
capture records `missing protected root: vault`; it does not report a numeric
pollution value.  Production pollution `null`.  The machine envelope and returned report use
`production_pollution=null`, `production_vault_sentinels.available=false`,
and `unchanged=null`.  A numeric pollution count is emitted only when both
before and after protected-tree snapshots are valid.  Sentinel unavailability
keeps evidence incomplete and no acceptance gate is called.

MCP parity, semantic degradation/Qdrant, corruption isolation, measured
context baseline, scale, owner review, reboot, and Mac evidence are
`NOT_MEASURED`/reserved for 4R2 or later acceptance.  Their readiness fields
remain false and no hard-coded success value can affect a gate.

## Frozen inputs and scope

- Corpus SHA-256: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`
- Questions SHA-256: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`
- Product commit: `5be8d92997a3945dd7d83732a0350cac340c5320`
- Report commit: recorded by Git as the docs commit containing this report
- No frozen fixture, evaluator/scorer/threshold, Task 3 retrieval,
  Artifact/Production/Vault, or 4R2 implementation was changed or used.
- `LOCAL_EXECUTION_TASK.md` remained `IDLE`; no local installation or owner
  acceptance was performed.

## Blocking findings

None for Task 4R1.  The measured product quality failure and unmeasured 4R2
fields remain explicit downstream acceptance work; they are not relabeled as
Task 4R1 measurement success.
