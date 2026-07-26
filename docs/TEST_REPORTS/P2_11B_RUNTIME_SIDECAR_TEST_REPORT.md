# P2-11B Packaged Runtime Sidecar Test Report

## Branch

```text
work/p2-11b-runtime-sidecar-manager
```

## Scope

This report covers:

```text
packaged Python 8766 runtime
owner-local directory contract
persistent Sidecar identity
Rust process lifecycle manager
Desktop runtime controls
Windows NSIS bundling
```

## Python tests

```text
tests/test_packaged_control_api.py
```

The tests cover:

- absolute owner-local storage/log/workspace roots;
- explicit owner Vault preservation;
- non-loopback rejection;
- filesystem-root rejection;
- packaged runtime safety contract;
- state and stop-request paths;
- Sidecar identity publication;
- matching stop request handling;
- mismatched stop request rejection;
- `--check-config` execution without starting the server.

## Desktop smoke test

```text
desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs
```

The smoke verifies:

- target-triple Sidecar declaration;
- onedir runtime resource mapping;
- fixed NSIS hooks;
- no owner-data deletion in hooks;
- loopback-only packaged entrypoint;
- PyInstaller onedir contract;
- optional media provider exclusion;
- Rust fixed-binary process manager;
- authenticated health check;
- bounded startup attempts;
- external-service stop/restart refusal;
- absence of general JavaScript shell execution;
- Desktop start/stop/restart/status commands;
- redacted diagnostics.

The complete Desktop smoke suite increases from 17 to 18 scripts.

## Rust tests

`runtime_manager.rs` includes unit coverage for:

- path redaction;
- token placement under owner-local storage;
- packaged identity mode and loopback requirements.

The release workflow must execute Rust compilation and tests before NSIS packaging.

## Real packaged-runtime acceptance

The Windows release workflow performs a real executable test:

```text
PyInstaller build
-> launch lingji-core.exe
-> wait for token and sidecar-state.json
-> GET /api/health with X-LingJi-Token
-> verify HTTP 200
-> write matching sidecar-stop-request.json
-> verify process exits
-> verify sidecar-state.json is removed
```

A direct `Stop-Process` is reserved only for workflow cleanup if the acceptance step fails.

## Installer acceptance

After Sidecar acceptance, the workflow builds Tauri using:

```text
src-tauri/tauri.sidecar.conf.json
```

It verifies release metadata contains:

```text
python_sidecar_included = true
pyinstaller_mode = onedir
updater_included = false
optional_media_providers_bundled = false
```

Required release output:

```text
LingJi_<version>_windows_x64_setup.exe
LingJi_<version>_windows_x64.exe
lingji-core-manifest.json
build-metadata.json
SHA256SUMS.txt
INSTALLATION-NOTES.txt
```

## Required CI gates

```text
Python 3.11 tests
Python 3.12 tests
Windows full tests
18-script Desktop smoke suite
React / TypeScript / Vite build
Tauri Rust cargo check/test
PyInstaller onedir build
packaged executable config check
authenticated 8766 health check
managed stop request check
Tauri Sidecar bundle
NSIS installer build
release metadata and SHA-256 verification
MCP smoke
Browser capture smoke
Obsidian plugin smoke
```

## Owner-machine checks after CI

1. Install the Sidecar-enabled NSIS package as current user.
2. Launch LingJi with no manually started Python process.
3. Verify the Desktop starts the packaged core automatically.
4. Confirm no PowerShell or Python console window appears.
5. Confirm the Sidebar shows managed core and PID.
6. Stop the core and verify owner data remains.
7. Start the core again and verify the same data returns.
8. Restart the core and verify the Desktop reconnects.
9. Force-close the Desktop while the core is running, reopen it and verify the packaged identity is adopted.
10. Start a manual external 8766 service and verify the Desktop refuses to stop or restart it.
11. Confirm runtime logs are under the redacted owner-local path.
12. Confirm an explicit Obsidian Vault path remains unchanged.
13. Reinstall over the existing version and verify Sidecar files are replaced without deleting owner data.
14. Uninstall and verify Vault, storage, SQLite and Qdrant data remain.

## Security and authority impact

```text
General JS shell permission: no
Arbitrary release executable command: no
Loopback-only control API: yes
Authenticated health check: yes
External process stop/restart: refused
Owner data outside install directory: yes
Explicit Vault preserved: yes
Automatic model download: no
Automatic Qdrant rebuild/delete: no
Automatic updater: no
Database schema change: no
Production memory mutation in CI: no
second_brain changes: no
```

## 2026-07-26 Local NSIS Reinstall Closeout

The final owner-machine acceptance pass was executed in the existing local
repository and install path:

```text
Repository: D:\LingJi-Validation\P2-11B\lingji
Install directory: E:\灵机
Owner data directory: C:\Users\Administrator\AppData\Local\LingJi
```

Additional fixes validated in this pass:

- the PyInstaller sidecar is built with `--windowed`;
- `--check-config-output` validates the windowed executable contract without
  relying on console stdout;
- missing `stdout`/`stderr` streams are mapped to `os.devnull` before Uvicorn
  startup;
- `LINGJI_SIDECAR_PYTHON` allows the release command to use the prepared
  Python 3.12 sidecar environment instead of the system default Python.

Local commands and results:

```text
.venv-p2-11b\Scripts\python.exe -m pytest tests/test_packaged_control_api.py -v
PASS, 10/10

cd desktop\lingji-control && npm run test:smoke
PASS, 18/18

cd desktop\lingji-control && npm run build
PASS

cargo test --manifest-path src-tauri\Cargo.toml --target x86_64-pc-windows-msvc
PASS, 3/3

cargo check --manifest-path src-tauri\Cargo.toml --target x86_64-pc-windows-msvc
PASS

npm run release:windows
PASS with LINGJI_SIDECAR_PYTHON=.venv-p2-11b\Scripts\python.exe
```

Installed runtime acceptance:

```text
NSIS cover install to E:\灵机: PASS
Installed Desktop starts: PASS
Packaged lingji-core.exe starts automatically: PASS
127.0.0.1:8766 listens: PASS
Authenticated /api/health returns HTTP 200: PASS
Matching sidecar stop request clears process/state/port: PASS
Silent uninstall preserves owner data: PASS
Reinstall after uninstall: PASS
```

Artifact hashes:

```text
NSIS installer:
2EA2A047480F19D94AD47EC0C0473F06F67BD06E27EC04CC0E37FE42AB075685

Installed sidecar executable:
F8BEC92FEB0F5238A542140DFD99E522D3B73F4F9E9FE5ED560C1FFE3415487E
```

The installed health endpoint returned `degraded` because optional local
capabilities such as ffmpeg/ffprobe/Ollama were unavailable. This was not a
startup, authentication, or lifecycle failure.

## Status

```text
LOCAL_VALIDATED_AWAITING_GITHUB_CI_ON_FINAL_FIX_COMMIT
```
