# Repository Context Routing and Local Validation Report

> Date: 2026-07-26  
> Branch: `work/context-routing-validation`  
> Status: `IMPLEMENTED_PENDING_CI`

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
= complete merge gate on the final tree

release
= full gate plus Windows Sidecar/Tauri/NSIS release build
```

Successful validation emits only concise suite status and summary paths. Full logs remain available per suite and are read only when a failure requires diagnosis.

## Required Validation

- Windows PowerShell 5.1 parses and executes `scripts/validate.ps1 -Mode focused -Area docs`.
- `git diff --check` passes.
- Existing Python, Desktop, Rust, MCP, Obsidian and release gates remain unchanged in coverage.
- `npm run build` remains build-only and Desktop smoke remains explicit.

## Boundaries

- No product behavior changes.
- No database, Vault, Qdrant, Ollama or runtime-data changes.
- No test deletion or assertion reduction.
- No new architecture authority or parallel configuration map.
- No change to `second_brain/` runtime behavior.

## Current Limitation

CI and owner-machine full/release validation have not yet completed for this branch. Until those results exist, this change is implemented but not formally validated.
