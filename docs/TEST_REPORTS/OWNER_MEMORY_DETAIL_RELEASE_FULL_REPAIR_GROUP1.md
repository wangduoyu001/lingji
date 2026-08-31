# Owner Memory Detail Release Full Repair — Group 1

## Scope and identity

- Baseline: `b3427d26b6b192461290a167495c8720ff4835f4`
- Activation: `6c7834af`
- Product/test commit: `0b35123402dbda57b2ab19896a0b6d95d3cbaefa`
- Scope: five test/environment contracts only; no memory-detail product code or runtime behavior changed.
- Not run: full, release, live 8766/8767, package, install, Artifact, Production/Vault, real chats, owner data, owner observation.

## Root cause and repair

1. The Task4R preflight and legacy second-brain smoke invoked checkout-specific `./.venv/bin/python` or bare
   `python`. They now invoke `sys.executable`, so the subprocess uses the interpreter running pytest.
2. The real PowerShell entry-only test now forwards `--python-command sys.executable` and uses a per-test output
   root. It neither installs PowerShell nor mutates the global PATH.
3. The frontend build contract incorrectly required at least two JavaScript chunks. It now reads the built
   `index.html`, requires at least one JavaScript entry, and verifies that every referenced entry exists.
4. The Desktop Attention contract asserted the retired `pending_review_count` projection. It now requires the
   current authenticated `/api/work/pending-actions` endpoint, `pendingActionsFrom`, and shared
   `usePollingResource`, while explicitly rejecting the old projection.

## TDD evidence

Initial five-node RED:

```text
python3 -m pytest -q --tb=short \
  tests/evaluation/test_task4_reset_runner.py::test_release_preflight_is_executable_and_prevents_scale_invocation \
  tests/test_00_task4_reset_validation_guard.py::test_release_entry_executes_real_powershell_when_available \
  tests/test_second_brain.py::SecondBrainTests::test_second_brain_is_not_in_original_start_chain \
  tests/test_brain_status_e2e.py::TestBrainStatusApiContract::test_frontend_dist_exists \
  tests/test_p2_08_p2_09_integration.py::test_desktop_uses_shared_polling_and_shadow_dashboard_without_execution_controls
4 failed, 1 passed, 2 warnings
```

The four failures were respectively the missing checkout-local interpreter, missing bare `python`, a one-chunk
valid Vite build, and the removed legacy pending projection. The PowerShell node passed only because no executable
was on the ordinary PATH; it was then exercised separately with the already-downloaded, isolated Microsoft
portable runtime from the preceding failed release gate.

GREEN five-node result:

```text
5 passed, 2 warnings in 2.72s
```

Real isolated PowerShell entry-only result, with its directory prepended only to that pytest child process:

```text
TASK7E_REAL_POWERSHELL_RELEASE_ENTRY PASS events=preflight scale-env=0 scale-command=0
1 passed in 2.18s
```

Direct affected regression:

```text
37 passed, 11 deselected, 2 warnings in 21.42s
```

The 11 deselected cases are the existing Task4R stage-exception parameter matrix, outside this group's authorized
scope. This group does not classify or repair those failures and does not claim full/release readiness.

## Disposition

`FOCUSED_PASS`. The five authorized contracts are closed. The previous release result remains `COMPLETED / FAIL`;
the root agent must finish the other independently classified failures before running a new single release gate.
