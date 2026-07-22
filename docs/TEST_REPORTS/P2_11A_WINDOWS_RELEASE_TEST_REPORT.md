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

## New Windows release workflow

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

The workflow must fail when:

- no NSIS installer is produced;
- the installer is empty;
- no Desktop executable is produced;
- build metadata commit/version does not match;
- metadata claims the unsigned baseline is signed;
- a desktop-v tag does not match the Tauri version.

## Existing gates preserved

```text
Python 3.11 tests
Python 3.12 tests
Windows full tests
17-script Desktop smoke suite
React / TypeScript / Vite build
Tauri Rust cargo check
MCP smoke
Browser capture smoke
Obsidian plugin smoke
```

## CI artifact checks

After the pull request workflow runs:

1. Download the `lingji-windows-<version>-<commit>` artifact.
2. Confirm all five required files are present.
3. Confirm the installer size is greater than zero.
4. Recalculate SHA-256 for the installer and executable.
5. Confirm the values match `SHA256SUMS.txt` and `build-metadata.json`.
6. Confirm `signed` is false.
7. Confirm `python_sidecar_included` is false.
8. Confirm no Vault, storage, SQLite or Qdrant data is included.

## Manual owner checks still required

CI can build and inspect the installer but cannot prove all physical Windows interaction behavior on the owner's machine.

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
TESTS_ADDED_AWAITING_GITHUB_ACTIONS
```
