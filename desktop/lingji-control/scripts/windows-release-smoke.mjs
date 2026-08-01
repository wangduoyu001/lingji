import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  tauriText,
  packageText,
  cargo,
  buildRs,
  rustMain,
  runtimeBootstrap,
  hook,
  shell,
  boundary,
  packager,
  workflow,
  sidecarConfigText,
  validationScript,
] = await Promise.all([
  read("../src-tauri/tauri.conf.json"),
  read("../package.json"),
  read("../src-tauri/Cargo.toml"),
  read("../src-tauri/build.rs"),
  read("../src-tauri/src/main.rs"),
  read("../src-tauri/src/runtime_bootstrap.rs"),
  read("../src/hooks/useReleaseMetadata.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("package-windows-release.ps1"),
  read("../../../.github/workflows/windows-desktop-release.yml"),
  read("../src-tauri/tauri.sidecar.conf.json"),
  read("../../../scripts/validate.ps1"),
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

assert.match(rustMain, /^#!\[cfg_attr\(not\(debug_assertions\), windows_subsystem = "windows"\)\]/m);
for (const token of [
  "fn release_metadata",
  "runtime_bootstrap_status",
  "runtime_binding_verification",
  "runtime_auto_configure",
  "require_verified_runtime",
  "startup_contract_requested",
  "initialize_runtime_binding",
  "guarded_runtime_ensure",
  "guarded_runtime_stop",
  "guarded_runtime_restart",
]) assert.ok(rustMain.includes(token), `Tauri entrypoint is missing ${token}`);
assert.match(rustMain, /if runtime_bootstrap::startup_contract_requested\(\)/);
assert.match(rustMain, /apply_startup_contract/);
assert.match(rustMain, /else \{\s*let _ = runtime_bootstrap::apply_saved_environment\(\)/s);

for (const token of [
  "LINGJI_BOOTSTRAP_CONTRACT_FILE",
  "binding_locked",
  "startup_contract",
  "automatic_safe_default",
  "verify_runtime_binding",
  "require_verified_runtime",
  "automatic_base_candidates",
  "binding_contract_version",
  "ping_matches",
  "startup_contract_requested",
  "Automatic DataRoot selection is disabled while a startup contract is requested",
  "Runtime identity contract, DataRoot or workspace did not match",
]) assert.ok(runtimeBootstrap.includes(token), `Runtime bootstrap is missing ${token}`);
assert.match(runtimeBootstrap, /runtime_ping_requires_current_identity_contract/);
assert.match(runtimeBootstrap, /runtime_ping_rejects_wrong_root_or_workspace/);
assert.equal(
  /startup_contract_requested\(\)[\s\S]*?apply_saved_environment\(\)/.test(runtimeBootstrap),
  false,
  "Saved bootstrap must not be applied from inside a requested startup-contract path",
);

assert.match(hook, /invoke<ReleaseMetadata>\("release_metadata"\)/);
assert.match(hook, /copyDiagnostics/);
assert.equal(hook.includes("token="), false, "Copied diagnostics must not expose the control token");
assert.equal(hook.includes("vault_path"), false, "Copied diagnostics must not expose Vault paths");
assert.match(shell, /复制诊断信息/);
assert.match(shell, /releaseMetadata\?\.version/);
assert.match(shell, /desktop-runtime-tools/);
assert.match(boundary, /LINGJI AUTOPILOT/);
assert.match(boundary, /MANUAL FALLBACK/);
assert.match(boundary, /灵机没有找到可自动使用的非 C 盘目录/);
assert.match(boundary, /恢复运行/);
assert.equal(boundary.includes(">启动核心</button>"), false, "Routine installed startup must remain automatic");

for (const token of [
  "schema_version = 5",
  "Get-PeSubsystem",
  "desktop_pe_subsystem = \"windows_gui\"",
  "sidecar_pe_subsystem = \"windows_gui\"",
  "bootstrap_config = \"%LOCALAPPDATA%\\LingJi\\desktop-bootstrap.json\"",
  "bootstrap_config_contains_runtime_data = $false",
  "owner_data_root = \"startup-contract-or-automatic-non-system-drive\"",
  "workspace_profiles = @(\"production\", \"acceptance\")",
  "first_run_configuration_required = $false",
  "automatic_safe_non_system_drive_selection = $true",
  "startup_binding_contract_supported = $true",
  "runtime_binding_identity_required = $true",
  "external_runtime_adoption_allowed = $false",
  "owner_authorization_required_for_real_content = $true",
  "c_drive_runtime_data_allowed = $false",
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
assert.equal(
  packager.includes('owner_data_root = "%LOCALAPPDATA%\\LingJi"'),
  false,
  "Release metadata must not claim LocalAppData is the Runtime data root",
);
assert.match(packager, /automatically selects the first writable non-C drive/);
assert.match(packager, /LINGJI_BOOTSTRAP_CONTRACT_FILE/);
assert.match(packager, /actual DataRoot and workspace/);

for (const token of [
  "FailureTailLines = 40",
  "$ErrorActionPreference = \"Continue\"",
  "$global:LASTEXITCODE = 0",
  "latest-summary.json",
  "native-stderr-warning-contract",
  "Remove-StaleValidationRuns",
]) assert.ok(validationScript.includes(token), `Validation entry is missing ${token}`);

for (const token of [
  "workflow_dispatch:",
  "tags:",
  '"desktop-v*"',
  "pull_request:",
  "permissions:",
  "contents: read",
  "requirements-sidecar-build.txt",
  "build_windows_sidecar.ps1",
  "Test Rust runtime manager",
  "Verify authenticated health and managed stop",
  "sidecar-stop-request.json",
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
