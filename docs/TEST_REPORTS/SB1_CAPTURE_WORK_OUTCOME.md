# SB-1 Capture → Work → Outcome 自动验收报告

> Date: 2026-08-22  
> Branch: `feat/sb0-work-fact-contract`  
> PR: `#106` / Draft / DO NOT MERGE  
> Product code SHA: `f23c20c6692d0390ae3c6930b5eba1882bbffb22`  
> Verified repository head: `441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a`  
> Result: `AUTOMATED_PASS`  
> Owner M5: `NOT RUN / NOT IMPLIED BY THIS REPORT`

## 1. Scope

SB-1 connects owner-visible Capture inputs to the canonical Work Fact contract completed in SB-0.

Verified lifecycle:

```text
Cmd+K / Capture Center / supported Capture input
-> authenticated /api/capture/*
-> stable capture identity
-> stable WorkItem(work_id)
-> extraction job(job_id)
-> capture.accepted
-> extraction.queued
-> extraction.started
-> extraction.retrying? when applicable
-> extraction.completed | extraction.failed | extraction.cancelled
-> Outcome success | failure | skipped
-> NextAction actor
-> Desktop exact work_id projection
```

SB-1 does not claim Work → Memory/Evidence completion. That is SB-2.

## 2. Implemented facts

### 2.1 Durable identity

- Capture response contains `capture_id + work_id + job_id` when formally accepted.
- `work_id` is derived from the Capture idempotency identity rather than UI-local/random state.
- extraction job options persist `_lingji_work_id`, `_lingji_capture_id`, `_lingji_capture_identity`.
- duplicate replay after service/runtime recreation resolves to the same `job_id` and `work_id`.
- rejected/invalid input does not create an owner WorkItem.

### 2.2 Extraction lifecycle projection

- claim -> `extraction.started`
- transient retry -> `extraction.retrying`, NextAction actor=`system`
- completed -> success Outcome
- final failed -> failure Outcome with sanitized summary/evidence
- cancelled -> skipped Outcome
- failure does not fabricate a PendingAction
- retry clears the previous terminal Outcome before reopening the same WorkItem
- lifecycle callback failure cannot overwrite extraction queue truth

### 2.3 Desktop handoff

- Capture Center and Cmd/Ctrl+K share the formal `/api/capture/text` path for text capture.
- no direct `/api/memory` write path is introduced.
- no localStorage Work truth is introduced.
- a success claim requires a returned real `work_id`.
- exact work navigation is:

```text
Capture / QuickCapture work_id
-> App.openWork(work_id)
-> workTargetId
-> ActivityPage(workId)
-> GET /api/work/{work_id}
```

- normal Activity navigation without a target continues to use `/api/work/current`.
- this prevents a historical Capture A from opening unrelated current Work B.

## 3. Focused/integration test evidence

Key tests:

```text
tests/test_capture_work_lifecycle.py
tests/test_capture_work_bridge.py
tests/test_capture_control.py
tests/test_capture_api.py
tests/test_work_store.py
tests/test_work_projector.py
tests/test_work_control_api.py

desktop/lingji-control/scripts/work-fact-smoke.mjs
desktop/lingji-control/scripts/quick-capture-smoke.mjs
desktop/lingji-control/scripts/capture-center-smoke.mjs
```

`test_capture_work_lifecycle.py` uses real CaptureControlService + real ExtractionPipeline + SQLite/WorkStore. `test_capture_api.py` primarily validates the authenticated HTTP contract; durable Work persistence is proven by the real lifecycle tests rather than being falsely attributed to its fake control fixture.

## 4. Full repository test evidence

Verified repository head: `441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a`

```text
Linux Python 3.11
585 passed / 11 skipped / 0 failed

Linux Python 3.12
585 passed / 11 skipped / 0 failed

Windows Python 3.12
585 passed / 11 skipped / 0 failed
```

Also PASS:

```text
Desktop full smoke suite
React production build
Tauri configuration validation
MCP smoke
Browser Capture smoke
Obsidian plugin smoke
acceptance-doc-sync
local-execution-handoff
P0 Windows Gate
```

Workflow evidence:

```text
tests: run 32555189462 / SUCCESS
P0 Windows Gate: run 32555189460 / SUCCESS
acceptance-doc-sync: run 32555189473 / SUCCESS
local-execution-handoff: run 32555189451 / SUCCESS
```

## 5. macOS packaged gate

Workflow:

```text
macOS Desktop Gate
run: 32555189465
result: SUCCESS
```

Verified steps include:

```text
Static macOS release smoke
Desktop frontend build
Apple Silicon sidecar build
Rust unit tests
.app build
packaged sidecar contract
packaged authenticated control API boot
DMG creation
DMG mount/final verification
```

Artifact:

```text
name: lingji-macos-arm64
artifact_id: 9471250404
workflow_head: 441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a
sha256: 256577b01f934708b2109032b4b4ac1c269a9188f3958ad590c27d3e2b8f3fe3
```

## 6. Windows packaged gate

Workflow:

```text
Windows Desktop Release Baseline
run: 32555189500
result: SUCCESS
```

Verified steps include:

```text
Desktop smoke
Desktop frontend build
Rust RuntimeManager tests
packaged runtime Python contract
packaged Python runtime build
authenticated health + managed stop
Tauri NSIS installer build
installer/executable/checksum packaging
release artifact contract
artifact upload
```

Artifact:

```text
name: lingji-windows-0.1.0-441d1d2e
artifact_id: 9471266207
workflow_head: 441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a
sha256: 5d375dad7e965f7a8929f24dc8bfa1a15165041166fd50614b66ef04038e7464
```

Rust validation evidence:

```text
name: lingji-runtime-rust-validation-441d1d2e
artifact_id: 9471229744
sha256: 202338d45898352005d139ccb4f22376fc49cd29a9936ed7374e6d24f615a2bd
```

## 7. Regressions found and fixed during SB-1

### 7.1 App shell overwrite

A QuickCapture integration change temporarily replaced the formal `App.tsx` shell with an older simplified version, removing `NAVIGATION`, `RuntimeBoundary`, release metadata and runtime lifecycle controls. Desktop CI failed and the formal shell was restored before SB-1 acceptance.

### 7.2 Exact work-id handoff mismatch

Product tree `7807b9265b56cc69917087942ab7dd7e1163c949` failed because:

1. QuickCapture smoke still required legacy `onNavigate("activity")` behavior.
2. `AppPages` supplied `onOpenWork` while CaptureCenterPage still declared the old `onNavigate` prop, causing TypeScript TS2322.

Final repair product commit:

```text
f23c20c6692d0390ae3c6930b5eba1882bbffb22
```

The old failing tree is not counted as PASS.

## 8. Acceptance boundary

SB-1 status after this report:

```text
AUTOMATED_PASS
```

This does NOT mean:

- Phase 1 is complete;
- owner M5 has passed;
- Work → Memory/Evidence is complete;
- Memory provenance/readability is accepted;
- Opportunity Center may start.

Next engineering node is:

```text
SB-2 — Work → Memory / Evidence
```

Before SB-2 product changes, its acceptance contract must be written/confirmed in `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`.