# Repository Context Routing and Local Validation Report

> Date: 2026-07-26  
> Initial context-routing merge: `96084c49ada2adb33d2202690d3d7b98e5b695ca`  
> Mainline convergence merge: `fdb2467a61b0596200f2836cf8c04d68efb6c992`  
> Master validation finalization: `ea93e21de0dfc622167dbf8f0cf3094f5c6f9b20`  
> Status: `MERGED_AND_CI_VALIDATED`

## Goal

Reduce repeated AI/Codex context loading, remove stale automatic context, converge the validated repository history into the default `master` branch, and provide truthful focused/full/release validation without duplicating test implementations.

## Changes

- Replaced duplicated root instructions with a concise `AGENTS.md` routing entry.
- Deprecated stale AI context pointers and redirected current facts to existing authorities.
- Removed six obsolete `.codex/context/` files that still described the PySide6/8765 parallel prototype.
- Added focused test and validation routing to `docs/MODULES/CODE_MAP.md`.
- Added `scripts/validate.ps1` with `focused`, `full` and `release` modes.
- Added concise JSON/Markdown summaries and per-suite logs under ignored `output/validation/`.
- Added a Windows PowerShell 5.1 CI check for the lightweight validation entry.
- Added `run_packaged_control_api.py` to the Windows compile gate.
- Added a concise root `README.md` and replaced obsolete setup, environment, configuration and data-flow instructions.
- Merged the complete validated feature history into GitHub's existing default `master` branch with a normal merge commit.
- Retargeted P0 Windows and Windows release PR gates to `master`.
- Expanded local `full` coverage with clean-install, browser extension and isolated MCP checks.
- Expanded local `release` to prepare checksums, metadata, installation notes and the Sidecar manifest after the Windows build.

## Context Contract

Default task loading is now:

```text
AGENTS.md
-> relevant PROJECT_STATUS section
-> relevant CODE_MAP section
-> directly affected code and tests
```

Architecture, governance and historical reports are loaded only when the task depends on those contracts.

## Validation Modes

```text
focused
= module tests during development

full
= complete local merge gate on the final tree

release
= full gate plus Windows Sidecar/Tauri/NSIS build and release-artifact preparation
```

GitHub Windows release CI and owner-machine installation remain the final authority for packaged lifecycle and installation acceptance. The local entry does not duplicate the release workflow's managed Sidecar process test.

Successful validation emits only concise suite status and summary paths. Full logs remain available per suite and are read only when a failure requires diagnosis.

## GitHub Validation

Initial context routing:

```text
tests workflow #753: SUCCESS
P0 Windows Gate #122: SUCCESS
```

Master history convergence:

```text
PR #51 tests workflow #755: SUCCESS
merge commit: fdb2467a61b0596200f2836cf8c04d68efb6c992
```

Master validation finalization:

```text
PR #52 tests workflow #757: SUCCESS
PR #52 P0 Windows Gate #123: SUCCESS
PR #52 Windows Desktop Release Baseline #12: SUCCESS
merge commit: ea93e21de0dfc622167dbf8f0cf3094f5c6f9b20
```

Validated coverage:

- Windows PowerShell 5.1 parses and executes the local validation entry.
- Python 3.11, Python 3.12 and Windows full tests pass.
- Clean-install and Python compile gates pass, including `run_packaged_control_api.py`.
- Desktop smoke and production build pass.
- Tauri Rust check and RuntimeManager tests pass.
- MCP, Obsidian plugin and browser capture checks pass.
- Packaged Python Sidecar build, authenticated runtime ping and matching managed stop pass.
- Tauri NSIS installer, release metadata, checksums, installation notes, Sidecar manifest and artifact upload pass.
- `npm run build` remains build-only and Desktop smoke remains explicit.
- `master` and `feature/second-brain-memory` were synchronized to an identical remote tree after convergence.

## Boundaries

- No product behavior changes.
- No database, Vault, Qdrant, Ollama or runtime-data changes.
- No test deletion or assertion reduction.
- No new architecture authority or parallel configuration map.
- No change to `second_brain/` runtime behavior.
- No access to the old project directory.

## Remaining Evidence Boundary

No separate owner-machine invocation of `scripts/validate.ps1 -Mode full` or `-Mode release` is recorded in this report. CI validates the same underlying contracts and the Windows release chain, but a future release must still retain owner-machine installation, reinstall and uninstall evidence instead of treating CI as a substitute.
