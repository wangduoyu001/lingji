# Repository Context Routing and Local Validation Report

> Date: 2026-07-26  
> Source branch: `work/context-routing-validation`  
> Merge commit: `96084c49ada2adb33d2202690d3d7b98e5b695ca`  
> Status: `MERGED_AND_CI_VALIDATED`

## Goal

Reduce repeated AI/Codex context loading while preserving clear architecture, module ownership, focused tests and full release gates.

## Changes

- Replaced duplicated root instructions with a concise `AGENTS.md` routing entry.
- Deprecated stale `docs/AI_CONTEXT.md` and redirected current facts to existing authorities.
- Added focused test and validation routing to `docs/MODULES/CODE_MAP.md`.
- Added `scripts/validate.ps1` with `focused`, `full` and `release` modes.
- Added concise JSON/Markdown summaries and per-suite logs under ignored `output/validation/`.
- Added a Windows PowerShell 5.1 CI step for the lightweight `docs` validation mode.
- Added `run_packaged_control_api.py` to the existing Windows compile gate.

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

GitHub Windows release CI and owner-machine installation remain the final authority for packaged lifecycle and installation acceptance.

Successful validation emits only concise suite status and summary paths. Full logs remain available per suite and are read only when a failure requires diagnosis.

## GitHub Validation

```text
tests workflow #753: SUCCESS
P0 Windows Gate #122: SUCCESS
```

Validated coverage:

- Windows PowerShell 5.1 parses and executes `scripts/validate.ps1 -Mode focused -Area docs`.
- Python 3.11, Python 3.12 and Windows tests pass.
- Python compile gate passes, including `run_packaged_control_api.py`.
- Desktop smoke and production build pass.
- Tauri Rust check passes.
- MCP, Obsidian plugin and browser capture checks pass.
- `npm run build` remains build-only and Desktop smoke remains explicit.

## Boundaries

- No product behavior changes.
- No database, Vault, Qdrant, Ollama or runtime-data changes.
- No test deletion or assertion reduction.
- No new architecture authority or parallel configuration map.
- No change to `second_brain/` runtime behavior.

## Remaining Evidence Boundary

No separate owner-machine invocation of `scripts/validate.ps1 -Mode full` or `-Mode release` is recorded in this report. The code and CI contracts are validated; a future release should still retain its own Windows workflow and installation evidence instead of treating this report as an installer acceptance record.
