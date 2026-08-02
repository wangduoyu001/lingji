# PR60 Validation Git Identity Fix

## Defect

During local final-closeout release validation for the fresh Day 0 repair, every build/test/package step passed but both `output/validation/latest-summary.json` and `desktop/lingji-control/release/windows-x64/build-metadata.json` recorded `commit: unknown`; the summary also recorded `branch: unknown`.

The generated installer was therefore not acceptable as exact-Head evidence even though the build steps were green.

## Root Cause

`Get-GitValue` piped native `git` output through `Select-Object` before reading `$LASTEXITCODE`. Under Windows PowerShell 5.1 the later pipeline state can preserve or replace a stale native exit code. A successful Git command then returned valid text while the function rejected it and used the fallback.

## Repair

- Move the Git helper to a small independently testable PowerShell module.
- Capture all native Git output.
- Save `$LASTEXITCODE` immediately after Git returns.
- Select and trim the first output value only after the native exit code is preserved.
- Keep the existing explicit fallback for real Git failures or empty output.

## Acceptance

| Gate | Result |
|---|---|
| Focused validation identity regression | PASS — 33 passed |
| Full Python | PENDING |
| Desktop smoke/build | PENDING |
| Rust/Tauri | PENDING |
| Unified Windows release | PENDING |
| Summary exact commit/branch | PENDING |
| Package metadata exact commit | PENDING |

This repair changes only acceptance/release identity collection. It does not alter LingJi runtime behavior or owner data.
