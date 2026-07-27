# PR #53 Windows GUI and Low-Context Validation Report

## Scope

This report covers:

```text
Windows Desktop console-window suppression
Windows Sidecar GUI-subsystem verification
Windows PowerShell 5.1 native stderr handling
low-context local validation output and cleanup
explicit non-system-drive runtime data-root bootstrap
production / acceptance workspace isolation
capability-level copied diagnostics
mandatory installed-UI acceptance boundary
owner-machine bootstrap-bypass regression and correction
```

It does not replace the P2-11B Sidecar lifecycle report or the P2-12A Desktop UI report.

## Branch and pull request

```text
Branch: work/windows-gui-low-token-validation
Pull request: #53
Base: master
State after owner-machine failure: draft / not mergeable by policy
```

## Implemented contracts

### Desktop and Sidecar window behavior

- Release builds of the Tauri executable use the Windows GUI subsystem:

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

The local validation entry enforces:

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

## Runtime data-root bootstrap

### Intended storage contract

```text
%LOCALAPPDATA%\LingJi\desktop-bootstrap.json
= small Desktop bootstrap pointer only

<owner-selected non-C base>\production
= production databases, vectors, raw data, logs, cache, backups and runtime files

<owner-selected non-C base>\acceptance
= physically separate acceptance equivalents
```

The Desktop must not start Core until the owner has selected a non-C base directory and explicitly selected `production` or `acceptance` in the installed UI.

### Rejected owner-machine acceptance build

The owner-machine acceptance attempt used:

```text
commit: b75127d899cfafb86dfb3597362031b8c2b00a9f
artifact: lingji-windows-0.1.0-b75127d8
installer sha256: bac23cbba4afe892b5325986a96e0ddbe5c8c17d19f007da485be6eb0aa86ebd
```

Observed result:

```text
first configuration UI: not shown
requested acceptance base: D:\codex\lingji-acceptance-data
observed effective data root: E:\lingji\acceptance
Core before owner configuration: started
8766: listening; authenticated acceptance intentionally stopped
visible page/control acceptance: 0 / 0
LocalAppData file count: increased from 9 to 10; file contents were not inspected
UI: kept open during evidence collection, then stopped
```

This build is rejected for owner-machine acceptance and must not be reused.

### Root cause

The installed Desktop treated inherited process environment variables as authoritative bootstrap configuration:

```text
LINGJI_OWNER_DATA_ROOT
LINGJI_WORKSPACE
```

The previous `current_status()` and `apply_saved_environment()` implementation checked those ambient variables before reading the owner-confirmed Desktop bootstrap file. A stale developer or machine-level environment value could therefore:

1. mark bootstrap as configured;
2. bypass the first-configuration UI;
3. select an unintended effective data root;
4. allow the guarded Runtime ensure command to start Core.

The automated tests had verified path rejection and command guarding but had not prohibited ambient environment variables from satisfying the installed-Desktop bootstrap contract.

### Corrective implementation

The corrected contract is now:

- inherited `LINGJI_OWNER_DATA_ROOT` and `LINGJI_WORKSPACE` values are quarantined before Desktop bootstrap resolution;
- ambient environment variables can no longer configure the installed Desktop;
- the saved Desktop bootstrap file is the only authoritative startup configuration;
- bootstrap schema is upgraded from `1` to `2`;
- schema `2` requires `owner_confirmed=true`;
- schema `1` or unconfirmed files force the installed UI back to configuration-required state;
- old bootstrap files can be replaced safely on Windows through temporary and backup files;
- only after the owner saves a valid configuration does the Desktop set process-local Runtime environment values for the managed Sidecar;
- copied diagnostics include `bootstrap_source` and `inherited_runtime_environment_ignored`;
- all Runtime commands remain guarded by `require_configured()`.

The source-of-truth invariant is:

```text
ambient process environment != Desktop configuration
owner-confirmed desktop-bootstrap.json = Desktop configuration
```

## Capability-level status and diagnostics

The backend exposes independent health, memory, vector, embedding, queue, storage, scheduler, provider and hardware facts through `/api/overview` and related endpoints.

Copied diagnostics distinguish:

```text
control API and Runtime lifecycle
bootstrap configuration source
whether inherited Runtime environment was ignored
active workspace
actual Runtime data root and C-drive detection
system health errors and warnings
memory state, document count and revision
vector state, collection, count, dimension and rebuild requirement
embedding configured/active model and state
task pending/running/failed counts
scheduler job count
storage free bytes
```

A healthy Runtime process is not evidence that every optional capability is healthy.

## Automated coverage

The regression smoke contract now asserts:

- bootstrap schema `2` exists;
- explicit `owner_confirmed` is required;
- legacy schema requires owner reconfirmation;
- inherited Runtime environment variables are removed before bootstrap resolution;
- no `environment_status` path can configure the installed Desktop;
- Windows bootstrap replacement uses temporary and backup files;
- diagnostics expose ignored inherited environment state;
- Runtime commands remain guarded;
- first-run configuration UI remains present;
- no routine standalone start-core button is introduced;
- C-drive paths are rejected without touching the rejected path;
- production and acceptance paths remain physically separate;
- no control token or Vault path is copied into diagnostics.

Validated corrective code commit:

```text
78c4e78f497a2f001e9bf5871490fa4326830954
```

Required checks:

```text
tests #799: SUCCESS
P0 Windows Gate #160: SUCCESS
Windows Desktop Release Baseline #49: SUCCESS
```

The Windows release workflow also validated the real PyInstaller Sidecar build, authenticated `127.0.0.1:8766` ping, managed stop, Tauri release build, NSIS package, PE subsystem checks, checksums, metadata and artifact upload.

Automated success does not restore acceptance of the rejected `b75127d8` owner-machine build. A new artifact from the corrected PR head is required.

## Next owner-machine acceptance

Before completion, the agent must:

1. use a new artifact built after the bootstrap-bypass correction;
2. stop and uninstall the rejected build without deleting owner data;
3. ensure no old LingJi Core owns port 8766;
4. launch the installed Tauri application, not Vite or a browser page;
5. confirm the configuration UI appears even when stale machine-level LingJi environment variables exist;
6. select `D:\codex\lingji-acceptance-data` and `acceptance` in the real UI;
7. confirm Core does not start before saving that configuration;
8. confirm the effective Runtime root is exactly `D:\codex\lingji-acceptance-data\acceptance`;
9. identify the exact LocalAppData file added or changed instead of reporting only a count;
10. verify no new Runtime database, vector, raw, cache, log or token file appears under LocalAppData;
11. verify startup and restart produce no visible PowerShell, cmd or console window;
12. verify the managed Sidecar and authenticated `127.0.0.1:8766` connection;
13. verify independent health, memory, vector, embedding, task and storage states are truthful;
14. traverse every visible page and operate every visible control using isolated acceptance data;
15. keep the installed UI open for the owner's final confirmation.

The PR must not be merged solely on automated evidence. Final completion requires the owner's explicit UI acceptance.

## Release classification

```text
Code signing: not implemented
Updater: not implemented
Current artifact class: internal acceptance / PR build
Public production release: not approved
```

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
REJECTED_OWNER_MACHINE_BUILD_B75127D8
BOOTSTRAP_BYPASS_CORRECTED
AUTOMATED_REGRESSION_VALIDATION_PASSED
NEW_INSTALLER_AND_OWNER_UI_ACCEPTANCE_REQUIRED
PR_DRAFT_AND_UNMERGED
```
