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
  memory,
  attention,
  shell,
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
  read("../src/pages/MemoryHomePage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/components/DesktopShell.tsx"),
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

assert.match(autopilotEngine, /auth_status_provider/);
assert.match(autopilotEngine, /auth_permission_insufficient/);
assert.match(autopilotEngine, /auth_reauthentication_required/);
for (const surface of [overview, memory, attention]) {
  assert.equal(/authorization|cookie|control_token/i.test(surface), false, "Daily owner surfaces must not render credential material");
}

// V5 owner contract: Home and Work consume one sanitized WorkItem projection; discovery
// and owner attention remain concrete-object facts rather than inferred activity.
for (const token of [
  "现在需要你吗",
  "刚刚替你做了什么",
  "现在正在做什么",
  "下一步",
  "记忆发生了什么变化",
  "主动发现",
]) assert.ok(overview.includes(token), `V5 home is missing ${token}`);
assert.match(overview, /\/api\/capture\/jobs\?limit=24&offset=0/);
assert.match(overview, /buildOwnerAttentionItems/);
assert.match(overview, /ownerAttentionSummary/);
assert.match(overview, /有 WorkItem 才显示结果/);
assert.match(overview, /发现不等于已授权、已接管或已执行/);
assert.equal(overview.includes("CurrentWorkPanel"), false, "V5 home must not restore the old status-card composition");
assert.equal(overview.includes("queueRoot"), false, "V5 home must not infer work from raw overview queue");

for (const token of ["第二永久记忆大脑", "记住了什么", "为什么能相信它", "来源证据", "记忆缺口"]) {
  assert.ok(memory.includes(token), `Primary memory surface is missing ${token}`);
}
assert.match(memory, /pagination\?\.has_more/);
assert.match(attention, /每个按钮背后都有一个真实对象/);
assert.match(attention, /AUTHORIZE_ASSISTANT_IMPORT_/);
assert.equal(attention.includes("pending_review_count"), false, "Owner inbox must not create actions from a summary count");
assert.match(shell, /第二永久记忆大脑/);
assert.match(shell, /运行与诊断详情/);

assert.match(workFeed, /CaptureJobsResponse/);
assert.match(workFeed, /workItemId/);
assert.match(workFeed, /captureId/);
assert.match(workFeed, /nextActor/);
assert.equal(workFeed.includes("safeRelativePath"), false, "V5 WorkItem identity must not depend on path guessing");
assert.equal(workFeed.includes("payload.text"), false, "Owner projection must not expose captured content");
assert.equal(workFeed.includes("raw_snapshot"), false, "Owner projection must not expose raw snapshot paths");
assert.equal(workFeed.includes("event_type"), false, "Generic events must not become WorkItems");
assert.ok(workflow.includes("sidecar-stop-request.json"), "DMG isolation gate must stop its exact sidecar instance");

console.log("macos-release-smoke: PASS");
