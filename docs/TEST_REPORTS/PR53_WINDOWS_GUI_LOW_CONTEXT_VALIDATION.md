# PR #53 Windows Desktop Validation Report

## Scope

This report is the current authority for PR #53 and covers:

```text
Windows Desktop and Sidecar console-window suppression
LingJi hardware detection PowerShell regression
owner-confirmed non-system-drive Runtime storage
production / acceptance workspace isolation
capability-level diagnostics
low-context validation
owner-machine installed UI acceptance
```

PR #53 remains Draft, open and unmerged until the installed Windows build is accepted by the owner.

## Owner decision: zero-Shell gate removed

On 2026-07-29 the owner removed the in-application `桌面零 Shell 验收` requirement.

The removed feature attempted to:

- classify `powershell.exe`, `pwsh.exe`, `cmd.exe` and `conhost.exe` by process ancestry;
- observe the process tree for two 60-second phases;
- restart Core inside the observation window;
- block acceptance when the generated report did not pass.

That mechanism was not required for the product and itself became an unusable UI blocker. It has therefore been deleted from the Desktop UI, Tauri command registry, Rust module and smoke contracts.

The removal does **not** revert the real PowerShell defect fix. LingJi had launched this command during routine hardware detection:

```text
Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name
```

That behavior belonged to LingJi and was a product defect. CPU model detection now reads Windows `ProcessorNameString` through `winreg`, physical-disk PowerShell/WMI probing remains removed, and permitted diagnostic executables use hidden/no-window flags on Windows.

## Current Windows window contracts

- Release Tauri builds use the Windows GUI subsystem.
- The packaged Python Sidecar uses PyInstaller `--windowed`.
- Rust starts `lingji-core.exe` directly with `CREATE_NO_WINDOW`.
- Static CPU and disk detection does not launch PowerShell, pwsh or CMD.
- Permitted diagnostic executables such as `nvidia-smi`, `ffmpeg`, `ffprobe` and `nvcc` use `CREATE_NO_WINDOW`, `STARTF_USESHOWWINDOW` and `SW_HIDE`.
- Release packaging reads Desktop and Sidecar PE headers and rejects a non-GUI binary.
- Forced Sidecar termination may use hidden `taskkill` only as the final owned-process fallback.

The product no longer claims that every Shell process is forbidden. The actual product requirement is narrower and useful: routine LingJi startup, hardware inspection and managed runtime lifecycle must not open visible console windows or invoke unnecessary PowerShell probes.

## Runtime data-root contract

```text
%LOCALAPPDATA%\LingJi\desktop-bootstrap.json
= small Desktop bootstrap pointer only

<owner-selected non-C base>\production
= production Runtime data

<owner-selected non-C base>\acceptance
= physically separate acceptance Runtime data
```

Runtime databases, vectors, raw data, logs, cache, token files, lifecycle state and backups must not silently fall back to C.

Installed Desktop startup requires bootstrap schema `2` with `owner_confirmed=true`. Inherited `LINGJI_OWNER_DATA_ROOT` and `LINGJI_WORKSPACE` values are quarantined and cannot satisfy first-run configuration.

## Capability diagnostics

Copied diagnostics distinguish:

```text
Desktop and Runtime lifecycle
bootstrap source and ignored inherited environment
active workspace and effective Runtime data root
C-drive write detection
system health errors and warnings
memory state, count and revision
vector state, collection, count, dimension and rebuild requirement
embedding configured and active model
pending, running and failed task counts
scheduler state
storage free bytes
```

A healthy Runtime process is not treated as proof that every optional capability is healthy.

## Code changes after owner-machine findings

```text
8b4af260  remove CPU and physical-disk PowerShell probes
020fbbfb  hide permitted Windows diagnostic subprocesses
7da1796a  add hardware regression tests
f663de5c  replace obsolete PowerShell CPU expectation
34f6a2d4  remove zero-Shell acceptance UI
4bec5460  remove zero-Shell Tauri command registration
05a70939  remove zero-Shell smoke contract
b93e1d78  delete zero-Shell Rust module
37335ae9  rename regression coverage around windowless hardware behavior
```

The prior artifact `lingji-windows-0.1.0-f663de5c` is obsolete because it still contains the removed zero-Shell UI and command. A new artifact must be built from the final PR head before owner acceptance.

## Automated coverage required at final head

- Python 3.11 and 3.12 repository tests;
- Windows Python tests;
- Desktop smoke and production frontend build;
- Tauri Rust check/tests;
- packaged Python Runtime contract;
- authenticated `127.0.0.1:8766` health and managed stop;
- Windows GUI PE-subsystem verification;
- NSIS build, metadata and checksum verification;
- hardware regression proving CPU/disk detection does not invoke PowerShell probes;
- hidden-window flags for permitted diagnostic subprocesses;
- smoke assertion proving the removed zero-Shell command and module are absent.

Automated validation is pending for the new final head.

## Remaining owner-machine acceptance

After a new artifact is produced:

1. uninstall the obsolete PR #53 build;
2. install the new exact-head artifact;
3. confirm first-run non-C DataRoot selection and acceptance workspace isolation;
4. confirm Runtime becomes connected, healthy and managed;
5. inspect normal startup, diagnostics loading and managed Core restart for visible PowerShell, CMD or console flashes;
6. traverse every visible page and control against real behavior;
7. restart the application and Windows;
8. verify same-version reinstall and uninstall data preservation;
9. keep the installed UI open for owner confirmation.

There is no longer a zero-Shell button, process-name blacklist, two-minute process observation or zero-Shell report requirement.

## Safety boundaries

```text
Production Vault access: no
Production SQLite/Qdrant mutation: no
Legacy LocalAppData deletion or silent migration: no
Automatic model download: no
New runtime service: no
New UI framework: no
Test deletion or assertion reduction: no
Owner-machine UI acceptance bypass: no
```

## Status

```text
LINGJI_POWERSHELL_ROOT_CAUSE_FIXED
WINDOWLESS_DESKTOP_AND_SIDECAR_PRESERVED
ZERO_SHELL_PRODUCT_GATE_REMOVED_BY_OWNER_DECISION
OBSOLETE_F663DE5C_ARTIFACT_REJECTED
NEW_EXACT_HEAD_AUTOMATED_VALIDATION_PENDING
NEW_INSTALLER_AND_OWNER_UI_ACCEPTANCE_REQUIRED
PR_DRAFT_AND_UNMERGED
```
