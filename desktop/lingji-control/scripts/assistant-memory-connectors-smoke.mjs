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
  directorCss,
  captureApi,
  connectors,
  governed,
  mcpHttp,
  packaged,
  buildScript,
  sidecarRequirements,
] = await Promise.all([
  read("../src/pages/AssistantHubPage.tsx"),
  read("../src/components/AssistantConnectorPanel.tsx"),
  read("../src/pages/AssistantHubPage.css"),
  read("../src/components/AssistantSetupDirector.css"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/connectors.py"),
  read("../../../src/assistant_hub/governed.py"),
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
  "配置、客户端命令、真实测试分开显示",
  "配置文件存在不等于客户端可用",
  "发现可处理的历史资料",
  "扫描只读元数据；读取正文和导入必须再次确认",
  "Embedding / Qdrant",
  "status_state",
  "blocking_reason",
  "/api/assistant-hub/connections",
  "/api/assistant-hub/status",
  "/api/vector/status",
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

for (const cssToken of [
  ".assistant-setup-director",
  ".assistant-readiness-grid",
  ".assistant-import-consent",
  ".assistant-connector-facts",
  ".assistant-connector-problem",
]) assert.ok(directorCss.includes(cssToken), `Guided setup styles are missing ${cssToken}`);

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
  '_MCP_HOST = "127.0.0.1"',
  "_MCP_PORT = 8767",
  "_MCP_URL",
  "automatic_core_memory_write",
]) assert.ok(connectors.includes(token), `Connector service is missing ${token}`);
assert.equal(connectors.includes("shell=True"), false, "Connector management must not execute shell strings");

for (const token of [
  "status_state",
  "client_available",
  "last_test_detail",
  "配置文件已写入，但系统找不到 codex 命令",
  "last_test_ok",
  'payload.pop("copy_payload", None)',
]) assert.ok(governed.includes(token), `Governed connector truth state is missing ${token}`);

for (const token of [
  "BearerTokenMiddleware",
  "authorization",
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
  '"--collect-submodules", "mcp.server"',
  '"--collect-submodules", "mcp.shared"',
  '"--hidden-import", "mcp.types"',
  '"--exclude-module", "mcp.cli"',
  "contract.mcp.managed",
  "contract.mcp.authentication",
  "contract.mcp.automatic_core_memory_write",
  "mcp_runtime_bundled = $true",
  "mcp_cli_bundled = $false",
]) assert.ok(buildScript.includes(token), `Sidecar builder is missing ${token}`);
assert.equal(buildScript.includes('"--collect-submodules", "mcp",'), false, "Packaging must not import optional MCP CLI modules");
assert.match(sidecarRequirements, /requirements-mcp\.txt/);

console.log("assistant-memory-connectors-smoke: PASS");
