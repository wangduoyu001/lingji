# Task 1 — Invocation-scoped release evidence

## Status

```text
Status: DONE_WITH_CONCERNS
Base commit: 07382e053882ad63942fa6cb45bae090dbaf1373
Product/tests commit: 97684938562a1561972fc6a11ef5368d9b64a57e
Docs/evidence commit: PENDING (this report is included in that separate commit)
```

The invocation-isolation implementation is complete and tested. The only concern is
that this worktree does not contain `./.venv/bin/pytest`; the required command therefore
cannot be launched literally. The same command was run with the existing system
Python 3.12.10 and produced the results below. No tool was installed or downloaded.

## Scope and safety audit

Changed only the validation launcher/script, their focused tests, and the required
acceptance documentation. The implementation does not modify quality measurement,
retrieval, runtime, Desktop, Artifact, Vault, Production, or owner data. The local
execution task remains the historical `IDLE` task; no local acceptance task was
activated.

## TDD RED

Required command:

```text
./.venv/bin/pytest -q tests/test_validation_invocation_isolation.py tests/test_00_task4_reset_validation_guard.py --tb=short
```

Result: could not start; shell exit `127` because `./.venv/bin/pytest` is absent.

Equivalent command using the pre-existing system interpreter:

```text
python3 -m pytest -q tests/test_validation_invocation_isolation.py tests/test_00_task4_reset_validation_guard.py --tb=short
```

First RED result: `3 failed, 6 passed`.

Exact failing tests and expected baseline cause:

```text
tests/test_validation_invocation_isolation.py::test_same_second_nested_invocations_keep_each_owned_evidence_and_parent_final_write
  temporary validation root stayed empty because the old script always wrote to repository output/validation
tests/test_validation_invocation_isolation.py::test_different_second_nested_invocations_keep_authoritative_per_run_summaries
  same root-selection failure; the old second-resolution output contract did not create an independent run
tests/test_validation_invocation_isolation.py::test_stale_cleanup_only_removes_old_completed_runs_inside_validation_root
  old-completed sibling remained because the old script had no bounded owner-aware cleanup
```

This was a behavior failure against the real PowerShell entry, not a mock or source
text-only assertion.

## Implementation

- Every invocation creates a GUID-backed invocation ID. The human-readable timestamp
  is only a prefix and cannot determine identity.
- Each run owns an independent directory containing `.owner.json`, `logs/`, and the
  authoritative `summary.json`/`summary.md`. The owner marker is bounded to 4 KiB and
  records invocation ID, process identity, start time, terminal state, and end time.
- `latest-summary.json`/`latest-summary.md` remain convenience pointers; child runs may
  update those pointers but cannot remove or overwrite a live parent run directory.
- Cleanup examines only direct regular directories beneath the selected validation
  root. It removes only old (`>=24h`) runs with a parseable terminal `completed` marker
  and no matching live process. Running, failed, malformed, unresolved, symlinked,
  foreign, and otherwise unproven entries are retained.
- The launcher still invokes the real `scripts/validate.ps1`; optional output-root,
  output-hint, and Python-command arguments only forward test/child identity context.

## GREEN and regression evidence

Focused command (system Python equivalent, because `.venv` is absent):

```text
python3 -m pytest -q tests/test_validation_invocation_isolation.py tests/test_00_task4_reset_validation_guard.py --tb=short
```

Final result: `10 passed`.

Additional checks:

```text
python3 -m compileall -q scripts tests       PASS
git diff --check                              PASS
```

PowerShell host was verified read-only before execution:

```text
Executable: /tmp/LingJiToolchain/powershell-7.6.5/pwsh
Version: PowerShell 7.6.5
```

The real entry-only release guard was run through
`scripts/run_powershell_validation.py` with an isolated temporary validation root:

```text
mode: release
entry-only: true
exit: 1 (expected non-zero)
stdout: BLOCKED_4R2_REQUIRED
hook events: preflight
scale-env count: 0
scale-command count: 0
```

The generated run directory contained its own `.owner.json`, failure `summary.json`,
`summary.md`, and preflight log. The temporary root was removed after inspection.

Acceptance synchronization and local-handoff checks are run after this report and the
documentation changes are staged:

```text
python3 scripts/check_acceptance_sync.py
python3 scripts/check_local_execution_handoff.py
```

## Evidence directories

Behavior tests used pytest-managed temporary roots, each with an isolated `validation`
directory. The direct guard used a temporary root under `/tmp/LingJiTask1-real-*`.
All roots created by the direct guard were removed after inspection; no repository
`output/validation` evidence was used as test data. Per-run directory names observed
the form:

```text
[optional-hint]-yyyyMMdd-HHmmss-<32-hex-invocation-id>-<commit>-<mode>
```

## Explicitly not run

The following were intentionally not run, per Task 1 scope: quality CLI, 100k,
full validation, normal release validation, Artifact build/download/install, live
8766/8767 services, Production/Vault access, real chat, owner data, Desktop UI,
Windows/macOS packaging, and owner acceptance. No production process was started,
and no formal or owner data was modified.

## Commits and workspace

Product/tests are separated from docs/evidence:

```text
fix: isolate nested validation evidence
97684938562a1561972fc6a11ef5368d9b64a57e

docs: record validation isolation evidence
PENDING until this report and acceptance docs are committed
```

Files in the product/tests commit:

```text
scripts/validate.ps1
scripts/run_powershell_validation.py
tests/test_00_task4_reset_validation_guard.py
tests/test_validation_invocation_isolation.py
```

Files in the docs/evidence commit:

```text
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/MODULES/CODE_MAP.md
.superpowers/sdd/2026-08-30-release-4r2-acceptance-reset/task-1-report.md
```

The worktree is expected to be clean after the docs/evidence commit. No unrelated
changes were staged or committed.
