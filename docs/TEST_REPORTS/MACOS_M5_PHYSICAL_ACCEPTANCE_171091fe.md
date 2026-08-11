# macOS M5 Phase 4 Failure Report — `171091fe`

## Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 171091fe764c6653cdc7325b4a1a71e0b7800822
Rejected Artifact: 9102748834 / REJECTED-lingji-macos-arm64-171091fe
DMG SHA-256: 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
Reconstructed: true
```

## Evidence provenance

The original local report, screenshots, logs, and the expected acceptance branch were not present in this checkout or on GitHub when this report was reconstructed. The current task instruction records the owner's completed physical M5 observation and the exact rejected artifact identity. This report preserves those confirmed facts without manufacturing an App metadata value, a workflow checkout value, or a timestamp that is no longer recoverable.

The contemporaneous macOS follow-up report for the earlier `bf9da9ff` artifact remains a separate historical report. It is useful only as context for the recurring UX and isolation symptom; it is not evidence that its observed identity belongs to `171091fe`.

## Blocking defects

### M5-IDENTITY-002 — installed package identity is not exact

```text
Observed: the owner-confirmed Phase 4 Artifact was rejected for an imprecise package / installed-App identity.
Expected: workflow checkout, final DMG App metadata, installed App diagnostics, Desktop executable, and bundled Sidecar all identify exactly 171091fe764c6653cdc7325b4a1a71e0b7800822.
Evidence: task ID PR88-M5-PHASE4-FAILURE-REPAIR-171091FE; rejected Artifact 9102748834; rejected DMG SHA-256 above.
Exact path: unavailable after cleanup; the task requires the repair gate to read metadata from the final DMG and copied App, rather than infer it from strings.
Exact observed metadata SHA: unavailable; not reconstructed.
Impact: a package can claim or run code other than the reviewed product Head.
```

### M5-UX-003 — normal first run is not owner-readable

```text
Observed: first use still asked the owner to choose a storage location and exposed technical setup information. Automatic discovery only added two AI applications; it did not make the next owner action understandable. No terminal exception was observed.
Expected: normal launch automatically prepares LingJi and arrives at Overview. It must not make the owner choose DataRoot, workspace, production/acceptance mode, Qdrant, SQLite, ports, or bootstrap details. A recoverable failure has one clear primary recovery action; manual path selection is advanced fallback only.
Evidence: owner observation recorded in the active task's Phase 4 failure conclusion.
Exact UI capture path: unavailable after cleanup; source state was not retained.
Impact: the normal first-use path is confusing even when runtime startup has no visible exception.
```

### M5-ISOLATION-002 — runtime wrote outside the task-scoped data root

```text
Observed: the failed launch created ~/Documents/acceptance rather than confining state to the task-scoped acceptance data root.
Expected: with HOME isolated and LINGJI_ACCEPTANCE_DATA_ROOT set, runtime database, Qdrant, logs, raw data, vault, backup, runtime state, and token material stay under the task root; ~/Documents/acceptance does not exist.
Evidence: owner-confirmed Phase 4 failure conclusion in the active task. The owner already moved this round's test data to Trash and restored the previously valid signed /Applications/灵机.app.
Exact write timestamp and process stack: unavailable after cleanup; must be recreated by the required packaged-chain macOS isolation regression.
Impact: acceptance can pollute user-visible Documents and violate production/acceptance physical isolation.
```

## Required repair evidence

Before a new artifact may be built, the repair must add automated regressions that reproduce each failure path, including final-DMG identity comparison and a full packaged bootstrap/Sidecar isolation run. The former Artifact `9102748834` and its DMG hash are permanently rejected and must not be retried.

## Owner and environment status

```text
Owner physical observation: COMPLETE (FAIL)
Old rejected runtime: stopped
Ports 8766/8767: released during owner cleanup
Test evidence and data: moved to Trash by the owner
Previously valid signed /Applications/灵机.app: restored by the owner
New physical reacceptance: NOT AUTHORIZED until a new exact Artifact exists
```
