# PR #53 Windows GUI and Low-Context Validation Report

## Scope

This report covers only:

```text
Windows Desktop console-window suppression
Windows Sidecar GUI-subsystem verification
Windows PowerShell 5.1 native stderr handling
low-context local validation output and cleanup
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

## Automated coverage

The existing Windows release smoke now asserts:

- the Tauri release GUI-subsystem attribute;
- Desktop and Sidecar PE-subsystem checks in the packager;
- subsystem metadata fields;
- PowerShell 5.1 warning/exit-code handling contracts;
- stable latest-summary output;
- stale-validation cleanup;
- bounded failure-tail output.

Required PR checks:

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
```

The Windows release workflow remains responsible for the real PyInstaller Sidecar build, authenticated `127.0.0.1:8766` ping, managed stop, Tauri release build, NSIS package, checksums, metadata and artifact upload.

## Installed UI acceptance boundary

Automated checks do not replace owner-machine UI acceptance.

Before completion, the agent must:

1. install the PR artifact or an equivalent package built from the exact validated commit;
2. launch the installed Tauri application, not Vite or a browser page;
3. observe startup and restart with no visible console window;
4. verify the managed Sidecar and authenticated `127.0.0.1:8766` connection;
5. traverse every visible page and operate every visible control using isolated acceptance data;
6. verify each control reaches real API, file, database, task or process logic;
7. reject dead buttons, fabricated success, placeholder pages and UI-only shells;
8. keep the installed UI open for the owner’s final confirmation.

The PR must not be merged solely on automated evidence. Final completion requires the owner’s explicit UI acceptance.

## Safety boundaries

```text
Production Vault access: no
Production SQLite/Qdrant mutation: no
Automatic model download: no
New runtime service: no
New UI framework: no
Test deletion or assertion reduction: no
Owner-machine UI acceptance bypass: no
```

## Status

```text
IMPLEMENTED
AUTOMATED_PR_VALIDATION_REQUIRED
OWNER_MACHINE_UI_ACCEPTANCE_REQUIRED_BEFORE_MERGE
```
