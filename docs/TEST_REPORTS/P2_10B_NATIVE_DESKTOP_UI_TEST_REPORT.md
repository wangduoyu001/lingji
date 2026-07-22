# P2-10B Native Desktop UI Test Report

## Environment

Implementation was performed through the writable GitHub connector on branch:

```text
work/p2-10b-native-desktop-ui
```

No local Windows, Tauri, browser or Node runtime is attached to this conversation. Executable evidence must come from GitHub Actions.

## New smoke contract

```text
desktop/lingji-control/scripts/native-desktop-ui-smoke.mjs
```

It verifies:

- `DesktopShell` is the application shell;
- browser API/token controls are absent;
- browser localStorage is not used for credentials;
- credentials come from the Tauri `control_credentials` command;
- unsupported browser runtime is explicit;
- grouped navigation has stable icons;
- desktop sidebar, toolbar and runtime cards exist;
- native Tauri decorations remain enabled;
- the Tauri window uses a dark theme and fixed background color.

The test is registered in the full Desktop smoke suite.

## Existing smoke updates

`ui-modular-smoke.mjs` now also requires:

```text
src/components/DesktopShell.tsx
src/components/NavIcon.tsx
```

It continues to verify all formal pages, settings governance, runtime pages and modular App size.

## Build gates required

The pull request must pass:

```text
npm ci
npm run test:smoke
npm run build
cargo check
Python 3.11 tests
Python 3.12 tests
Windows full tests
MCP smoke
Browser capture smoke
Obsidian plugin smoke
```

Browser capture smoke is unrelated to the Desktop rendering surface. It validates the existing optional capture extension and does not make the Desktop browser-dependent.

## Manual owner checks after CI

1. Launch the packaged Tauri application and verify no browser window is required.
2. Verify the operating-system titlebar, resize and minimize/maximize behavior.
3. Verify the app opens centered at the configured size.
4. Verify credentials are loaded without displaying a token field.
5. Stop 8766 and verify the offline banner and reconnect action.
6. Restart 8766 and verify reconnect restores the overview.
7. Open the same frontend URL in a browser and verify the desktop-only boundary screen appears.
8. Resize to the minimum window size and verify sidebar, overview and settings remain usable.
9. Verify navigation icons and active state are clear without relying on color alone.
10. Verify stale and unknown runtime values remain truthful.

## Data and authority impact

```text
Database schema changed: no
New settings store: no
New credentials store: no
Browser localStorage credentials: removed
Production Vault mutation: no
Production Qdrant mutation: no
Production Ollama mutation: no
Auto Review ACTIVE: no
second_brain changes: no
```

## Status

```text
TESTS_ADDED_AWAITING_GITHUB_ACTIONS
```
