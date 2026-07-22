# P2-11A Windows Release Baseline Test Report

## Branch

```text
work/p2-11a-windows-release-baseline
```

## Scope

This report covers the reproducible Windows NSIS installer baseline for LingJi Desktop.

## New release smoke test

```text
desktop/lingji-control/scripts/windows-release-smoke.mjs
```

It verifies:

- package.json, Tauri and Cargo versions match;
- NSIS is the only formal bundle target;
- installer mode is current-user;
- WebView2 bootstrapper is embedded;
- build identity variables are exported by Rust build.rs;
- the Tauri release metadata command exists;
- installed credential discovery checks standard Windows owner-local paths;
- copied diagnostics exclude control tokens and Vault paths;
- the release packager generates SHA-256, metadata and installation notes;
- unsigned artifacts cannot claim signing;
- the workflow builds NSIS on Windows;
- pull request builds upload artifacts without publishing releases;
- workflow permissions remain read-only.

The complete Desktop smoke suite increases from 16 to 17 scripts.

## Windows release workflow

```text
.github/workflows/windows-desktop-release.yml
```

Required output:

```text
LingJi_<version>_windows_x64_setup.exe
LingJi_<version>_windows_x64.exe
build-metadata.json
SHA256SUMS.txt
INSTALLATION-NOTES.txt
```

The workflow fails when:

- no NSIS installer is produced;
- the installer is empty;
- no Desktop executable is produced;
- build metadata commit/version does not match;
- metadata claims the unsigned baseline is signed;
- a desktop-v tag does not match the Tauri version.

## GitHub Actions results

Validated implementation head:

```text
4e20ba0c244aff5b5850c1ce60ceb9da19817365
```

Workflow results:

```text
tests #723: SUCCESS
P0 Windows Gate #111: SUCCESS
Windows Desktop Release Baseline #2: SUCCESS
```

Passed gates:

```text
Python 3.11 tests: SUCCESS
Python 3.12 tests: SUCCESS
Windows full tests: SUCCESS
17-script Desktop smoke suite: SUCCESS
React / TypeScript / Vite build: SUCCESS
Tauri configuration validation: SUCCESS
Tauri Rust cargo check: SUCCESS
MCP smoke: SUCCESS
Browser capture smoke: SUCCESS
Obsidian plugin smoke: SUCCESS
Real Windows NSIS installer build: SUCCESS
Release artifact packaging: SUCCESS
Release artifact contract verification: SUCCESS
GitHub Actions artifact upload: SUCCESS
```

## Generated artifact

GitHub Actions artifact:

```text
name: lingji-windows-0.1.0-4e20ba0c
artifact id: 8522596731
archive bytes: 6,490,045
expires: 2026-08-05
```

GitHub artifact digest:

```text
sha256:832cd68c46ac1006877091c8f42a5940dd96ddaf1561955ddb6cca21757c2149
```

The downloaded archive was independently recalculated and matched the GitHub digest:

```text
832cd68c46ac1006877091c8f42a5940dd96ddaf1561955ddb6cca21757c2149
```

## Artifact contents

```text
INSTALLATION-NOTES.txt                    688 bytes
LingJi_0.1.0_windows_x64.exe        9,179,648 bytes
LingJi_0.1.0_windows_x64_setup.exe  3,642,468 bytes
SHA256SUMS.txt                            198 bytes
build-metadata.json                     1,209 bytes
```

Build metadata confirmed:

```text
version: 0.1.0
commit: 4e20ba0c244aff5b5850c1ce60ceb9da19817365
channel: pr
target: x86_64-pc-windows-msvc
installer_format: nsis
installer_install_mode: currentUser
webview_install_mode: embedBootstrapper
signed: false
python_sidecar_included: false
updater_included: false
owner_data_bundled: false
uninstall_deletes_owner_data: false
```

## Independent SHA-256 verification

The checksums were recalculated after downloading and extracting the artifact.

```text
fe4b26fb6b6be98c81379c247beaccfd9c20267586842728cbf54c793f2babef  LingJi_0.1.0_windows_x64_setup.exe
c043e7eeed102ee994c264d5c92a17263c3b762e9eb1b5c52cbf770f59f6fd8f  LingJi_0.1.0_windows_x64.exe
```

The recalculated values matched both:

```text
SHA256SUMS.txt
build-metadata.json
```

## Manual owner checks still required

CI can build, download and inspect the installer but cannot prove all physical Windows interaction behavior on the owner's machine.

Required owner checks:

1. Run the NSIS setup without administrator elevation.
2. Confirm LingJi installs for the current user.
3. Confirm Start Menu and uninstall entries appear.
4. Launch LingJi without opening a browser.
5. Confirm version, channel and short commit appear in the sidebar.
6. Use `复制诊断信息` and verify no token or private path appears.
7. With 8766 stopped, confirm the Desktop shows the offline diagnostic state.
8. With 8766 started and credentials available, confirm reconnect succeeds.
9. Install the same version again and confirm owner data remains unchanged.
10. Uninstall the Desktop and confirm the Vault, storage, settings, SQLite and Qdrant data remain.

## Security and authority impact

```text
Workflow contents permission: read only
Automatic GitHub Release publication: no
Code-signing claim: no
Control token in artifact metadata: no
Private path in copied diagnostics: no
Database schema change: no
Production Vault mutation: no
Production Qdrant mutation: no
Production Ollama mutation: no
Python sidecar included: no
Automatic updater included: no
second_brain changes: no
```

## Status

```text
CI_VALIDATED_AWAITING_OWNER_INSTALL_CHECK
```
