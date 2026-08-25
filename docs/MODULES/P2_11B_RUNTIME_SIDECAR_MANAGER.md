# P2-11B Packaged Python Runtime Sidecar Manager

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Make the installed LingJi Tauri Desktop able to start, monitor, stop and diagnose the authenticated local 8766 runtime without asking the owner to open PowerShell.

P2-11B builds on the P2-11A installer baseline and adds a packaged Python core plus a fixed-purpose Rust lifecycle manager.

## Runtime architecture

```text
LingJi Tauri Desktop
-> Rust RuntimeManager
-> packaged lingji-core.exe
-> authenticated 127.0.0.1:8766
```

The Desktop continues to call the normal authenticated 8766 API. It does not access SQLite, Qdrant, Ollama or the Vault directly.

## Owner-local data authority

The installed runtime receives an explicit absolute owner-local root.

Default Windows layout:

```text
%LOCALAPPDATA%\LingJi\
├─ storage\
├─ logs\
├─ runtime\
├─ snapshots\
├─ backups\
└─ workspaces\
```

Mutable runtime stores do not inherit their location from:

- the installation directory;
- the current working directory;
- the Tauri executable directory.

An explicitly configured Obsidian Vault remains authoritative and is not overwritten. When no explicit Vault exists, the packaged runtime uses an owner-local default.

## Packaged Python entrypoint

```text
run_packaged_control_api.py
```

Responsibilities:

- require an absolute `--data-root`;
- reject filesystem roots;
- reject non-loopback hosts;
- configure absolute storage/log/workspace paths before importing `src.config`;
- preserve explicit owner Vault configuration;
- expose `--check-config` without starting the server;
- publish packaged-process identity;
- monitor matching stop requests;
- invoke the existing formal `run_control_api.py` entrypoint.

The formal control API implementation is not duplicated.

## PyInstaller package

Build requirements:

```text
requirements-sidecar-build.txt
```

Build script:

```text
scripts/build_windows_sidecar.ps1
```

Packaging mode:

```text
PyInstaller onedir
executable: lingji-core.exe
contents directory: lingji_core_lib
```

The minimal runtime excludes optional large media providers:

```text
PySide6
torch
tensorflow
paddleocr
faster_whisper
scenedetect
```

Those providers remain separately installable and visible as unavailable when absent.

The build script:

1. creates a clean PyInstaller build;
2. rejects missing executable/runtime files;
3. executes the packaged binary with `--check-config`;
4. prepares the Tauri target-triple executable;
5. copies the onedir runtime directory;
6. writes a sidecar manifest with bytes and SHA-256;
7. removes stale Tauri target copies before bundling.

## Tauri bundle contract

Overlay configuration:

```text
desktop/lingji-control/src-tauri/tauri.sidecar.conf.json
```

It declares:

```text
externalBin: binaries/lingji-core
resource: binaries/lingji_core_lib -> lingji_core_lib
resource: lingji-core-manifest.json
NSIS installer hooks
```

The target-triple source filename is:

```text
lingji-core-x86_64-pc-windows-msvc.exe
```

Tauri installs it as the fixed runtime executable expected by the Rust manager.

## Rust RuntimeManager

Implementation:

```text
desktop/lingji-control/src-tauri/src/runtime_manager.rs
```

Commands exposed to the Desktop:

```text
runtime_status
runtime_ensure
runtime_stop
runtime_restart
```

The manager does not expose a general shell API to JavaScript.

It only resolves the fixed packaged binary. A development-only environment override is compiled only in debug builds.

Responsibilities:

- resolve the owner-local root;
- locate the fixed packaged binary and adjacent runtime directory;
- perform authenticated `/api/runtime/ping` liveness checks;
- detect a healthy external 8766 service;
- start one packaged core;
- prevent duplicate start while an identified Sidecar is starting;
- redirect stdout/stderr to owner-local logs;
- hide the Python console window on Windows;
- perform bounded startup attempts;
- expose PID, start time, restart count, exit code and redacted paths;
- stop or restart only packaged managed processes;
- refuse to stop or restart an ordinary external 8766 service;
- stop a managed Sidecar when the Tauri application exits.

## Persistent Sidecar identity

The packaged Python process writes:

```text
%LOCALAPPDATA%\LingJi\runtime\sidecar-state.json
```

The identity includes:

```text
schema_version
mode = packaged_sidecar
pid
instance_id
started_at_ms
host
port
```

This allows a restarted Desktop to distinguish:

- a packaged LingJi Sidecar that it may adopt;
- an ordinary external 8766 process that it may only use.

The Desktop never adopts a process whose identity is malformed, non-loopback or not marked `packaged_sidecar`.

## Managed stop protocol

The Rust manager writes:

```text
sidecar-stop-request.json
```

The request must contain the matching random `instance_id`.

The Python process monitors the request and exits only when the ID matches. It removes its state file before termination.

Stop behavior:

1. send the matching stop request;
2. wait for process/health shutdown;
3. use a fixed PID fallback only after timeout;
4. remove stale lifecycle files;
5. never touch owner data.

A healthy external 8766 process has no accepted packaged identity and cannot be stopped or restarted from the Desktop.

## NSIS replacement behavior

Installer hooks:

```text
desktop/lingji-control/src-tauri/windows/sidecar-hooks.nsh
```

Before replacing or uninstalling application files, NSIS stops the fixed `lingji-core.exe` image and removes only installed Sidecar binaries.

The hooks do not remove:

```text
Obsidian Vault
LingJi owner-local storage
runtime settings
SQLite state
Qdrant collections
Ollama models
```

## Desktop behavior

The Desktop models:

```text
stopped
starting
healthy
unhealthy
external
failed
```

It shows:

- core health;
- whether the core is Desktop-managed or external;
- PID for managed processes;
- redacted log/data locations;
- last error and exit code;
- restart count;
- whether the installed build contains a Sidecar.

Available actions:

- start core when stopped;
- restart a managed core;
- stop a managed core;
- reconnect to an external core;
- copy redacted diagnostics.

## Windows release workflow

The P2-11A workflow is extended to:

1. install Python 3.12 and pinned Sidecar build requirements;
2. run packaged-entrypoint tests;
3. build the PyInstaller onedir Sidecar;
4. launch the packaged executable;
5. read the generated token;
6. verify authenticated `/api/runtime/ping`;
7. read the published Sidecar identity;
8. submit a matching stop request;
9. verify the packaged process exits and clears stale identity;
10. build Tauri with the Sidecar overlay;
11. build NSIS;
12. include Sidecar identity in release metadata.

## Permanent boundaries

```text
bind: loopback only
general JS shell execution: no
user-supplied release executable path: no
automatic model download: no
automatic Qdrant deletion/rebuild: no
automatic Vault mutation: no
database schema change: no
owner data in install directory: no
updater included: no
code signing claim: no
```

## Changed files

```text
run_packaged_control_api.py
requirements-sidecar-build.txt
scripts/build_windows_sidecar.ps1
tests/test_packaged_control_api.py
.github/workflows/windows-desktop-release.yml
desktop/lingji-control/src-tauri/tauri.sidecar.conf.json
desktop/lingji-control/src-tauri/windows/sidecar-hooks.nsh
desktop/lingji-control/src-tauri/src/runtime_manager.rs
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/src-tauri/Cargo.toml
desktop/lingji-control/src/runtimeTypes.ts
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/hooks/useReleaseMetadata.ts
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/ReleaseUX.css
desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs
desktop/lingji-control/scripts/windows-release-smoke.mjs
desktop/lingji-control/scripts/package-windows-release.ps1
```

## Out of scope

P2-11B does not:

- add automatic updating;
- publish a signed public release;
- bundle optional media models;
- silently run at Windows login;
- migrate arbitrary existing owner data;
- enable Auto Review ACTIVE;
- replace Obsidian Vault + Git as knowledge authority.
