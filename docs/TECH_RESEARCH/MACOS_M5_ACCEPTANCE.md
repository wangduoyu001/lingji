# LingJi macOS M5 / Apple Silicon Acceptance

Status: **CI acceptance passed; physical M5 GUI acceptance pending owner run**

Date: 2026-08-09

## Scope

LingJi remains one product and one core codebase. Windows and macOS are platform release targets, not separate product branches.

- Windows release remains NSIS / `x86_64-pc-windows-msvc`.
- macOS release targets Apple Silicon / `aarch64-apple-darwin` and DMG.
- Core Python services, Control API, memory/data contracts and React UI remain shared.
- macOS-specific work is limited to build/release configuration and the smallest bootstrap environment shim required by the existing desktop runtime.

## Apple Silicon build gate

Workflow: `.github/workflows/macos-desktop-gate.yml`

Passing run:

- Run ID: `31288663236`
- Head commit: `c10d25541ec8814179545e03f3c6709b7beeb283`
- Runner: GitHub hosted `macos-15`, verified `uname -m == arm64`
- Python: 3.12 native arm64
- Rust target: `aarch64-apple-darwin`

All gate stages passed:

1. Apple Silicon runner verification.
2. Native arm64 Python verification; Rosetta builds are rejected by the sidecar build script.
3. macOS release static smoke test.
4. React desktop frontend build.
5. Native PyInstaller Sidecar build.
6. Sidecar packaged-runtime configuration contract check.
7. Rust unit tests on `aarch64-apple-darwin`.
8. Tauri `.app` release build.
9. Packaged Sidecar found inside the `.app` resources.
10. Packaged Sidecar launched from the `.app` and authenticated `127.0.0.1:8766/api/runtime/ping` successfully.
11. DMG created from the verified app build.
12. Final DMG mounted read-only with `hdiutil`.
13. `.app` found inside the mounted DMG.
14. Sidecar and `lingji_core_lib` found inside the DMG app.
15. `codesign --verify --deep --strict` passed for the mounted app.
16. Sidecar contract check passed when executed directly from the mounted DMG.
17. DMG artifact upload passed.

## Artifact

Artifact name: `lingji-macos-arm64`

Artifact ID: `9030728866`

Artifact digest:

`sha256:c7d052daebfb65ac4adfd443efa8dd7d2f471c5aad77f6849b54e06b18d1f81e`

Artifact archive size: 45,994,342 bytes.

Archive contains:

`灵机_0.1.0_aarch64.dmg`

DMG size in the artifact: 46,204,704 bytes.

## macOS release implementation

### Build script

`scripts/build_macos_sidecar.sh`

- Defaults to `aarch64-apple-darwin`.
- Requires a native arm64/aarch64 Python for Apple Silicon builds.
- Explicitly rejects a Rosetta/x86 Python for M-series releases.
- Mirrors the existing Windows PyInstaller `onedir` packaging contract.
- Produces the Tauri target-triple Sidecar and shared `lingji_core_lib` runtime directory.

### Tauri platform configuration

`desktop/lingji-control/src-tauri/tauri.macos.conf.json`

- Keeps DMG configuration out of the Windows base release configuration.
- Maps the Apple Silicon Sidecar into the resource name expected by the existing RuntimeManager without forking the RuntimeManager implementation.
- Uses ad-hoc signing identity `-` for unsigned Apple Silicon development/acceptance builds.

### Desktop bootstrap shim

`desktop/lingji-control/src-tauri/src/main.rs`

On macOS only, before the existing bootstrap code runs, `$HOME/Library/Application Support` is exposed through the existing owner-local bootstrap directory contract. Windows behavior is unchanged.

This is intentionally a small platform boundary instead of a second macOS implementation of the runtime.

## Windows preservation

Windows regression was checked after the macOS platform work.

General workflow run `31288497766` passed:

- Python 3.11 unit tests.
- Python 3.12 unit tests.
- Windows compile.
- Windows unit tests.
- Desktop UI smoke tests.
- Obsidian plugin smoke tests.
- MCP smoke test.
- Browser capture smoke test.

The Windows NSIS base bundle target and existing Windows Sidecar builder remain in place.

## Physical M5 acceptance

CI proves the Apple Silicon architecture/release chain and packaged local runtime. It does not replace a real GUI launch on the owner's M5 Mac.

Owner acceptance should use the generated `灵机_0.1.0_aarch64.dmg` and verify:

1. DMG opens normally.
2. `灵机.app` can be copied to Applications.
3. App opens on the physical M5 Mac.
4. First-run data-directory selection is visible and understandable.
5. Production workspace can be selected/configured.
6. Runtime reaches healthy state.
7. Control API reports healthy.
8. Existing Vault/data can be selected without modifying the source data unexpectedly.
9. Ollama/Obsidian and other optional local dependencies are detected or clearly reported as unavailable rather than silently failing.
10. Quit/reopen preserves configuration and does not create duplicate runtime processes.

Only after these owner-device checks should the physical M5 acceptance status be changed from pending to passed.

## Next engineering gate

After physical M5 launch is confirmed, the next priority is local storage lifecycle governance:

- runtime log rotation and retention;
- temporary-file cleanup;
- cache quota/expiry;
- stale report retention;
- SQLite event/history maintenance;
- visible storage-health reporting.

These should be added without changing the authoritative memory/data model or splitting Windows/macOS core behavior.
