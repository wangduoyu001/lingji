# Task 1 — Invocation-scoped release evidence

## Status

```text
Status: DONE_WITH_CONCERNS
Base commit: 07382e053882ad63942fa6cb45bae090dbaf1373
Product/tests commit: 38f5cdd45f7a271549e4edc342e856c0c3cf2cbb
Docs/evidence commit: dc75a3942ba9865fce2de4de07e55bd851cf14a6
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

## Repair Round 1 — independent review closure

The complete independent review was read before implementation:
`.superpowers/sdd/2026-08-30-release-4r2-acceptance-reset/task-1-review.md`.
The repair scope was limited to C1, I1, I2, I3, and I4. M1/M2 remain the
explicitly deferred non-blocking operational limitations; no additional product
scope was added.

### Repair RED

After adding real behavior tests for the review findings, the focused command
was run before the repair implementation:

```text
python3 -m pytest -q tests/test_validation_invocation_isolation.py tests/test_00_task4_reset_validation_guard.py --tb=short
```

Result: `8 failed, 10 passed`.

The eight failures were the two parametrized
`test_live_parent_survives_nested_entry_only_without_sleep` cases, plus
`test_active_pid_and_pid_reuse_are_retained_fail_closed`,
`test_per_run_root_reparse_swap_never_writes_outside`, the two parametrized
`test_latest_summary_symlink_never_writes_outside_validation_root` cases,
`test_selected_validation_root_symlink_fails_closed`, and
`test_malformed_foreign_and_nonpositive_owner_markers_are_retained`. They
failed because the prior implementation did not hold a real parent process,
did not fail closed on root/latest/per-run reparse destinations, accepted
unproven owner markers/PIDs for deletion, and skipped valid stale cleanup when
the selected root had a trailing separator.

One additional strict-schema regression was then written first and run RED:

```text
python3 -m pytest -q tests/test_validation_invocation_isolation.py::test_malformed_foreign_and_nonpositive_owner_markers_are_retained --tb=short
```

Result: `1 failed`; a completed marker whose `process_id` had the wrong JSON
type was deleted by the pre-repair reader.

### Repair GREEN

Product/tests repair commit:

```text
38f5cdd45f7a271549e4edc342e856c0c3cf2cbb  fix: isolate nested validation evidence
```

The repair adds canonical no-follow checks for the selected root, ancestors,
per-run directories, regular log/summary files, and latest destinations;
strict bounded owner-marker schema/type/identity/directory binding; fail-closed
PID identity handling where only an explicit `NoProcessFoundForGivenId` result
proves inactivity; and a path+marker recheck immediately before stale removal.
Tests use a real PowerShell barrier and live process without sleeps, cover
same-second and cross-second nested entry-only runs, active and reused PIDs,
trailing roots, actual root/per-run/latest symlinks, outside sentinels, marker
malformation/bounds, parent final writes, logs, and authoritative summaries.

Final focused command after the repair:

```text
python3 -m pytest -q tests/test_validation_invocation_isolation.py tests/test_00_task4_reset_validation_guard.py --tb=short
```

Result: `18 passed` (11 isolation tests and 7 release-guard tests).

Additional required checks:

```text
python3 -m compileall -q scripts tests                 PASS
git diff --check                                        PASS
python3 scripts/check_acceptance_sync.py               PASS (after docs commit)
python3 scripts/check_local_execution_handoff.py       PASS
```

PowerShell was verified read-only before use:

```text
Executable: /tmp/LingJiToolchain/powershell-7.6.5/pwsh
Version: PowerShell 7.6.5
Parser probe: scripts/validate.ps1 -> syntax_errors=0
```

The real entry-only release guard was run through the launcher with a private
temporary validation root and the existing system Python command. It returned
exit status `1` as required, emitted `BLOCKED_4R2_REQUIRED`, wrote exactly the
`preflight` hook event, and produced `scale-env=0` and `scale-command=0`.
Its run directory contained the per-run owner marker, failure summaries, and
preflight log; the temporary root was removed after inspection. No repository
`output/validation` evidence was used for the final guard probe.

### Repair evidence and boundaries

Pytest evidence used pytest-managed temporary directories under the system
temporary area; each test's validation root was isolated and cleaned by pytest.
The direct guard used a temporary `/private/var/folders/.../tmp.*/validation`
root, which was removed after inspection. No evidence fixture or owner data was
left in the repository.

The repair did not run quality CLI, 100k, full validation, ordinary release
validation, Artifact build/download/install, live 8766/8767 services,
Production/Vault, real chat, owner data, Desktop UI, packaging, installation,
or owner acceptance. The available host was PowerShell 7.6.5 rather than
Windows PowerShell 5.1, so Windows-native reparse/PID behavior remains a target
host verification concern; the script remains written for PowerShell 5.1
syntax/commands. M1 latest-pointer cross-run consistency and M2 retention/quota
policy remain deferred as instructed.

The docs/evidence commit is intentionally separate:

```text
docs: record validation isolation evidence
dc75a3942ba9865fce2de4de07e55bd851cf14a6
```

The worktree was checked for a clean status after the docs/evidence commit.
