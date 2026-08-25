# P2-10B Native Desktop UI

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Turn the LingJi control center into a desktop-first Tauri application instead of a browser-like administration page.

The product may still use Tauri's embedded webview as its rendering engine, but the owner-facing experience must not depend on:

- opening a browser;
- typing a localhost URL;
- manually pasting a control token;
- browser localStorage;
- browser routing;
- browser-only connection panels.

## Desktop runtime contract

The formal application starts from Tauri.

```text
Tauri desktop process
-> Rust control_credentials command
-> local control token file
-> authenticated 127.0.0.1:8766 API
-> React desktop shell
```

When opened outside Tauri, the UI displays a desktop-only boundary screen and does not expose a browser control surface.

## Credential boundary

`desktop/lingji-control/src/api.ts` no longer reads or writes browser localStorage.

The Desktop obtains credentials through:

```text
src-tauri/src/main.rs::control_credentials
```

The token remains local and is not displayed in the interface.

## Application shell

New components:

```text
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/components/NavIcon.tsx
```

The shell owns:

- product identity;
- grouped navigation;
- current page hierarchy;
- local connection state;
- desktop retry action;
- content scrolling boundary.

Page implementations remain in `AppPages.tsx` and are not duplicated.

## Navigation

Navigation metadata now contains a stable icon key. Icons are dependency-free inline SVG so the Desktop does not add a third-party icon package merely to draw twenty small symbols.

Navigation remains grouped as:

```text
总览
记忆与项目
采集与处理
模型与运行
运维与设置
```

## Connection states

The Desktop explicitly models:

```text
booting
connected
offline
unsupported
```

- `booting`: reading local credentials and checking 8766.
- `connected`: local authenticated control service is available.
- `offline`: Tauri is running but the local service or credentials are unavailable.
- `unsupported`: the interface was opened outside Tauri.

The previous API address and token form has been removed.

## Visual system

`src/styles.css` is the shared Desktop visual system.

It defines:

- application surfaces;
- sidebar and navigation states;
- toolbar hierarchy;
- status colors;
- panels and metrics;
- forms and buttons;
- tables and logs;
- settings layout;
- responsive behavior inside the resizable desktop window.

`src/DesktopUX.css` contains page-specific layout refinements.

The visual direction is a restrained local control application, not a marketing site and not a browser admin template.

## Overview hierarchy

`OverviewPage.tsx` now separates:

```text
System Posture
Core Runtime
Model / Compute / Storage
Health Checks
Local Providers
Scheduled Jobs
```

Unknown and stale values continue to preserve the truthful runtime contracts introduced in P2-09.

## Tauri window

The formal window uses native operating-system decorations and a dark window theme.

Configured defaults:

```text
1480 x 940
minimum 980 x 680
centered
resizable
native decorations enabled
dark theme
```

Using native decorations avoids reimplementing window movement, resizing and operating-system controls inside page code.

## Security and architecture

Unchanged:

- Desktop talks only to authenticated 8766.
- Desktop does not access SQLite, Qdrant or Ollama directly.
- No database schema changes.
- No new configuration store.
- No new token file.
- No browser credential persistence.
- Auto Review remains OFF/SHADOW only.
- `second_brain/` is not modified.

## Changed files

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/api.ts
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/styles.css
desktop/lingji-control/src/DesktopUX.css
desktop/lingji-control/src/components/DesktopShell.tsx
desktop/lingji-control/src/components/NavIcon.tsx
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src-tauri/tauri.conf.json
```

## Out of scope

This phase does not:

- replace Tauri with a fully native Rust widget toolkit;
- auto-install or auto-start Python services;
- redesign every individual feature page;
- add cloud login;
- add a browser-accessible control panel;
- expose the local token to the owner interface.

Further page-by-page refinement must reuse this shell and visual system instead of creating another UI framework.
