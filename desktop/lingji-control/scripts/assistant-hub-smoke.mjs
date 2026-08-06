import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  types,
  navigation,
  pages,
  hub,
  connectorPanel,
  css,
  importCss,
  captureApi,
  discovery,
  imports,
] = await Promise.all([
  read("../src/types.ts"),
  read("../src/navigation.ts"),
  read("../src/AppPages.tsx"),
  read("../src/pages/AssistantHubPage.tsx"),
  read("../src/components/AssistantConnectorPanel.tsx"),
  read("../src/pages/AssistantHubPage.css"),
  read("../src/pages/AssistantImportFlow.css"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/discovery.py"),
  read("../../../src/assistant_hub/imports.py"),
]);

assert.match(types, /\| "assistant_hub"/);
assert.match(navigation, /id: "assistant_hub"/);
assert.match(navigation, /AI 助手与记忆导入/);
assert.match(pages, /page === "assistant_hub"/);
assert.match(pages, /<AssistantHubPage/);

for (const token of [
  "自动运行观察台",
  "灵机正在主动发现 AI 来源并准备导入",
  "立即重新扫描",
  "一次授权",
  "选择 ChatGPT 官方导出包，选中后立即导入",
  "选择 Codex Work Report，选中后立即导入",
  "/api/assistant-hub/scan",
  "/api/assistant-hub/import-candidates/",
  "/api/assistant-hub/import-selected-file",
  "不需要再次点击提交",
  "不允许 AI 直接写入 Core Memory",
]) assert.ok(hub.includes(token), `Assistant Hub is missing ${token}`);

assert.equal(hub.includes("扫描我的 AI 软件"), false, "Assistant scanning must not be a required primary owner action");
assert.equal(hub.includes("setPaths"), false, "Assistant import must not maintain owner-entered path state");
assert.equal(hub.includes("/api/capture/file"), false, "Assistant Hub must use governed one-action import APIs");
assert.match(hub, /useEffect\(\(\) => \{ void load\(true\); \}, \[load\]\)/);
assert.match(hub, /AUTHORIZE_SELECTED_ASSISTANT_IMPORT/);

for (const token of [
  "配置、命令启动和真实注册分开显示",
  "client_launch_blocked",
  "readiness?.configuration",
  "readiness?.client",
  "readiness?.real_connection",
  "Qdrant 唯一状态来源",
  "semantic_search_available",
]) assert.ok(connectorPanel.includes(token), `Assistant connector panel is missing ${token}`);

for (const token of [
  "/api/assistant-hub/status",
  "/api/assistant-hub/scan",
  "/api/assistant-hub/import-plan",
  "/api/assistant-hub/import-candidates/{candidate_id}/authorize",
  "/api/assistant-hub/import-selected-file",
  "/api/assistant-hub/connections",
  "/api/runtime/ping",
  "binding_contract_version",
  "AssistantImportPlanner",
  "AUTHORIZE_SELECTED_ASSISTANT_IMPORT",
]) assert.ok(captureApi.includes(token), `Assistant Hub API is missing ${token}`);

for (const token of [
  "metadata_only",
  "content_read",
  "arbitrary_path_submission",
  "owner_authorization_required",
  "automatic_core_memory_write",
  "resolve_authorized_candidate",
  "followlinks=False",
]) assert.ok(imports.includes(token), `Assistant import planner is missing ${token}`);

for (const token of [
  "read_only",
  "content_read",
  "automatic_core_memory_write",
  "review_required_for_permanent_memory",
  "CODEX_HOME",
  ".claude",
  "WorkBuddy",
  "followlinks=False",
]) assert.ok(discovery.includes(token), `Assistant discovery is missing ${token}`);

assert.equal(discovery.includes("read_text("), false, "Assistant discovery must not read conversation contents");
assert.equal(discovery.includes("read_bytes("), false, "Assistant discovery must not read conversation bytes");
assert.equal(discovery.includes("rglob("), false, "Assistant discovery must not follow unbounded recursive glob behavior");

for (const cssToken of [
  ".assistant-onboarding-hero",
  ".assistant-setup-flow",
  ".assistant-card-grid",
  ".assistant-connector-grid",
  ".assistant-import-grid",
  ".assistant-memory-policy",
]) assert.ok(css.includes(cssToken), `Assistant Hub styles are missing ${cssToken}`);

for (const cssToken of [
  ".assistant-primary-import",
  ".assistant-import-candidate",
  ".assistant-vector-truth",
]) assert.ok(importCss.includes(cssToken), `Assistant import/status styles are missing ${cssToken}`);

console.log("assistant-hub-smoke: PASS");
