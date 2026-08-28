# Task 6Q — Trusted Lifecycle Projection Correctness

## Scope and disposition

Task 6Q is a bounded follow-up to the Task6P final-review I1. It fixes only
callback projection trust boundaries; it does not reopen Task6P's historical
repair cap, change queue/database/UI behavior, or claim Task6 acceptance.
`LOCAL_EXECUTION_TASK.md` remained `IDLE`; no live 8766/8767 service, Artifact,
release, Production/Vault data, or owner data was used.

```text
Product/tests commit: de412d52df3478c9cfa09b11572cb3841095d897
Task6P historical disposition: FAIL / BLOCKED_AT_REPAIR_CAP (preserved)
Task6: IN_PROGRESS / NOT_ACCEPTED
```

## Root cause

`ExtractionPipeline._notify_lifecycle()` collected every string below an
explicit lease-key alias in job/result/error payloads, then used those values
as global substring replacement material. A payload value such as
`lease_token: "a"` therefore changed unrelated callback正文 and the collector
was not bounded by material format, count, or size.

## Implementation

- Removed `_lease_material_from_explicit_keys()` and all pipeline references.
- Kept one lifecycle projection boundary, now accepting explicitly supplied
  `trusted_known_materials` only.
- Internal queue-claim success/failure paths pass only a validated queue
  `uuid4().hex` 32hex lease and its matching 64hex SHA-256 fingerprint, with a
  maximum of two materials and strict format/relationship validation.
- Direct `execute()` has no claim and passes the default empty trusted list;
  explicit allowlisted lease keys are still recursively removed, while their
  values never become replacement material.
- Existing cycle, depth, node, string-size, unknown-object fail-closed, terminal
  state, worker ownership, persistence, Control/MCP, and structured boundaries
  remain unchanged.

## TDD evidence

The new RED tests were run against the pre-fix tree after adding the tests and
before changing production code:

```text
tests/test_task6p_queue_persistence_redaction.py — 5 failed, 9 passed
```

The failures reproduced short `a`, ordinary-word, long, and valid-shape-but-
untrusted direct payload values being globally replaced, plus the missing
trusted projection API. After the fix:

```text
tests/test_task6p_queue_persistence_redaction.py — 14 passed
```

Coverage includes nested mapping/list/tuple values, malicious short/long/32hex
payload values, trusted internal token/fingerprint replacement, direct execute
with an empty trusted list, ordinary text preservation, automatic success, and
normal/automatic failure callback paths.

## Verification

Fresh backend matrix:

```text
214 passed, 6 warnings
```

The matrix included Task6P/L/M, extraction pipeline/queue/worker, automatic
memory runtime/scheduler/watcher/control, packaged Control, MCP, Capture,
Task8 Work Fact, Work API/store, and structured evidence tests. Desktop
`test:memory-sources-repair`, `test:memory-sources`, and TypeScript/Vite
`build` passed. The rendered `test:e2e:memory` command was attempted but
timed out at its existing `page.goto(..., waitUntil: "networkidle")` step;
no UI code was changed by Task6Q and this report does not claim rendered PASS.
`compileall` and `git diff --check` passed before the documentation commit.

Full/release validation, live services, Artifact, Production/Vault, and owner
acceptance remain unexecuted. Task6V remains deferred and Task6 remains
`IN_PROGRESS / NOT_ACCEPTED`.

## Files

- `src/extraction/pipeline.py`
- `src/extraction/queue.py`
- `tests/test_task6p_queue_persistence_redaction.py`
- synchronized `docs/PROJECT_STATUS.md`, `docs/MODULES/CODE_MAP.md`,
  `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`, and the existing product plan

## Disposition

```text
Task6Q code/tests: IMPLEMENTED_FOCUSED_PASS
Task6P: FAIL / BLOCKED_AT_REPAIR_CAP (historical, unchanged)
Task6: IN_PROGRESS / NOT_ACCEPTED
Rendered Desktop check: BLOCKED by existing networkidle timeout
Live/Artifact/owner acceptance: NOT_TESTED
```
