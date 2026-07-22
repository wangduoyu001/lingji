import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  entrypoint,
  pythonTests,
  buildScript,
  sidecarConfigText,
  hooks,
  cargo,
  rustMain,
  manager,
  connection,
  runtimeTypes,
  shell,
  releaseHook,
] = await Promise.all([
  read("../../../run_packaged_control_api.py"),
  read("../../../tests/test_packaged_control_api.py"),
  read("../../../scripts/build_windows_sidecar.ps1"),
  read("../src-tauri/tauri.sidecar.conf.json"),
  read("../src-tauri/windows/sidecar-hooks.nsh"),
  read("../src-tauri/Cargo.toml"),
  read("../src-tauri/src/main.rs"),
  read("../src-tauri/src/runtime_manager.rs"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src/runtimeTypes.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/hooks/useReleaseMetadata.ts"),
]);

const sidecarConfig = JSON.parse(sidecarConfigText);
assert.deepEqual(sidecarConfig.bundle.externalBin, ["binaries/lingji-core"]);
assert.equal(sidecarConfig.bundle.resources["binaries/lingji_core_lib"], "lingji_core_lib");
assert.equal(sidecarConfig.bundle.windows.nsis.installerHooks, "./windows/sidecar-hooks.nsh");

for (const token of [
  "--data-root",
  "--check-config",
  "LINGJI_OWNER_DATA_ROOT",
  "LINGJI_WORKSPACE_ROOT",
  "CONTROL_API_HOST",
  "127.0.0.1",
  "owner_data_outside_install_dir",
  "sidecar-state.json",
  "sidecar-stop-request.json",
  "install_runtime_lifecycle",
  "instance_id",
]) assert.ok(entrypoint.includes(token), `Packaged entrypoint is missing ${token}`);
assert.equal(entrypoint.includes('"0.0.0.0"'), false);
assert.match(entrypoint, /target\.setdefault\("VAULT_DIR"/);
assert.match(pythonTests, /rejects_non_loopback_host/);
assert.match(pythonTests, /rejects_filesystem_root/);
assert.match(pythonTests, /preserves_explicit_owner_vault/);
assert.match(pythonTests, /matching_stop_request/);
assert.match(pythonTests, /mismatched_stop_request/);

for (const token of [
  "PyInstaller",
  "--onedir",
  "--contents-directory",
  "lingji_core_lib",
  "lingji-core-$TargetTriple.exe",
  "--check-config",
  "optional_media_providers_bundled = $false",
  "Get-FileHash",
]) assert.ok(buildScript.includes(token), `Sidecar builder is missing ${token}`);

assert.match(hooks, /taskkill \/F \/IM lingji-core\.exe/);
assert.match(hooks, /RMDir \/r "\$INSTDIR\\lingji_core_lib"/);
assert.equal(hooks.includes("LingJi\\storage"), false, "Installer hooks must not delete owner storage");
assert.equal(hooks.includes("Obsidian"), false, "Installer hooks must not touch the Vault");
assert.match(cargo, /serde_json = "1"/);

for (const token of [
  "mod runtime_manager",
  ".manage(RuntimeManager::default())",
  "runtime_status",
  "runtime_ensure",
  "runtime_stop",
  "runtime_restart",
]) assert.ok(rustMain.includes(token), `Rust app is missing ${token}`);

for (const token of [
  "Command::new(&binary)",
  "authenticated_health",
  "X-LingJi-Token",
  "STARTUP_ATTEMPTS",
  "spawn_blocking",
  "PackagedRuntimeIdentity",
  "sidecar-state.json",
  "sidecar-stop-request.json",
  "write_stop_request",
  "The healthy 8766 service was started outside this Desktop and will not be stopped",
  "The healthy 8766 service is external and cannot be restarted",
  "CREATE_NO_WINDOW",
  "#[cfg(debug_assertions)]",
]) assert.ok(manager.includes(token), `Runtime manager is missing ${token}`);
assert.equal(manager.includes("tauri_plugin_shell"), false, "Runtime manager must not expose general shell execution");
assert.equal(manager.includes("Command::new(command"), false, "Runtime manager must not accept a user command");

for (const command of ["runtime_ensure", "runtime_status", "runtime_stop", "runtime_restart"]) {
  assert.ok(connection.includes(`"${command}"`), `Desktop connection hook is missing ${command}`);
}
assert.match(connection, /runtimeBusy/);
assert.match(runtimeTypes, /RuntimeStatus/);
assert.match(runtimeTypes, /runtimeStateLabel/);
assert.match(shell, /启动核心/);
assert.match(shell, /停止核心/);
assert.match(shell, /重启核心/);
assert.match(shell, /外部进程/);
assert.match(releaseHook, /runtime_data_root/);
assert.match(releaseHook, /runtime_log/);
assert.equal(releaseHook.includes("control_token"), false);

console.log("runtime-sidecar-smoke: PASS");
