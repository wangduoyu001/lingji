import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = (path) => readFile(resolve(here, path), "utf8");

const [app, shell, boundary, api, connection, navigation, styles, tauri] = await Promise.all([
  source("../src/App.tsx"),
  source("../src/components/DesktopShell.tsx"),
  source("../src/components/RuntimeBoundary.tsx"),
  source("../src/api.ts"),
  source("../src/hooks/useLingJiConnection.ts"),
  source("../src/navigation.ts"),
  source("../src/styles.css"),
  source("../src-tauri/tauri.conf.json"),
]);

assert.match(app, /DesktopShell/);
assert.match(app, /RuntimeBoundary/);
assert.match(boundary, /桌面应用/);
assert.match(boundary, /控制能力只在本机桌面应用开放/);
assert.equal(app.includes("API 地址"), false);
assert.equal(app.includes("connection-panel"), false);
assert.equal(app.includes("setBaseUrl"), false);
assert.equal(app.includes("setToken"), false);
assert.equal(app.includes("浏览器开发模式"), false);
assert.match(shell, /desktop-sidebar/);
assert.match(shell, /desktop-toolbar/);
assert.match(shell, /NavIcon/);
assert.match(shell, /重新连接/);
assert.equal(api.includes("localStorage"), false, "Desktop credentials must not use browser localStorage");
assert.match(api, /isTauriDesktopRuntime/);
assert.match(api, /control_credentials/);
assert.match(connection, /unsupported/);
assert.match(connection, /Tauri 桌面应用/);
assert.match(navigation, /icon:/);
assert.match(styles, /\.desktop-frame/);
assert.match(styles, /\.desktop-sidebar/);
assert.match(styles, /\.desktop-runtime-card/);
assert.match(tauri, /"decorations": true/);
assert.match(tauri, /"theme": "Dark"/);
assert.match(tauri, /"backgroundColor": "#0b0d12"/);

console.log("native-desktop-ui-smoke: PASS");
