# P2-11A Windows Release Baseline

## Goal

Create the first reproducible Windows delivery artifact for LingJi Desktop.

This phase proves that the Tauri application can be built into a Windows NSIS installer and accompanied by enough identity and integrity information to diagnose exactly what was installed.

It does not yet bundle or manage the Python runtime. Runtime sidecar work belongs to P2-11B.

## Delivery boundary

The Windows artifact contains:

```text
LingJi Tauri Desktop application
NSIS current-user installer
Desktop executable copy for inspection
SHA-256 manifest
Build metadata
Installation notes
```

It does not contain:

```text
Python runtime sidecar
Automatic 8766 lifecycle management
Automatic updater
Code-signing certificate
Obsidian Vault
LingJi storage
SQLite databases
Qdrant collections
Ollama models
```

## Installer format

The formal Windows installer target is NSIS.

```text
bundle.targets = ["nsis"]
installMode = "currentUser"
webviewInstallMode = "embedBootstrapper"
```

Current-user installation avoids requiring administrator privileges and installs under the current user's Windows application area.

The embedded WebView2 bootstrapper improves first-install reliability without bundling the full offline WebView2 runtime.

## Build identity

The Rust build embeds:

```text
version
commit
build_time_utc
channel
target
installer_format
signed
```

The values are exported by `src-tauri/build.rs` and returned through the Tauri command:

```text
release_metadata
```

Local builds use safe fallback values such as `development` and `unknown`.

CI builds set the values explicitly.

## Desktop diagnostics

The Desktop sidebar displays:

```text
version
channel
short commit
```

The owner can copy a diagnostic text containing:

```text
product
version
commit
build time
channel
target
installer format
signing state
connection state
control service state
platform
user agent
```

The copied text must not include:

```text
control token
Vault path
storage path
SQLite path
private memory content
```

## Installed credential discovery

The Tauri bridge continues to honor:

```text
LINGJI_CONTROL_TOKEN_FILE
LINGJI_CONTROL_BASE_URL
```

It additionally checks standard owner-local paths:

```text
%LOCALAPPDATA%\LingJi\storage\control_api_token
%APPDATA%\LingJi\storage\control_api_token
%USERPROFILE%\.lingji\storage\control_api_token
```

Repository-relative compatibility paths remain available for development.

P2-11B will become the formal owner of runtime placement and token creation.

## Artifact packaging

`desktop/lingji-control/scripts/package-windows-release.ps1`:

1. reads the formal Tauri version;
2. locates the NSIS installer;
3. locates the compiled Desktop executable;
4. rejects missing or empty artifacts;
5. copies artifacts to a stable release directory;
6. calculates SHA-256 hashes;
7. writes `SHA256SUMS.txt`;
8. writes `build-metadata.json`;
9. writes `INSTALLATION-NOTES.txt`.

Artifact names are stable:

```text
LingJi_<version>_windows_x64_setup.exe
LingJi_<version>_windows_x64.exe
```

## GitHub Actions workflow

Workflow:

```text
.github/workflows/windows-desktop-release.yml
```

Triggers:

```text
pull request to feature/second-brain-memory when Desktop/release files change
manual workflow dispatch
desktop-v* tags
```

Pull requests build and upload an artifact for verification but do not publish a GitHub Release.

Tag builds must match the application version exactly:

```text
desktop-v<tauri.version>
```

The workflow permission remains:

```text
contents: read
```

It cannot create or modify a release.

## Signing truth

P2-11A artifacts are unsigned.

Both embedded metadata and generated metadata state:

```text
signed = false
```

No document or UI may claim that Windows code signing exists until real signing credentials and a verified signing job are added.

## Data preservation

The installer does not bundle owner data and contains no uninstall hook that deletes owner data.

Installing, upgrading or uninstalling the Desktop application must not intentionally delete:

```text
Obsidian Vault
LingJi storage
runtime settings
SQLite state
Qdrant collections
Ollama models
```

P2-11B and P2-11C must preserve this boundary when adding the runtime and updater.

## Changed files

```text
.github/workflows/windows-desktop-release.yml
desktop/lingji-control/src-tauri/tauri.conf.json
desktop/lingji-control/src-tauri/build.rs
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/src/hooks/useReleaseMetadata.ts
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/ReleaseUX.css
desktop/lingji-control/scripts/package-windows-release.ps1
desktop/lingji-control/scripts/windows-release-smoke.mjs
desktop/lingji-control/scripts/run-smoke-suite.mjs
desktop/lingji-control/package.json
```

## Out of scope

This phase does not:

- auto-start 8766;
- package Python;
- install Ollama or Qdrant;
- create a signed public release;
- add automatic updating;
- migrate owner data;
- run production memory mutations;
- close packaged-application interaction issues before owner-machine validation.
