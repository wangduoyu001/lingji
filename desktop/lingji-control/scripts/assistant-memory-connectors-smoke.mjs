import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  hub,
  panel,
  css,
  captureApi,
  connectors,
  mcpHttp,
  packaged,
  buildScript,
  sidecarRequirements,
] = await Promise.all([
  read("../src/pages/AssistantHubPage.tsx"),
  read("../src/components/AssistantConnectorPanel.tsx"),
  read("../src/pages/AssistantHubPage.css"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/connectors.py"),
  read("../../../src/mcp_http.py"),
  read("../../../run_packaged_control_api.py"),
  read("../../../scripts/build_windows_sidecar.ps1"),
  read("../../../requirements-sidecar-build.txt"),
]);

for (const token of [
  "扫描",
  "连接",
  "导入",
  "审核",
  "AssistantConnectorPanel",
  "不允许 AI 直接写入 Core Memory",
]) assert.ok(hub.includes(token), `Assistant workflow is missing ${token}`);

for (const token of [
  "连接不等于导入历史",
  "/api/assistant-hub/connections",
  "/preview",
  "/apply",
  "/test",
  "/rollback",
  "预览并连接",
  "测试连接",
  "断开并回滚",
  "本机 127.0.0.1:8767",
  "Bearer Token 认证",
  "配置已复制到剪贴板",
]) assert.ok(panel.includes(token), `Connector panel is missing ${token}`);

for (const cssToken of [
  ".assistant-connector-section",
  ".assistant-runtime-card",
  ".assistant-connector-grid",
  ".assistant-connector-card",
  ".assistant-connector-preview",
  ".assistant-preview-close",
]) assert.ok(css.includes(cssToken), `Connector styles are missing ${cssToken}`);

for (const route of [
  "/api/assistant-hub/connections",
  "/api/assistant-hub/connections/{connector_id}/preview",
  "/api/assistant-hub/connections/{connector_id}/apply",
  "/api/assistant-hub/connections/{connector_id}/test",
  "/api/assistant-hub/connections/{connector_id}/rollback",
]) assert.ok(captureApi.includes(route), `Connector API is missing ${route}`);
assert.match(captureApi, /Depends\(authorize\)/);
assert.match(captureApi, /ConnectorActionRequest/);

for (const token of [
  "CONNECT_CODEX_TO_LINGJI",
  "CONNECT_CLAUDE_TO_LINGJI",
  "COPY_WORKBUDDY_LINGJI_CONFIG",
  "DISCONNECT_",
  "connector_backups",
  "CONFIG_CONFLICT",
  "tomllib.loads",
  "CREATE_NO_WINDOW",
  "127.0.0.1:8767/mcp",
  "automatic_core_memory_write",
]) assert.ok(connectors.includes(token), `Connector service is missing ${token}`);
assert.equal(connectors.includes("shell=True"), false, "Connector management must not execute shell strings");

for (const token of [
  "BearerTokenMiddleware",
  "Authorization",
  "Bearer",
  "401",
  "streamable_http_app",
  "127.0.0.1",
]) assert.ok(mcpHttp.includes(token), `Authenticated MCP runtime is missing ${token}`);
assert.equal(mcpHttp.includes('host="0.0.0.0"'), false, "MCP runtime must remain loopback-only");

for (const token of [
  "--service",
  '"mcp"',
  "--parent-pid",
  "mcp-state.json",
  "mcp_http_token",
  "_start_managed_mcp_process",
  "CREATE_NO_WINDOW",
  "streamable-http",
  "automatic_core_memory_write",
]) assert.ok(packaged.includes(token), `Packaged runtime is missing ${token}`);

for (const token of [
  '"--collect-submodules", "mcp"',
  "contract.mcp.managed",
  "contract.mcp.authentication",
  "contract.mcp.automatic_core_memory_write",
  "mcp_runtime_bundled = $true",
]) assert.ok(buildScript.includes(token), `Sidecar builder is missing ${token}`);
assert.match(sidecarRequirements, /requirements-mcp\.txt/);

console.log("assistant-memory-connectors-smoke: PASS");
