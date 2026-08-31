# OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_GATE Release Validation Report

## 1. Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE / release blocked
Product commit: 4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543
Product/tests commit: 81256c4242a6bb8062f1b591832a3313948e9ff9
Task instruction commit: a8d50b5f2f138cf97333dad8aeac38057965ff1f
Artifact: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
```

The real PowerShell release command ran from the isolated worktree. `release` includes `full`; no separate full
invocation was made. The embedded full gate stopped at `python-full`, so the release preflight
`automatic-memory-4r2-readiness` was not reached. This is a release-blocking FAIL, not a PASS or a quality waiver.

## 2. Product and Environment Identity

| Item | Value |
|---|---|
| Repository | `wangduoyu001/lingji` |
| Branch | `codex/owner-memory-detail-drilldown` |
| Candidate documented HEAD | `4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543` |
| Product/tests code commit | `81256c4242a6bb8062f1b591832a3313948e9ff9` |
| Task docs binding commit | `a8d50b5f2f138cf97333dad8aeac38057965ff1f` |
| Checkout HEAD at execution | `33db87612043062cbe336b6cafd684a7f8981ec1` (docs-only task binding after candidate) |
| PowerShell | `7.6.5`, real `pwsh`, runtime architecture `Arm64` |
| PowerShell asset | `powershell-7.6.5-osx-arm64.tar.gz` |
| Official URL | `https://github.com/PowerShell/PowerShell/releases/download/v7.6.5/powershell-7.6.5-osx-arm64.tar.gz` |
| Asset SHA256 | `8196d4b4e7c21b7f6df9d45687bb4e42dc8335f330b580d9eb15f3ef5042a8c3` |
| Artifact/install | `NOT_APPLICABLE_RELEASE_VALIDATION_ONLY` |

PowerShell was downloaded and unpacked only below `/private/tmp/LingJiAcceptance/owner-memory-detail-release-gate/tooling`
(the canonical path of the requested `/tmp/...` root); no global install or PATH mutation occurred.

## 3. Exact Validation and Results

Final command:

```text
/private/tmp/LingJiAcceptance/owner-memory-detail-release-gate/tooling/pwsh -NoLogo -NoProfile -File scripts/validate.ps1 -Mode release -PythonCommand python3 -FailureTailLines 40
```

Process environment used only for this invocation:

```text
LINGJI_VALIDATE_OUTPUT_ROOT=/private/tmp/LingJiAcceptance/owner-memory-detail-release-gate/validation
LINGJI_VALIDATE_OUTPUT_HINT=owner-memory-detail-release-gate
```

| Suite | Result | Duration | Evidence |
|---|---:|---:|---|
| `git-diff-check` | PASS | 0.06 s | validation summary |
| `clean-install-contracts` | PASS | 2.43 s | validation summary |
| `python-full` | FAIL | 274.90 s | failure-log tail |
| `automatic-memory-4r2-readiness` | NOT_REACHED | 0 s | blocked by `python-full` |
| Desktop/build/release tail | NOT_REACHED | 0 s | blocked by `python-full` |

`python-full` summary: **13 failed, 1622 passed, 11 skipped, 7 warnings** in `273.68s`.
The failing tests were:

```text
tests/evaluation/test_task4_reset_runner.py::test_release_preflight_is_executable_and_prevents_scale_invocation
tests/evaluation/test_task4_reset_runner.py::test_runner_stage_exception_publishes_fresh_not_evaluated_envelope[scoring]
tests/integration/test_automatic_memory_packaged_flow.py::test_automatic_memory_packaged_flow_runs_twice_from_clean_acceptance_roots
tests/test_00_task4_reset_validation_guard.py::test_release_entry_executes_real_powershell_when_available
tests/test_brain_status_e2e.py::TestBrainStatusApiContract::test_frontend_dist_exists
tests/test_p2_08_p2_09_integration.py::test_desktop_uses_shared_polling_and_shadow_dashboard_without_execution_controls
tests/test_promotion_recovery_matrix.py::test_recovery_case_06_restart_after_link_commit_activates_after_verification
tests/test_second_brain.py::SecondBrainTests::test_second_brain_is_not_in_original_start_chain
tests/test_structured_evidence_lexical.py::test_formal_mcp_search_entry_returns_structured_message_citation
tests/test_structured_evidence_lexical.py::test_state_db_revoke_and_expiry_are_excluded_from_current_gateway_context_and_mcp
tests/test_task7n1_scale_admission.py::test_unmeasured_runtime_baseline_is_nullable_not_zero
tests/test_task7o_contract_closure.py::test_runner_uses_nullable_mcp_and_baseline_contract
tests/test_task7p_frozen_oracle.py::test_canonical_published_artifact_contains_one_nested_diagnostic_stream
```

The authoritative temporary summary was read at `validation/latest-summary.json|md`, and only the failing
`python-full.log` tail (40 lines) was read. The summary reported `commit=unknown`/`branch=unknown` from the script's
PowerShell git helper; independent shell identity at execution was checkout HEAD `33db8761…` above. This identity
observation is retained as an additional release-integrity concern; no commit or product code was changed to bypass it.

An initial invocation using `/tmp/.../validation` was rejected by the script's reparse-point guard at startup
(`VALIDATION_OUTPUT_ROOT_REPARSE`) before any suite ran. The final invocation used the canonical `/private/tmp` path.

### Failure classification

The failure tail was inspected only around the 13 reported failures. Classification is evidence-based and does not
authorize product changes during this release-only task:

| Failure | Classification | Reason |
|---|---|---|
| Task4 reset runner: executable preflight | `env` | Test invokes missing `./.venv/bin/python` on this Mac. |
| Task4 reset runner: stage exception envelope | `baseline` | Existing generic-ai adapter parse error produces `FAIL` where the historical test expects `BLOCKED`; unrelated to this release gate. |
| Packaged automatic-memory flow | `baseline` | Existing clean-root event scan timed out with no new terminal scan; no service was started by this release gate. |
| Release entry real PowerShell guard | `env` | Test helper searches for a `powershell` command while only isolated portable `pwsh` was allowed; no global alias/PATH was added. |
| Brain status frontend dist | `candidate regression` | Candidate checkout's committed frontend has one JS bundle while the contract requires at least two. |
| P2.08 shared polling dashboard | `candidate regression` | Candidate Desktop source no longer contains the asserted `pending_review_count` projection. |
| Promotion recovery case 06 | `baseline` | Existing restart-after-link path rolled back instead of activating; no related files changed in this gate. |
| Second-brain original start chain | `env` | Test launches missing `python` executable. |
| Structured evidence MCP citation | `baseline` | Existing `SimpleNamespace` fixture lacks `vault_path`; failure occurs before release code runs. |
| Structured evidence revoke/expiry | `baseline` | Same fixture construction failure (`vault_path`) as the preceding test. |
| Task7N1 nullable runtime baseline | `baseline` | Historical quality-contract payload lacks `context_baseline`; this is the known deferred measurement gate. |
| Task7O nullable MCP/baseline contract | `baseline` | Historical quality envelope remains `NOT_MEASURED` where the old assertion expects `FAILED`; known deferred gate. |
| Task7P frozen oracle diagnostics | `baseline` | Historical canonical artifact lacks `diagnostic_evidence`; known deferred 4R2 quality contract. |

The `candidate regression` labels identify contracts currently failing on the candidate tree; `env` labels are local
toolchain/fixture assumptions; `baseline` labels are pre-existing or explicitly deferred contracts. Regardless of
classification, the embedded full gate is FAIL and the release preflight was not reached.

## 4. Scope and Cleanup

```text
Live 8766: FREE after run
Live 8767: FREE after run
LingJi/Desktop/sidecar: NOT_STARTED
PowerShell residual process: none
Install/package/Artifact: forbidden and not performed
Production/Vault/owner data: untouched
Automatic-memory quality status: known MEASURED_FAIL; not reclassified
Separate `full` command: forbidden and not run
```

The release gate did not start a service, read real data, install software, or create an Artifact. Temporary tooling,
validation output and command logs were moved to the user's Trash after evidence extraction (recoverable cleanup); the
acceptance root is absent. The summary metrics, command, failure tail and identity are preserved in this report and the
canonical result receipt.

## 5. Blocking Defects

```text
Defect ID: OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_GATE_FULL_001
Severity: release-blocking
Affected scope: embedded full validation
Reproduction: run the exact release command above from candidate worktree
Expected: all embedded full suites pass and release preflight is reached
Actual: python-full failed with 13 failures; release preflight was not reached
Required fix: repair the failing full-gate regressions, then run one fresh release gate
Retest scope: full suite as embedded by release, followed by release preflight
```

## 6. Final Recommendation

```text
Product commit: 4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543
Validated checkout: 33db87612043062cbe336b6cafd684a7f8981ec1 (docs-only binding after candidate)
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Owner observation complete: NOT_REQUIRED
Artifact/install: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
Blocking defects: OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_GATE_FULL_001
Acceptance docs synchronized: YES
Temporary evidence cleaned: YES (acceptance root absent; recoverable copy in user Trash)
```

## 7. Sign-off

```text
Codex executor: Release Gate execution Luna
Owner confirmation: NOT_REQUIRED (live/install/owner data forbidden)
Acceptance date: 2026-09-01
Report branch: acceptance/owner-memory-detail-drilldown-release-gate-4f0d2a77
Report commit: PENDING
```
