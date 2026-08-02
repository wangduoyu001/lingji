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
| Full Python | PASS — unified release suite |
| Desktop smoke/build | PASS |
| Rust/Tauri | PASS |
| Unified Windows release | PASS — 15/15 suites |
| Summary exact commit/branch | PASS — `4e6d25cc63800e290cdea1bc5e41e51a5bc200ec` / `codex/pr60-validation-git-identity-05376996` |
| Package metadata exact commit | PASS — `4e6d25cc63800e290cdea1bc5e41e51a5bc200ec` |

## Local Release Evidence

```text
validation overall: PASS
validation suites: 15 / 15 PASS
installer sha256: 5db9f275b1d03c109f52b1c886b26500b84a1caa50b6ab85331e6c3b0dbecbd2
portable sha256: a29cdac8ca877b510ecf86377cb86cd8fb836f690cec836de8d05389d6601d23
sidecar sha256: 31efce03dd388dc27c6d6cb8b1e8222be1cc3f1e6953b74586f0233b8f2fd921
manifest sha256: e29c3b28c6b92b768ce46de925efff7bb687ca4fb5e5bf2980254e3bfaad4ff9
build metadata sha256: 871d827621c52ef3e31110c6849061d41795a5ecf81018573b61f686d2668f88
```

Neither the final summary nor build metadata contains the fallback string `unknown`. The local build is validation evidence only; no Release was published and no external deployment occurred.

This repair changes only acceptance/release identity collection. It does not alter LingJi runtime behavior or owner data.
