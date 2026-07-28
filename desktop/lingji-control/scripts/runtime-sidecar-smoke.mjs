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
  bootstrap,
  manager,
  zeroShell,
  connection,
  runtimeTypes,
  shell,
  boundary,
  acceptancePage,
  releaseHook,
  hardwareSystem,
  hardwareRunner,
] = await Promise.all([
  read("../../../run_packaged_control_api.py"),
  read("../../../tests/test_packaged_control_api.py"),
  read("../../../scripts/build_windows_sidecar.ps1"),
  read("../src-tauri/tauri.sidecar.conf.json"),
  read("../src-tauri/windows/sidecar-hooks.nsh"),
  read("../src-tauri/Cargo.toml"),
  read("../src-tauri/src/main.rs"),
  read("../src-tauri/src/runtime_bootstrap.rs"),
  read("../src-tauri/src/runtime_manager.rs"),
  read("../src-tauri/src/windowless_acceptance.rs"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src/runtimeTypes.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/pages/AcceptancePage.tsx"),
  read("../src/hooks/useReleaseMetadata.ts"),
  read("../../../src/hardware/system_detectors.py"),
  read("../../../src/hardware/runner.py"),
]);

const sidecarConfig = JSON.parse(sidecarConfigText);
assert.deepEqual(sidecarConfig.bundle.externalBin, ["binaries/lingji-core"]);
assert.equal(sidecarConfig.bundle.resources["binaries/lingji_core_lib"], "lingji_core_lib");
assert.equal(sidecarConfig.bundle.windows.nsis.installerHooks, "./windows/sidecar-hooks.nsh");

for (const token of [
  "--data-root", "--workspace", "--check-config", "LINGJI_OWNER_DATA_ROOT",
  "LINGJI_WORKSPACE", "_ensure_standard_streams", "LINGJI_WORKSPACE_ROOT",
  "CONTROL_API_HOST", "127.0.0.1", "owner_data_outside_install_dir",
  "system_drive_runtime_data_allowed", "sidecar-state.json", "sidecar-stop-request.json",
  "install_runtime_lifecycle", "instance_id",
]) assert.ok(entrypoint.includes(token), `Packaged entrypoint is missing ${token}`);
assert.equal(entrypoint.includes('"0.0.0.0"'), false);
assert.match(entrypoint, /target\.setdefault\("VAULT_DIR"/);
assert.match(pythonTests, /rejects_non_loopback_host/);
assert.match(pythonTests, /rejects_filesystem_root/);
assert.match(pythonTests, /rejects_windows_system_drive/);
assert.match(pythonTests, /keeps_production_and_acceptance_separate/);
assert.match(pythonTests, /preserves_explicit_owner_vault/);
assert.match(pythonTests, /matching_stop_request/);
assert.match(pythonTests, /mismatched_stop_request/);

for (const token of [
  "PyInstaller", "--onedir", "--windowed", "--contents-directory", "lingji_core_lib",
  "lingji-core-$TargetTriple.exe", "--check-config", "--check-config-output",
  "LINGJI_SIDECAR_PYTHON", "Start-Process", "-Wait",
  "optional_media_providers_bundled = $false", "Get-FileHash",
]) assert.ok(buildScript.includes(token), `Sidecar builder is missing ${token}`);

assert.match(hooks, /taskkill \/F \/IM lingji-core\.exe/);
assert.match(hooks, /RMDir \/r "\$INSTDIR\\lingji_core_lib"/);
assert.equal(hooks.includes("LingJi\\storage"), false, "Installer hooks must not delete owner storage");
assert.equal(hooks.includes("Obsidian"), false, "Installer hooks must not touch the Vault");
assert.match(cargo, /serde_json = "1"/);

for (const token of [
  "mod runtime_bootstrap", "mod runtime_manager", "mod windowless_acceptance",
  ".manage(RuntimeManager::default())", "runtime_bootstrap_status", "runtime_configure",
  "guarded_runtime_status", "guarded_runtime_ensure", "guarded_runtime_stop",
  "guarded_runtime_restart", "run_windowless_acceptance", "quarantine_inherited_environment",
  "require_configured",
]) assert.ok(rustMain.includes(token), `Rust app is missing ${token}`);

for (const token of [
  "desktop-bootstrap.json", "BOOTSTRAP_SCHEMA_VERSION: u32 = 2", "base_data_root",
  "active_workspace", "owner_confirmed", "production", "acceptance",
  "c_drive_write_detected", "inherited_environment_ignored", "LINGJI_OWNER_DATA_ROOT",
  "LINGJI_WORKSPACE", "env::remove_var(OWNER_DATA_ROOT_ENV)",
  "env::remove_var(WORKSPACE_ENV)", "Stop the current LingJi runtime",
]) assert.ok(bootstrap.includes(token), `Runtime bootstrap is missing ${token}`);
assert.equal(bootstrap.includes("fn environment_status"), false, "Ambient environment must never configure the installed Desktop");
assert.match(bootstrap, /legacy_bootstrap_requires_owner_reconfirmation/);
assert.match(bootstrap, /current_bootstrap_requires_explicit_owner_confirmation/);
assert.match(bootstrap, /write_saved_config/);
assert.match(bootstrap, /json\.bak/);

for (const token of [
  "Command::new(&binary)", "authenticated_health", "/api/runtime/ping", "X-LingJi-Token",
  "STARTUP_ATTEMPTS", "spawn_blocking", "PackagedRuntimeIdentity", "sidecar-state.json",
  "sidecar-stop-request.json", "write_stop_request", "CREATE_NO_WINDOW", "#[cfg(debug_assertions)]",
]) assert.ok(manager.includes(token), `Runtime manager is missing ${token}`);
assert.equal(manager.includes("tauri_plugin_shell"), false, "Runtime manager must not expose general shell execution");
assert.equal(manager.includes("Command::new(command"), false, "Runtime manager must not accept a user command");

for (const forbidden of ["Get-CimInstance", "Get-PhysicalDisk", 'runner.command(["powershell"', 'runner.command(["pwsh"']) {
  assert.equal(hardwareSystem.includes(forbidden), false, `Hardware detection must not invoke ${forbidden}`);
}
for (const token of ["winreg.OpenKey", "ProcessorNameString", "model_source", "return []"]) {
  assert.ok(hardwareSystem.includes(token), `Shell-free hardware detection is missing ${token}`);
}
for (const token of ["CREATE_NO_WINDOW", "STARTF_USESHOWWINDOW", "SW_HIDE"]) {
  assert.ok(hardwareRunner.includes(token), `Windows diagnostic runner is missing ${token}`);
}

for (const token of [
  "CreateToolhelp32Snapshot", "Process32FirstW", "Process32NextW",
  '"powershell.exe"', '"pwsh.exe"', '"cmd.exe"', '"conhost.exe"',
  "OBSERVATION_SECONDS: u64 = 60", "manager.restart(app)", "authenticated_before",
  "authenticated_after", "forbidden_descendants", "external_shell_processes",
  "reports", "desktop-acceptance", "detects_nested_descendants_without_cycles",
]) assert.ok(zeroShell.includes(token), `Zero-shell acceptance is missing ${token}`);
for (const forbidden of ["Command::new", "powershell -", "pwsh -", "wmic", "WMI"])
  assert.equal(zeroShell.includes(forbidden), false, `Zero-shell acceptance must not invoke ${forbidden}`);

for (const command of [
  "runtime_bootstrap_status", "runtime_configure", "guarded_runtime_ensure",
  "guarded_runtime_status", "guarded_runtime_stop", "guarded_runtime_restart",
]) assert.ok(connection.includes(`"${command}"`), `Desktop connection hook is missing ${command}`);
assert.match(connection, /configuration_required/);
assert.match(connection, /runtimeBusy/);
assert.match(connection, /autoRecoveryActive/);
assert.match(connection, /ensureConnection\(false\)/);
assert.match(runtimeTypes, /RuntimeBootstrapStatus/);
assert.match(runtimeTypes, /inherited_environment_ignored/);
assert.match(runtimeTypes, /RuntimeStatus/);
assert.match(runtimeTypes, /runtimeStateLabel/);
assert.match(shell, /desktop-runtime-tools/);
assert.match(shell, /停止核心/);
assert.match(shell, /重启核心/);
assert.match(shell, /data_root_display/);
assert.match(shell, /外部进程/);
assert.match(boundary, /DATA ROOT REQUIRED/);
assert.match(boundary, /保存配置并启动核心/);
assert.match(boundary, /恢复运行/);
assert.match(boundary, /AUTO RECOVERY/);
assert.equal(boundary.includes(">启动核心</button>"), false, "Routine Sidecar startup must remain automatic");

assert.match(acceptancePage, /run_windowless_acceptance/);
assert.match(acceptancePage, /WINDOWLESS_ACCEPTANCE_TIMEOUT_MS/);
assert.match(acceptancePage, /超过 4 分钟/);
assert.match(acceptancePage, /桌面零 Shell 验收/);
assert.match(acceptancePage, /不调用 PowerShell、CMD、WMI 或批处理/);
assert.match(acceptancePage, /外部 Shell/);
assert.match(acceptancePage, /真实 Windows 安装版/);

assert.match(releaseHook, /runtime_data_root/);
assert.match(releaseHook, /system_health/);
assert.match(releaseHook, /vector_rebuild_required/);
assert.match(releaseHook, /c_drive_write_detected/);
assert.match(releaseHook, /inherited_runtime_environment_ignored/);
assert.equal(releaseHook.includes("control_token"), false);

console.log("runtime-sidecar-smoke: PASS");
