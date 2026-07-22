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

## Status

```text
TESTS_ADDED_AWAITING_GITHUB_ACTIONS
```
