# Task 6P Repair Round 1 — Final Independent Review

- Review date: 2026-08-28 (Asia/Shanghai)
- Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
- Reviewed tree: `33f6ffa407badda2531228a651aea6762dd4cfac`
- Repair product/tests: `924ac0c433a5d1029cce456cec1e6f24ef7dc7ba`
- Repair base: `d61acdf39eefca8870b46b7a3172fe8ce20d5d6f`
- Prior review: `task-6p-review.md` (`d61acdf`)
- Scope: independent read-only product review; this report and synchronized
  documentation are the only deliverables. Product files were not modified.

## Verdict

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Task 6P: FAIL / BLOCKED_AT_REPAIR_CAP
Task 6: IN_PROGRESS / NOT_ACCEPTED
Critical: 0
Important: 1 (I1)
Minor: 0
Disposition: NOT ACCEPTED
```

The repair closes the previously observed plaintext claimed-job leak for the
normal generated lease values and routes ordinary, automatic, and direct
execute callbacks through one projection boundary. It does not satisfy the
required ordinary-text and bounded-projection contract for attacker-controlled
explicit lease-key values, so the final review cannot accept Task6P.

## Fresh verification

All commands used the reviewed worktree and temporary pytest roots only. No
live 8766/8767 service, Artifact, release, Production/Vault data, or owner data
was used.

```text
tests/test_task6p_queue_persistence_redaction.py: 10 passed
Affected backend matrix (266 collected): 266 passed, 7 warnings
Full pytest, without deselection: 1359 passed, 11 skipped, 7 failed, 7 warnings
Desktop test:memory-sources-repair: PASS
Desktop test:memory-sources: PASS
Desktop npm run build (tsc/vite): PASS
Desktop test:e2e:memory (rendered): PASS
compileall src tests: PASS
git diff --check d61acdf..924ac0c: PASS
scripts/check_acceptance_sync.py: PASS
scripts/check_local_execution_handoff.py: PASS
```

The two pre-existing `tests/test_structured_evidence_lexical.py` failures were
run as part of the complete, non-deselected suite and independently reproduced
on both the repair tree and base `d61acdf`: `test_formal_mcp_search_entry_returns_structured_message_citation` and
`test_state_db_revoke_and_expiry_are_excluded_from_current_gateway_context_and_mcp`.
Both fail at `src/mcp_server.py:130` because a test-mutated
`SimpleNamespace` lacks `vault_path`. The other full-suite failures are
unrelated pre-existing packaged/runtime, frontend-dist, legacy UI contract,
promotion, and second-brain environment failures; none is attributed to this
repair. The two `vault_path` failures were not deselected from the full result.

## Requirement matrix

| Requirement | Result | Evidence |
|---|---|---|
| One callback projection boundary for ordinary/automatic/direct success/failure | PASS | `ExtractionPipeline._notify_lifecycle()` source review and 10 focused tests |
| Job/result/error projections omit generated lease token/fingerprint and nested explicit keys | PASS | Focused callback tests and affected backend matrix |
| Nested mapping/list/tuple, cycle/depth/node/string limits fail closed | PASS | Focused scrubber tests and source review |
| Custom objects fail closed without `repr()` and callback failures do not undo terminal state | PASS | Focused custom-object test and live callback-exception probe (`status=completed`) |
| Ordinary `token` text remains unchanged | **FAIL — I1** | See blocking finding below; only holds when it is not also supplied as an explicit lease-key value |
| Explicit lease-key values are collected only within a reasonable bounded/material boundary | **FAIL — I1** | Collector accepts arbitrary unbounded strings and count; see below |
| Queue/private worker ownership, persistence, Control/MCP/process/log paths remain intact | PASS | Affected backend matrix, source/diff review, no schema/API changes |
| Desktop static/build/rendered checks | PASS | All four Desktop commands above |
| No unrelated product scope or second fact source | PASS | Product diff is limited to `pipeline.py`, `queue.py`, and the focused test |

## Blocking finding

### I1 — Arbitrary explicit lease-key values over-redact callback正文 and are not bounded

`_lease_material_from_explicit_keys()` in `src/extraction/queue.py` collects
every string found below an explicit lease-key alias. It validates neither a
lease-token/fingerprint shape nor a minimum length, and it does not cap the
number or total size of collected values. `_notify_lifecycle()` then merges
these attacker-controlled strings into `known_material` and performs global
substring replacement over the job, result, and error projections.

An independent probe on the reviewed tree produced:

```text
_lease_material_from_explicit_keys({"lease_token": "a"}) -> ("a",)
_without_lease_material(
    {"lease_token": "a", "message": "a cat and a ordinary token"},
    redact_values=("a",), fail_closed_unknown=True
) -> {"message": "[REDACTED] c[REDACTED]t [REDACTED]nd [REDACTED] ordin[REDACTED]ry token"}
```

The same occurs with a normal word supplied as the explicit value, for
example `lease_token: "token"`, and with arbitrary values such as
`not-a-real-token`. Thus an attacker-controlled payload can erase unrelated
ordinary chat text from callback projections, violating the requirement that
ordinary token text be preserved and that collection/redaction stay within a
reasonable material boundary. The collector's traversal node limit does not
bound the size or number of strings added to `found`, so this is also an
avoidable callback CPU/memory amplification surface. The issue affects the
single callback boundary across ordinary, automatic, and direct-execute paths.

This is an Important contract/security finding, not a cosmetic difference:
generated lease material is no longer exposed, but callback consumers can
receive materially corrupted projections and an unbounded attacker-controlled
scrub workload. One Repair Round 1 was already authorized and consumed;
therefore this final review is `BLOCKED_AT_REPAIR_CAP` with no further product
repair authorized under Task6P.

## Preserved boundaries

- The private claimed-job seam remains local to worker ownership operations.
- Queue terminal writes, retry/failure handling, and durable ownership receipt
  behavior remain unchanged and passed the affected backend matrix.
- Callback projection is observational: a callback that raises is logged with a
  stable message and does not roll back a committed terminal queue state.
- Task6L and Task6M historical `FAIL / BLOCKED_AT_REPAIR_CAP` dispositions are
  unchanged. Task6 remains `IN_PROGRESS / NOT_ACCEPTED`; packaged 30/70,
  live, Artifact, release, Production/Vault, and owner acceptance remain
  unexecuted and unclaimed.

## Final disposition

```text
Reviewed tree: 33f6ffa407badda2531228a651aea6762dd4cfac
Repair product/tests: 924ac0c433a5d1029cce456cec1e6f24ef7dc7ba
Verdict: FAIL / BLOCKED_AT_REPAIR_CAP
Critical: 0
Important: 1 (I1 arbitrary explicit lease-key over-redaction/unbounded collection)
Minor: 0
Task6P: NOT_ACCEPTED
Task6: IN_PROGRESS / NOT_ACCEPTED
```
