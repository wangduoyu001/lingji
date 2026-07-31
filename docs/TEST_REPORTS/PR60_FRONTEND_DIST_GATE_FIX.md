# PR #60 Frontend Dist Release Gate Fix

Status: IMPLEMENTED, CI PENDING

## 1. Problem

The first owner-machine reacceptance for product commit `d69874afd8def42a40c4a5cc5e678a71921d44b5` stopped before installation because `tests/test_brain_status_e2e.py` required at least two JavaScript bundles.

Vite does not guarantee a minimum bundle count. A valid production build may contain one entry bundle. The old assertion also skipped when `dist` did not exist, which made the Python suite depend on whether a previous frontend build had left files behind.

## 2. Root Cause

The test mixed two unrelated responsibilities:

1. deterministic Local Control API contract tests;
2. validation of mutable frontend build output.

The frontend check ran before the release workflow built the frontend and therefore produced different results in clean and reused worktrees.

## 3. Changes

### `tests/test_brain_status_e2e.py`

Removed the order-dependent frontend filesystem assertion. The file now tests only deterministic API contracts.

### `scripts/validate_frontend_dist.py`

Added a dedicated validator for the actual Vite output. It verifies:

- the `dist` directory exists;
- `index.html` exists;
- `index.html` references at least one JavaScript entry asset;
- referenced JavaScript assets are local;
- asset paths cannot escape `dist`;
- each referenced asset exists and is non-empty;
- one bundle and multiple bundles are both valid.

### `tests/test_validate_frontend_dist.py`

Added deterministic tests for:

- valid single-bundle output;
- missing `dist`;
- missing `index.html`;
- missing JavaScript reference;
- missing bundle;
- empty bundle;
- path traversal;
- remote JavaScript references.

### `desktop/lingji-control/package.json`

Added `validate:dist` and made `npm run build` execute it immediately after `vite build`.

The enforced sequence is now:

```text
TypeScript compile
→ Vite production build
→ validate the newly generated dist
```

This sequence is used by desktop CI, Tauri packaging and Windows release builds.

## 4. Architecture Decision

The product is not forced to create artificial code splitting merely to satisfy a test. Bundle count is an implementation detail. The release contract validates referenced production assets, not their number.

## 5. Data and Security Impact

None. No runtime data, Vault, memory database, Qdrant collection, token or user configuration is accessed or modified.

The validator rejects remote JavaScript and paths escaping the packaged `dist` directory.

## 6. Test Commands

```text
python -m pytest -q tests/test_brain_status_e2e.py tests/test_validate_frontend_dist.py
cd desktop/lingji-control
npm run build
cd ../..
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1 -Mode release
```

## 7. Expected Result

- clean and reused worktrees produce the same release-gate result;
- a valid single Vite bundle passes;
- missing, empty, remote or escaping assets fail;
- Day 0 does not start until the exact-head release gate and new Windows Artifact pass.

## 8. Rollback

Revert the commits that add the dedicated validator, its tests and the `validate:dist` build step. Do not restore the bundle-count assertion.

## 9. Current Limitation

The previous Artifact `8762312712` remains failed and must not be reused. A new exact-head Windows Artifact is required after all CI and release checks pass.
