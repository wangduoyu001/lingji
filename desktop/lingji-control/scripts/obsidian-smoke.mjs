import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const root = new URL("../", import.meta.url);
const repo = new URL("../../../", import.meta.url);
const page = readFileSync(new URL("src/pages/ObsidianPage.tsx", root), "utf8");
const routes = readFileSync(new URL("src/AppPages.tsx", root), "utf8");
const navigation = readFileSync(new URL("src/navigation.ts", root), "utf8");
const types = readFileSync(new URL("src/types.ts", root), "utf8");
const api = readFileSync(new URL("src/control/obsidian_api.py", repo), "utf8");
const service = readFileSync(new URL("src/obsidian/service.py", repo), "utf8");
const compatibility = readFileSync(new URL("second_brain/obsidian_cli.py", repo), "utf8");

assert.ok(navigation.includes('id: "obsidian"'));
assert.ok(routes.includes("<ObsidianPage"));
assert.ok(types.includes("export type ObsidianStatus"));

for (const endpoint of [
  "/api/obsidian/status",
  "/api/obsidian/validate",
  "/api/obsidian/refresh",
]) {
  assert.ok(page.includes(endpoint), `page missing endpoint ${endpoint}`);
  assert.ok(api.includes(endpoint), `backend missing endpoint ${endpoint}`);
}

for (const key of [
  "obsidian_cli_enabled",
  "obsidian_cli_path",
  "obsidian_vault_path",
  "obsidian_vault_name",
  "obsidian_cli_timeout_seconds",
  "obsidian_cli_dry_run",
]) assert.ok(page.includes(key), `missing setting ${key}`);

assert.ok(page.includes('@tauri-apps/plugin-dialog'));
assert.ok(page.includes('directory: kind === "vault"'));
assert.ok(page.includes("验证但不保存"));
assert.ok(page.includes("兼容层"));
assert.ok(service.includes("display_path(config.cli_path)"));
assert.ok(service.includes("display_path(config.vault_path)"));
assert.ok(!service.includes('"cli_path": config.cli_path'));
assert.ok(!service.includes('"vault_path": config.vault_path'));
assert.ok(compatibility.includes("from src.obsidian import"));
assert.ok(!compatibility.includes("def _run("));

console.log("obsidian-smoke: PASS");
