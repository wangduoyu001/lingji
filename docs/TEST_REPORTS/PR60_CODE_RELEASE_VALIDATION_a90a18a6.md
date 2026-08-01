# PR60 Code Release Validation

## Executive verdict

```text
Task: PR60-CODE-RELEASE-VALIDATION-A90A18A6
Verdict: BLOCKED
Merge recommendation: DO NOT MERGE
Product commit: a90a18a66ffba157c01367ba70bfec98f58798e2
Artifact: local validation output only (not a GitHub Artifact)
```

## Scope and safety boundary

This validation covers the frontend `dist` gate repair and the full Windows release chain. It did not install LingJi, start the Desktop UI or Production Runtime, read or import real material, or modify Vault, production databases, Qdrant, or owner AI-client settings. No listener was present on 8766 or 8767 before execution.

The remote PR #60 head was read before execution and matched the product commit exactly. Validation used an isolated worktree at the required commit. The recovery-only task instruction is `932d1c159cddec6b79742bed43f7b30f651eb15f` from `master`.

## Environment and preparation

```text
OS: Windows
Python: 3.13.2
Node/npm: npm 11.12.1
Cargo: 1.97.1
Pre-cleanup: PASS (task temporary root was absent; no LingJi processes or 8766/8767 listeners)
```

The first release invocation stopped at `windows-release-build` because the isolated Python lacked `PyInstaller`. The dependency is declared by `requirements-sidecar-build.txt`; it was installed only into a task-local virtual environment and cache. The full release command was then restarted from the beginning, rather than retrying just the failed step.

Failure tail from that initial invocation:

```text
No module named PyInstaller
PyInstaller failed with exit code 1
```

## Test results

| Command / suite | Exit | Result | Evidence |
|---|---:|---|---|
| `python -m pytest -q tests/test_brain_status_e2e.py tests/test_validate_frontend_dist.py` | 0 | 11 passed | Validates the single-bundle success case and missing, empty, remote-script, and out-of-bound-path failures. |
| `python -m pytest -q --tb=short` | 0 | 583 passed, 10 skipped, 3 subtests passed | Full Python regression. |
| `python -m compileall -q ...` | 0 | PASS | Required Python entry points, `src`, compatibility code, tests, and scripts compiled. |
| `npm ci --no-audit --no-fund` | 0 | PASS | Clean Desktop dependency install. |
| `npm run test:smoke` | 0 | 22 scripts passed | Desktop static smoke suite. |
| First clean `npm run build` | 0 | PASS | `validate:dist` passed with exactly 1 JavaScript entry. |
| Repeat `npm run build` with `dist` retained | 0 | PASS | `validate:dist` again passed with exactly 1 JavaScript entry. |
| `cargo test --manifest-path desktop/lingji-control/src-tauri/Cargo.toml --target x86_64-pc-windows-msvc` | 0 | 9 passed | Rust/Tauri runtime tests. |
| First `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1 -Mode release` | 1 | Environment dependency failure | `PyInstaller` absent; no code/test bypass applied. |
| Rerun of the same full release command with task-local Sidecar venv | 0 | PASS | All 15 full/release suites passed. |

The successful release summary recorded these release-stage results: `windows-release-build` PASS (249.55s) and `windows-release-package` PASS (0.76s). Its recorded commit is exactly `a90a18a66ffba157c01367ba70bfec98f58798e2`.

## Local release identity and hashes

All required local files existed and were non-empty. `build-metadata.json` recorded the exact product commit and channel `local-validation`; the Sidecar manifest hash matched the built Sidecar executable. These are local validation outputs only, not GitHub Artifacts.

| File | Bytes | SHA-256 |
|---|---:|---|
| Installer | 34,830,386 | `eedf292b17da9aa420183db3f18717f425dd432fd26d65dfd3d9ea9ea75de1d9` |
| Portable EXE | 9,516,032 | `765eee8828dbe58a277381c541ecf67e178603997fb2b20ad8cd33f8abce8d3c` |
| Sidecar EXE | 11,794,062 | `dec11548ee835ba11f9ac8d515ba5dfefb8a31e1e087d656e736225f94bf0731` |
| `build-metadata.json` | 3,503 | `5cdb8c334497465807f948bc562c84896264ad1c7cf41db400bd6495d98f6ffe` |
| `lingji-core-manifest.json` | 3,529 | `6a532313b4faf0bab1ccbbf9575f008d998bcfd05d6332393db0f2e278115c34` |
| `SHA256SUMS.txt` | 291 | `af7451120f56d15d382249d66c8ef0687338da60b54669430815258a247cd2df` |

## Final status

```text
Release validation: PASS (all required code/build/release checks; not rerun during recovery)
Owner observation: NOT_REQUIRED (this task expressly prohibits installation and UI launch)
Temporary evidence cleanup: BLOCKED_POST_CLEANUP
```

## Cleanup recovery

The prior `BLOCKED_POST_CLEANUP` outcome was caused solely by the cleanup-policy allowlist. `master` commit `0f9bb6421bceea815bfe8c5d26b59728c0f49fb6` corrected that policy. This recovery ran only the focused cleanup-tool test (10 passed), a safe dry-run, registered-worktree removal, and the explicit approved cleanup. The task-specific temporary root was removed successfully; the cleanup tool reported 13,245 files and 2,130 directories removed with no remaining entries.

No product test, Desktop build, Rust/Tauri test, release command, artifact generation, installation, UI launch, or real-data operation was rerun during recovery. The release results and all hashes above are retained unchanged.

The task additionally required deletion of the external recovery-worktree parent after remote read-back. Its sole remaining empty parent directory was explicitly targeted, but the execution environment safety policy refused that deletion. No bypass or manual alternative was used. Therefore the product release evidence remains PASS, but this recovery task cannot claim final completion and is `BLOCKED_POST_CLEANUP`.
