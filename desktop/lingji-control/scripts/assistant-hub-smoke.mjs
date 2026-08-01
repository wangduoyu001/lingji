import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [types, navigation, pages, hub, connectorPanel, css, captureApi, discovery] = await Promise.all([
  read("../src/types.ts"),
  read("../src/navigation.ts"),
  read("../src/AppPages.tsx"),
  read("../src/pages/AssistantHubPage.tsx"),
  read("../src/components/AssistantConnectorPanel.tsx"),
  read("../src/pages/AssistantHubPage.css"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/discovery.py"),
]);

assert.match(types, /\| "assistant_hub"/);
assert.match(navigation, /id: "assistant_hub"/);
assert.match(navigation, /AI 助手与记忆导入/);
assert.match(pages, /page === "assistant_hub"/);
assert.match(pages, /<AssistantHubPage/);

for (const token of [
  "自动运行观察台",
  "灵机正在主动发现和维护 AI 连接",
  "立即重新扫描",
  "等待授权来源",
  "ChatGPT 历史",
  "Codex 工作报告",
  "/api/assistant-hub/scan",
  "/api/capture/file",
  "授权并交给灵机",
  "不允许 AI 直接写入 Core Memory",
]) assert.ok(hub.includes(token), `Assistant Hub is missing ${token}`);

assert.equal(hub.includes("扫描我的 AI 软件"), false, "Assistant scanning must not be a required primary owner action");
assert.match(hub, /useEffect\(\(\) => \{ void load\(true\); \}, \[load\]\)/);
assert.match(hub, /owner_authorized: true/);

for (const token of [
  "连接不等于导入历史",
  "预览并连接",
  "测试连接",
  "断开并回滚",
]) assert.ok(connectorPanel.includes(token), `Assistant connector panel is missing ${token}`);

for (const token of [
  "/api/assistant-hub/status",
  "/api/assistant-hub/scan",
  "/api/assistant-hub/connections",
  "/api/runtime/ping",
  "binding_contract_version",
  "AiAssistantDiscoveryService",
  "AiMemoryConnectorService",
]) assert.ok(captureApi.includes(token), `Assistant Hub API is missing ${token}`);

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

console.log("assistant-hub-smoke: PASS");
