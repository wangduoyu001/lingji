import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [macConfigText, packageText, buildScript, rustMain, sidecarConfigText] = await Promise.all([
  read("../src-tauri/tauri.macos.conf.json"),
  read("../package.json"),
  read("../../../scripts/build_macos_sidecar.sh"),
  read("../src-tauri/src/main.rs"),
  read("../src-tauri/tauri.sidecar.conf.json"),
]);

const macConfig = JSON.parse(macConfigText);
const pkg = JSON.parse(packageText);
const sidecarConfig = JSON.parse(sidecarConfigText);

assert.deepEqual(macConfig.bundle.targets, ["dmg"]);
assert.equal(
  macConfig.bundle.resources["binaries/lingji-core-aarch64-apple-darwin"],
  "lingji-core.exe",
);
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
]) {
  assert.ok(buildScript.includes(token), `macOS sidecar builder is missing ${token}`);
}

for (const token of [
  '#[cfg(target_os = "macos")]',
  'join("Library").join("Application Support")',
  'env::set_var("LOCALAPPDATA", app_support)',
  'return "dmg"',
  "prepare_platform_environment();",
]) {
  assert.ok(rustMain.includes(token), `macOS desktop shim is missing ${token}`);
}

console.log("macos-release-smoke: PASS");
