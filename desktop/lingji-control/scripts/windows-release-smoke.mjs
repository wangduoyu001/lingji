import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [tauriText, packageText, cargo, buildRs, rustMain, hook, shell, packager, workflow, sidecarConfigText] = await Promise.all([
  read("../src-tauri/tauri.conf.json"),
  read("../package.json"),
  read("../src-tauri/Cargo.toml"),
  read("../src-tauri/build.rs"),
  read("../src-tauri/src/main.rs"),
  read("../src/hooks/useReleaseMetadata.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("package-windows-release.ps1"),
  read("../../../.github/workflows/windows-desktop-release.yml"),
  read("../src-tauri/tauri.sidecar.conf.json"),
]);

const tauri = JSON.parse(tauriText);
const sidecarConfig = JSON.parse(sidecarConfigText);
const pkg = JSON.parse(packageText);
const cargoVersion = cargo.match(/^version\s*=\s*"([^"]+)"/m)?.[1];

assert.equal(pkg.version, tauri.version, "package.json and Tauri versions must match");
assert.equal(cargoVersion, tauri.version, "Cargo and Tauri versions must match");
assert.deepEqual(tauri.bundle.targets, ["nsis"]);
assert.equal(tauri.bundle.windows.nsis.installMode, "currentUser");
assert.equal(tauri.bundle.windows.webviewInstallMode.type, "embedBootstrapper");
assert.deepEqual(sidecarConfig.bundle.externalBin, ["binaries/lingji-core"]);
assert.equal(sidecarConfig.bundle.resources["binaries/lingji_core_lib"], "lingji_core_lib");

for (const key of [
  "LINGJI_BUILD_COMMIT",
  "LINGJI_BUILD_TIME_UTC",
  "LINGJI_BUILD_CHANNEL",
  "LINGJI_BUILD_TARGET",
  "LINGJI_BUILD_SIGNED",
]) assert.ok(buildRs.includes(key), `build.rs is missing ${key}`);

assert.match(rustMain, /fn release_metadata/);
assert.match(rustMain, /owner_data_root/);
assert.match(rustMain, /runtime_ensure/);
assert.match(rustMain, /runtime_stop/);
assert.match(rustMain, /runtime_restart/);

assert.match(hook, /invoke<ReleaseMetadata>\("release_metadata"\)/);
assert.match(hook, /copyDiagnostics/);
assert.equal(hook.includes("token="), false, "Copied diagnostics must not expose the control token");
assert.equal(hook.includes("vault_path"), false, "Copied diagnostics must not expose Vault paths");
assert.match(shell, /复制诊断信息/);
assert.match(shell, /releaseMetadata\?\.version/);
assert.match(shell, /启动核心/);

for (const token of [
  "Get-FileHash",
  "SHA256SUMS.txt",
  "build-metadata.json",
  "INSTALLATION-NOTES.txt",
  "lingji-core-manifest.json",
  "uninstall_deletes_owner_data = $false",
  "python_sidecar_included = $true",
  "updater_included = $false",
  "signed = $false",
]) assert.ok(packager.includes(token), `Release packager is missing ${token}`);

for (const token of [
  "workflow_dispatch:",
  "tags:",
  '"desktop-v*"',
  "pull_request:",
  "permissions:",
  "contents: read",
  "requirements-sidecar-build.txt",
  "build_windows_sidecar.ps1",
  "Start packaged runtime and verify authenticated health",
  "X-LingJi-Token",
  "src-tauri/tauri.sidecar.conf.json",
  "package-windows-release.ps1",
  "actions/upload-artifact@v7",
  "if-no-files-found: error",
]) assert.ok(workflow.includes(token), `Release workflow is missing ${token}`);

for (const forbidden of [
  "contents: write",
  "gh release create",
  "createRelease:",
  "tauri-apps/tauri-action",
  "LINGJI_CONTROL_TOKEN=",
]) assert.equal(workflow.includes(forbidden), false, `Release workflow must not contain ${forbidden}`);

console.log("windows-release-smoke: PASS");
