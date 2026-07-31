# PR60 Release Gate Bundle Contract Fix

Status: IMPLEMENTED, WAITING FOR EXACT-HEAD CI AND NEW ARTIFACT

## 1. Trigger

The owner-machine Day 0 trial for product commit `d69874afd8def42a40c4a5cc5e678a71921d44b5` stopped before installation because the mandatory local release validation failed in:

```text
tests/test_brain_status_e2e.py::TestBrainStatusApiContract::test_frontend_dist_exists
```

The built Vite frontend contained one valid `index-*.js` entry bundle, while the old test required at least two JavaScript files.

## 2. Root cause

The product build configuration does not promise a minimum chunk count. Vite may legally emit one or multiple JavaScript bundles depending on dependency graph and optimization decisions.

The old assertion confused bundle count with build validity and was also execution-order dependent because it skipped when `dist` did not yet exist.

## 3. Fix

The test now validates the actual production contract:

1. `dist/index.html` exists;
2. `dist/assets` exists;
3. `index.html` references at least one JavaScript entry asset;
4. every referenced JavaScript asset resolves inside `dist`;
5. every referenced asset exists and is non-empty.

The fix does not force artificial code splitting and does not change product runtime behavior.

## 4. Files

```text
tests/test_brain_status_e2e.py
docs/TEST_REPORTS/PR60_RELEASE_GATE_BUNDLE_CONTRACT_FIX.md
```

## 5. Required validation

The exact product Head created by this fix must pass:

```text
python -m pytest -q tests/test_brain_status_e2e.py
python -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1 -Mode release
Desktop production build
P0 Windows Gate
Windows Desktop Release Baseline
```

A new Artifact is mandatory because the product Head changes. Artifact `8762312712` and commit `d69874af` become historical failed identities and must not be reused.

## 6. Acceptance continuation

After exact-head validation and a new Windows Artifact:

```text
clean old acceptance-only temporary data
→ verify new identity
→ rerun Day 0
→ owner UI checkpoints
→ real Codex MCP call
→ candidate review
→ restart and Windows reboot
→ authorized real-data trial
```

No real data was accessed by the failed run.

## 7. Rollback

Revert the test commit if the referenced-asset contract proves incorrect. Do not restore the `>=2` bundle-count assertion unless the product architecture explicitly adopts and tests a mandatory chunking policy.
