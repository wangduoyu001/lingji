# PR #53 Windows Desktop Acceptance Report

## Scope

This report is the current authority for PR #53 and covers:

```text
Windows Desktop and Sidecar console-window suppression
PowerShell 5.1 validation behavior
low-context local validation
owner-confirmed non-system-drive Runtime storage
production / acceptance workspace isolation
capability-level diagnostics
in-application zero-Shell acceptance
owner-machine UI acceptance boundary
```

It does not replace the P2-11B Sidecar lifecycle report or the P2-12A Desktop UI report.

## Pull request state

```text
Branch: work/windows-gui-low-token-validation
Pull request: #53
Base: master
State: draft / open / unmerged
Validated code commit: 83ae73a21161eebdf4bdb713a2d7ddf1c51a9864
```

The PR must remain draft until the owner completes installed UI acceptance.

## Windows process and window contracts

- Release Tauri builds use the Windows GUI subsystem.
- The packaged Python Sidecar uses PyInstaller `--windowed`.
- Rust starts `lingji-core.exe` directly with `CREATE_NO_WINDOW`.
- Runtime startup does not use PowerShell, CMD, WMI, batch files or a general shell plugin.
- Release packaging reads both executable PE headers and rejects a non-GUI Desktop or Sidecar.
- `build-metadata.json` records both GUI-subsystem contracts.
- Forced Sidecar termination uses a hidden `taskkill` process only as the final fallback after the owned stop-request contract and direct child termination fail.

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

Installed Desktop startup requires bootstrap schema `2` with `owner_confirmed=true`. Inherited `LINGJI_OWNER_DATA_ROOT` and `LINGJI_WORKSPACE` values are quarantined before bootstrap resolution and cannot satisfy first-run configuration.

The rejected owner-machine build `b75127d8` trusted an inherited `E:\lingji\acceptance` value, bypassed first-run UI and started Core before owner confirmation. That artifact remains permanently rejected.

## Capability-level diagnostics

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

## Low-context validation contract

```text
success -> concise PASS lines + output/validation/latest-summary.json|md
failure -> concise summary + failing-log tail only
new run -> remove older validation run directories
```

Rules:

- development uses the mapped `focused` area;
- final release runs `-Mode release` once because it already contains `full`;
- successful logs are not loaded into AI context;
- failure investigation starts from the bounded tail and expands only by relevant keywords;
- local acceptance does not modify or rebuild code.

## In-application zero-Shell acceptance

The installed Desktop now exposes `桌面零 Shell 验收` on the existing `环境验收` page.

The command runs entirely inside the Tauri application:

1. require a managed, authenticated healthy Core;
2. observe the Windows process table for 60 seconds;
3. restart Core through `RuntimeManager`;
4. observe for another 60 seconds;
5. confirm Core is again managed and authenticated;
6. classify forbidden Shell processes as LingJi descendants or unrelated external processes;
7. save the JSON report under the active acceptance data root;
8. render the result directly in the UI.

The implementation uses the Windows Toolhelp process snapshot API. It does not invoke PowerShell, CMD, WMI or a batch file.

Forbidden process names:

```text
powershell.exe
pwsh.exe
cmd.exe
conhost.exe
```

Acceptance fails when any forbidden process is found in the LingJi Desktop descendant tree. Unrelated external Shell processes are reported separately so Codex or another program cannot be misclassified as LingJi.

The UI refuses to present a browser or Vite preview as real Desktop evidence.

## Automated coverage

The smoke contract verifies:

- bootstrap schema and explicit owner confirmation;
- inherited environment quarantine;
- guarded Runtime commands;
- first-run configuration UI;
- C-drive rejection and workspace isolation;
- Desktop and Sidecar GUI subsystem contracts;
- absence of a general shell plugin or user-supplied runtime command;
- `CreateToolhelp32Snapshot`, `Process32FirstW` and `Process32NextW` use;
- two 60-second observation phases;
- application-internal Core restart;
- authenticated health verification;
- forbidden descendant and external Shell separation;
- acceptance report persistence;
- real-Tauri UI gating.

Validated code commit:

```text
83ae73a21161eebdf4bdb713a2d7ddf1c51a9864
```

Required checks:

```text
tests #805: SUCCESS
P0 Windows Gate #166: SUCCESS
Windows Desktop Release Baseline #55: SUCCESS
```

The release workflow additionally validated the real PyInstaller Sidecar build, authenticated `127.0.0.1:8766` ping, managed stop, Rust tests, Tauri release build, NSIS package, PE subsystem checks, checksums, metadata and artifact upload.

## Validated artifact

```text
Artifact: lingji-windows-0.1.0-83ae73a2
Artifact ID: 8673355000
Artifact digest: sha256:010f82609244b2a531b84a1d08857ef736b26541904d6ff2a174894ec93cab6c
Installer: LingJi_0.1.0_windows_x64_setup.exe
Installer bytes: 33074243
Installer sha256: 61ab31d095bf44584365f25d6592a0edaee6a79df8e86919614ac147c2a4ec50
```

Independent extraction verified `SHA256SUMS.txt` for the installer, Desktop executable and Sidecar manifest.

`build-metadata.json` confirms:

```text
commit = 83ae73a21161eebdf4bdb713a2d7ddf1c51a9864
channel = pr
target = x86_64-pc-windows-msvc
desktop_pe_subsystem = windows_gui
python_sidecar_included = true
sidecar_pe_subsystem = windows_gui
first_run_configuration_required = true
c_drive_runtime_data_allowed = false
signed = false
```

## Remaining owner-machine acceptance

Automated evidence cannot prove visible-window behavior on the owner machine or replace human UI review.

The remaining acceptance is deliberately small:

1. install the validated artifact;
2. launch LingJi from the Start menu or shortcut;
3. complete owner-confirmed acceptance workspace configuration when required;
4. close Codex and all command windows;
5. open `环境验收`;
6. click `开始桌面零 Shell 验收` once;
7. wait for the application-generated result;
8. confirm no visible blue PowerShell, CMD or black console window appeared;
9. continue the separate full-page and control UI acceptance;
10. keep the installed UI open for owner confirmation.

Local Codex must not poll processes, ports or logs during this observation. It must not modify, rebuild or repair code. A serious failure stops acceptance and returns evidence to the primary developer.

## Release classification

```text
Code signing: not implemented
Updater: not implemented
Artifact class: internal acceptance / PR build
Public production release: not approved
```

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
WINDOWLESS_DESKTOP_AND_SIDECAR_IMPLEMENTED
BOOTSTRAP_BYPASS_CORRECTED
IN_APPLICATION_ZERO_SHELL_ACCEPTANCE_IMPLEMENTED
AUTOMATED_VALIDATION_PASSED_AT_83AE73A2
INSTALLER_HASH_INDEPENDENTLY_VERIFIED
OWNER_MACHINE_ZERO_SHELL_AND_FULL_UI_ACCEPTANCE_REQUIRED
PR_DRAFT_AND_UNMERGED
```
