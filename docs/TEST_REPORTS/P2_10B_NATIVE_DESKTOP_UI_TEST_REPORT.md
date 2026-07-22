# P2-10B Native Desktop UI Test Report

## Environment

Implementation was performed through the writable GitHub connector on branch:

```text
work/p2-10b-native-desktop-ui
```

No local Windows, packaged Tauri application, browser or Node runtime was attached to this conversation. Executable evidence comes from GitHub Actions. Packaged-application interaction checks remain an owner-machine verification item.

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

The Auto Review smoke now checks grouped-navigation ownership in `DesktopShell` rather than requiring navigation implementation details to remain in `App.tsx`.

## GitHub Actions results

Validated implementation head:

```text
eda286679830cecc979a5db04747a8b9c1c3053e
```

Workflow results:

```text
tests #715: SUCCESS
P0 Windows Gate #105: SUCCESS
```

Passed gates:

```text
Python 3.11 unit tests: SUCCESS
Python 3.12 unit tests: SUCCESS
Windows compile and full tests: SUCCESS
clean-install contract validation: SUCCESS
full Python entry-point compile: SUCCESS
15-script Desktop smoke suite: SUCCESS
React / TypeScript / Vite production build: SUCCESS
Tauri Rust cargo check: SUCCESS
MCP smoke: SUCCESS
Browser capture smoke: SUCCESS
Obsidian plugin smoke: SUCCESS
```

Browser capture smoke is unrelated to the Desktop rendering surface. It validates the existing optional capture extension and does not make the Desktop browser-dependent.

## Manual owner checks still required

CI validates code, contracts, builds and Rust compilation. It does not prove physical interaction with the packaged application on the owner's Windows machine.

Remaining checks:

1. Launch the packaged Tauri application and verify no browser window is required.
2. Verify the operating-system titlebar, resize and minimize/maximize behavior.
3. Verify the app opens centered at the configured size.
4. Verify credentials are loaded without displaying a token field.
5. Stop 8766 and verify the offline banner and reconnect action.
6. Restart 8766 and verify reconnect restores the overview.
7. Open the frontend development URL in a browser and verify the desktop-only boundary screen appears.
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
CI_VALIDATED_AWAITING_OWNER_PACKAGED_APP_CHECK
```
