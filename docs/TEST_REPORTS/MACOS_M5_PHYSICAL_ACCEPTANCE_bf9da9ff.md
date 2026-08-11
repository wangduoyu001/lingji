# MACOS-M5-UX-REACCEPTANCE-BF9DA9FF Report

## Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Task: MACOS-M5-UX-REACCEPTANCE-BF9DA9FF
Product commit required by task: bf9da9ffec54c8e9cb927ffd0f3b9fd7213df928
Artifact: lingji-macos-arm64 / Artifact 9095953036
```

## Identity and Precheck

| Check | Actual | Result |
|---|---|---|
| macOS host | Apple Silicon arm64; Python and Node arm64 | PASS |
| Gatekeeper | enabled | PASS |
| Actions run 31477467940 | completed successfully; PR head `bf9da9ff…` | PASS |
| DMG SHA256 | `2373bf05629ea4aaec8f47433e1a0805f004bd3edd2e9638c972a8361c5ab39d` | PASS |
| DMG size | `46237964` bytes | PASS |
| Mounted app / sidecar | app, sidecar and runtime library present; arm64 | PASS |
| Mounted app signature | `codesign --verify --deep --strict` passed | PASS |
| Embedded Desktop build commit | `0753251301615f62369e7f5aa36873822d12b054` | FAIL |

The embedded commit is the GitHub pull-request merge commit, not the task's exact product commit. The required product identity therefore cannot be asserted for this Artifact.

## Owner-first UX Reacceptance

```text
First launch result: FAIL
Owner observation: no abnormal terminal window; selecting the storage location should be automatic; the flow remains insufficiently clear; only automatic discovery of two AI tools was visibly added.
Codex observation: first page was improved to “选择一个位置存放灵机资料” and technical terms moved to Advanced Settings, but a manual location-selection step remained mandatory.
Autodiscovery: UI reported two recognized AI tools and 4,400 Codex work-record metadata items; no owner authorization for source-body reading was given.
Codex work-record clarity: NOT_ACCEPTED by owner as part of the overall unclear flow.
Owner-decision vs system-issue clarity: NOT_ACCEPTED by owner as part of the overall unclear flow.
Technical-detail visibility: technical details were collapsed under Advanced Tools, but this does not cure the failed primary flow.
```

## Runtime and Data Safety

```text
Runtime result: FAIL
Control API result: NOT_TESTED_AFTER_IDENTITY_FAILURE
Restart result: NOT_TESTED_AFTER_IDENTITY_FAILURE
```

Before any location was selected, the Desktop automatically started an acceptance Core and displayed its data root as `~/Documents/acceptance`, outside the task's required isolated root. Metadata-only inspection showed that this directory was created during this test and contained Runtime, SQLite, Qdrant, token, log, raw, vault, and backup subdirectories. No source-body authorization was granted.

```yaml
production_pollution_count: 1
unexpected_data_root: ~/Documents/acceptance
unexpected_data_root_created_during_test: true
```

This is a test-data isolation failure even though the generated directory was subsequently removed from its original path.

## Installation Observation

The first overlay copy onto the previous acceptance app failed strict signature validation because stale `numpy-2.5.1.dist-info` resources from the older app remained while the new signed bundle used different resources. A clean copy after moving the known prior acceptance app aside passed signature validation. This is an installation-path regression risk: an ordinary overwrite must not leave a sealed bundle invalid.

## Cleanup

```yaml
pre_cleanup: PASS
post_cleanup: PASS
temp_root_absent: true
unexpected_documents_root_absent: true
orphan_runtime_count: 0
listening_8766_after_cleanup: false
listening_8767_after_cleanup: false
retained_core_files:
  - /Applications/灵机.app (restored from the prior original DMG and verified signed)
```

The exact task root, mounted DMG, failed new app copy, generated `~/Documents/acceptance` tree, logs, token, database, Qdrant files, and temporary installation backup were moved to local Trash after their ownership and creation during this test were verified. This keeps cleanup recoverable while removing all original task paths.

## Blocking Defects

```text
M5-IDENTITY-001 (P1)
Expected: Artifact metadata identifies exact product commit bf9da9ff….
Actual: Desktop displays 07532513…, the pull-request merge commit.
Required fix: build and publish an artifact with a product-commit identity contract that matches the task.

M5-UX-002 (P1)
Expected: owner can start without manually reasoning about where LingJi data should live.
Actual: owner found the manual storage-location flow unclear and expected it to be automatic.
Required fix: revise the default/automatic storage decision and first-use explanation; rebuild a new artifact and repeat owner reacceptance.

M5-ISOLATION-001 (P0)
Expected: all test runtime data stays under the task's isolated root.
Actual: a Core started before user selection and wrote to ~/Documents/acceptance.
Required fix: require the configured task-scoped root before Runtime startup and add a regression test covering fresh macOS first launch.

M5-INSTALL-001 (P1)
Expected: direct overwrite installation leaves the app signature valid.
Actual: overlay installation retained stale resources and caused sealed-resource verification failure.
Required fix: ship or document a replacement installation flow that removes stale signed-bundle resources safely.
```
