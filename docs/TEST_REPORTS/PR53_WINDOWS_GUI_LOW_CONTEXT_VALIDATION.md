# PR #53 Windows GUI and Low-Context Validation Report

## Scope

This report covers only:

```text
Windows Desktop console-window suppression
Windows Sidecar GUI-subsystem verification
Windows PowerShell 5.1 native stderr handling
low-context local validation output and cleanup
explicit non-system-drive runtime data-root bootstrap
production / acceptance workspace isolation
capability-level copied diagnostics
mandatory installed-UI acceptance boundary
```

It does not replace the P2-11B Sidecar lifecycle report or the P2-12A Desktop UI report.

## Branch and pull request

```text
Branch: work/windows-gui-low-token-validation
Pull request: #53
Base: master
```

## Implemented contracts

### Desktop and Sidecar window behavior

- Release builds of the Tauri executable use the Windows GUI subsystem through:

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
```

- Debug builds retain normal debug behavior.
- The packaged Python Sidecar remains a PyInstaller `--windowed` executable.
- Rust starts the Sidecar directly with `CREATE_NO_WINDOW`; no `cmd.exe`, PowerShell or batch wrapper is introduced.
- Release packaging reads the PE headers of both executables and rejects any package whose Desktop or Sidecar subsystem is not Windows GUI (`2`).
- `build-metadata.json` records both subsystem contracts.

### Windows PowerShell 5.1 validation behavior

- Native stdout and stderr are written to the suite log.
- Native stderr text is not treated as a build failure when the native exit code is zero.
- A non-zero native exit code remains a hard failure.
- A missing command remains a hard failure.
- Failure output is limited to a configurable tail, defaulting to 40 lines.
- The P0 Windows gate runs a real PowerShell 5.1 probe that writes an expected stderr warning and exits zero.

### Low-context local acceptance

The local validation entry now enforces:

```text
success -> concise PASS lines + output/validation/latest-summary.json|md
failure -> concise summary + only the failing log tail
new run -> remove older validation run directories
```

Operational rules:

- development uses the mapped `focused` area;
- final release acceptance runs `-Mode release` once;
- `release` already includes `full`, so running `full` immediately before `release` on the same tree is prohibited;
- successful logs must not be loaded into an AI/Codex context;
- a failing log is expanded only when its tail is insufficient.

### Explicit runtime data-root bootstrap

The first owner-machine installation of commit `74e6a89e91eb48cb1aeca1b355c9f73724db2ebe`
correctly proved the Desktop and managed Sidecar could start, but it also exposed that the
installed Runtime still defaulted to `%LOCALAPPDATA%\LingJi`. Acceptance stopped before
using that location as isolated test data.

The corrected contract is:

```text
%LOCALAPPDATA%\LingJi\desktop-bootstrap.json
= small Desktop bootstrap pointer only

<owner-selected non-C base>\production
= production databases, vectors, raw data, logs, cache, backups and runtime files

<owner-selected non-C base>\acceptance
= physically separate acceptance equivalents
```

Implemented behavior:

- first installed launch opens a real directory-selection setup screen before starting Core;
- the owner selects `production` or `acceptance` explicitly;
- the effective data root is `<base>\<workspace>`;
- C-drive data roots, relative paths, filesystem roots and unknown workspace names are rejected;
- a write probe verifies the selected directory before saving the bootstrap file;
- all exposed Runtime commands are blocked until a valid data root is configured;
- changing the data root is rejected while port 8766 is active;
- the packaged Sidecar receives the active workspace explicitly and keeps production and acceptance storage/raw/Qdrant paths separate;
- the Local Control token is read only from the configured effective data root;
- legacy `%LOCALAPPDATA%\LingJi` runtime data is not silently migrated, reused, deleted or overwritten.

### Capability-level status and diagnostics

The backend already exposed independent health, memory, vector, embedding, queue, storage,
scheduler, provider and hardware facts through `/api/overview` and related endpoints. The
previous copied diagnostic snapshot exported mostly Desktop/Runtime process state, which
made a healthy process chain look broader than it was.

Copied diagnostics now distinguish:

```text
control API and Runtime lifecycle
bootstrap configuration and active workspace
actual runtime data root and C-drive detection
system health errors and warnings
memory state, document count and revision
vector state, collection, count, dimension and rebuild requirement
embedding configured/active model and state
task pending/running/failed counts
scheduler job count
storage free bytes
```

The UI continues to show separate task, memory, vector, model, compute and storage signals.
A healthy Runtime process no longer serves as evidence that every optional capability is healthy.

## Automated coverage

The Windows release and Desktop smoke contracts assert:

- the Tauri release GUI-subsystem attribute;
- Desktop and Sidecar PE-subsystem checks in the packager;
- subsystem metadata fields;
- PowerShell 5.1 warning/exit-code handling contracts;
- stable latest-summary output;
- stale-validation cleanup;
- bounded failure-tail output;
- first-run data-root setup and bootstrap commands;
- no routine standalone start-core button;
- C-drive rejection without touching the rejected path;
- physical production/acceptance path separation;
- active workspace in Sidecar identity and contract;
- capability-level copied diagnostics without control tokens or Vault paths;
- release metadata that identifies LocalAppData as bootstrap-only and the Runtime root as owner-selected non-system-drive storage.

Final validated commit:

```text
b889bb2fb3fe9b76a949698eec9abfb228e5e8c7
```

Required PR checks:

```text
tests #790: SUCCESS
P0 Windows Gate #151: SUCCESS
Windows Desktop Release Baseline #40: SUCCESS
```

The Windows release workflow validated the real PyInstaller Sidecar build, authenticated
`127.0.0.1:8766` ping, managed stop, Tauri release build, NSIS package, PE subsystem checks,
checksums, metadata and artifact upload.

Final CI artifact:

```text
name: lingji-windows-0.1.0-b889bb2f
artifact id: 8654077495
artifact digest: sha256:cc142fb1e13bcd5551bdbeda76be551191658c3b1dfdc39c52e7480ca7096a61
installer sha256: 20323a2cb04b233c7d815860dededa9295284db175452dce92fdf16ff5b5f3f6
```

## Installed UI acceptance boundary

Automated checks do not replace owner-machine UI acceptance.

Before completion, the agent must:

1. install the PR artifact built from the exact final validated commit;
2. launch the installed Tauri application, not Vite or a browser page;
3. on first launch, select a non-C base directory and the `acceptance` workspace;
4. confirm Core does not start before valid data-root configuration;
5. verify actual mutable files appear only under `<base>\acceptance`;
6. verify `%LOCALAPPDATA%\LingJi` contains only the small bootstrap configuration plus untouched legacy evidence, not new Runtime databases/vectors/logs;
7. observe startup and restart with no visible console or PowerShell window;
8. verify the managed Sidecar and authenticated `127.0.0.1:8766` connection;
9. verify independent health/memory/vector/embedding/task/storage states are truthful;
10. traverse every visible page and operate every visible control using isolated acceptance data;
11. verify each control reaches real API, file, database, task or process logic;
12. reject dead buttons, fabricated success, placeholder pages and UI-only shells;
13. keep the installed UI open for the owner’s final confirmation.

The PR must not be merged solely on automated evidence. Final completion requires the owner’s explicit UI acceptance.

## Release classification

```text
Code signing: not implemented
Updater: not implemented
Current artifact class: internal acceptance / PR build
Public production release: not approved
```

Code signing remains a release-stage requirement and is intentionally not confused with the
current data-root and health-truthfulness acceptance blockers.

## Safety boundaries

```text
Production Vault access: no
Production SQLite/Qdrant mutation: no
Legacy LocalAppData migration/deletion: no
Automatic model download: no
New runtime service: no
New UI framework: no
Test deletion or assertion reduction: no
Owner-machine UI acceptance bypass: no
```

## Status

```text
AUTOMATED_VALIDATION_PASSED
OWNER_MACHINE_REINSTALL_AND_UI_ACCEPTANCE_REQUIRED_BEFORE_MERGE
```
