import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  macConfigText,
  packageText,
  buildScript,
  rustMain,
  bootstrap,
  sidecarConfigText,
  workflow,
  runtimeBoundary,
  overview,
  workFeed,
  autopilotEngine,
] = await Promise.all([
  read("../src-tauri/tauri.macos.conf.json"),
  read("../package.json"),
  read("../../../scripts/build_macos_sidecar.sh"),
  read("../src-tauri/src/main.rs"),
  read("../src-tauri/src/runtime_bootstrap.rs"),
  read("../src-tauri/tauri.sidecar.conf.json"),
  read("../../../.github/workflows/macos-desktop-gate.yml"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/ownerWorkFeed.ts"),
  read("../../../src/autopilot/engine.py"),
]);

const macConfig = JSON.parse(macConfigText);
const pkg = JSON.parse(packageText);
const sidecarConfig = JSON.parse(sidecarConfigText);

assert.deepEqual(macConfig.bundle.targets, ["dmg"]);
assert.equal(macConfig.bundle.resources["binaries/lingji-core-aarch64-apple-darwin"], "lingji-core.exe");
assert.equal(macConfig.bundle.macOS.signingIdentity, "-");
assert.deepEqual(sidecarConfig.bundle.externalBin, ["binaries/lingji-core"]);

assert.match(pkg.scripts["build:sidecar:macos"], /build_macos_sidecar\.sh aarch64-apple-darwin/);
assert.match(pkg.scripts["release:macos"], /--bundles dmg/);
assert.match(pkg.scripts["release:macos"], /--target aarch64-apple-darwin/);

for (const token of [
  "aarch64-apple-darwin",
  "PyInstaller",
  "--onedir",
  "lingji_core_lib",
  "platform.machine()",
  "Do not build the M5 sidecar through Rosetta",
  "--check-config",
  "owner_data_outside_install_dir",
]) assert.ok(buildScript.includes(token), `macOS sidecar builder is missing ${token}`);

for (const token of [
  '#[cfg(target_os = "macos")]',
  'join("Library").join("Application Support")',
  'env::set_var("LOCALAPPDATA", app_support)',
  'return "dmg"',
  "prepare_platform_environment();",
  "runtime_autoconfigure",
  "configure_default()",
  "SubmenuBuilder",
  '"窗口"',
  '"将灵机带到当前屏幕"',
  'CmdOrCtrl+Shift+L',
  "tauri::RunEvent::Reopen",
]) assert.ok(rustMain.includes(token), `macOS desktop bootstrap/window contract is missing ${token}`);

for (const token of [
  "LINGJI_ACCEPTANCE_DATA_ROOT",
  "automatic_default",
  "auto_selected",
  "persisted acceptance workspace is never reused",
  'join("LingJiData")',
]) assert.ok(bootstrap.includes(token), `macOS autopilot bootstrap is missing ${token}`);

for (const token of [
  "Checkout exact product source",
  "github.event.pull_request.head.sha || github.sha",
  "Verify exact source identity",
  "Verify embedded product identity",
  "--release-metadata-output",
  "release_metadata.json",
  "Verify installed App acceptance isolation",
  "LINGJI_ACCEPTANCE_DATA_ROOT=\"$TASK_ROOT/runtime-data\"",
  "isolated-home",
]) assert.ok(workflow.includes(token), `macOS release identity contract is missing ${token}`);

assert.match(rustMain, /release_metadata_output_path/);
assert.match(rustMain, /--release-metadata-output/);
assert.match(runtimeBoundary, /<details className="runtime-advanced-setup">[\s\S]*手动选择位置/);
assert.equal(
  runtimeBoundary.match(/<div className="toolbar runtime-fallback-actions">[\s\S]*?<\/div>/)?.[0].includes("手动选择位置"),
  false,
  "manual data-root selection must be an advanced fallback, not a first-run action",
);

// Daily home consumes sanitized projections only. Auth state still feeds the bounded
// Autopilot classifier and credential material never belongs on the owner surface.
assert.match(autopilotEngine, /auth_status_provider/);
assert.match(autopilotEngine, /auth_permission_insufficient/);
assert.match(autopilotEngine, /auth_reauthentication_required/);
assert.equal(/token|authorization|cookie/i.test(overview), false, "Daily home must not render credential material");
assert.match(overview, /你现在需要做什么/);
assert.match(overview, /资料工作清单/);
assert.match(overview, /灵机已做/);
assert.match(overview, /下一步/);
assert.match(workFeed, /safeRelativePath/);
assert.equal(workFeed.includes("payload.text"), false, "Owner projection must not expose captured content");
assert.equal(workFeed.includes("raw_snapshot"), false, "Owner projection must not expose raw snapshot paths");

assert.ok(workflow.includes("sidecar-stop-request.json"), "DMG isolation gate must stop its exact sidecar instance");

console.log("macos-release-smoke: PASS");
