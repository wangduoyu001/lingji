import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [types, navigation, pages, hub, css, captureApi, discovery] = await Promise.all([
  read("../src/types.ts"),
  read("../src/navigation.ts"),
  read("../src/AppPages.tsx"),
  read("../src/pages/AssistantHubPage.tsx"),
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
  "扫描我的 AI 软件",
  "第一次使用从这里开始",
  "连接不等于导入历史",
  "ChatGPT 历史",
  "Codex 工作报告",
  "/api/assistant-hub/scan",
  "/api/capture/file",
  "进入人工记忆审核",
  "不允许 AI 直接写入 Core Memory",
]) assert.ok(hub.includes(token), `Assistant Hub is missing ${token}`);

for (const token of [
  "/api/assistant-hub/status",
  "/api/assistant-hub/scan",
  "/api/assistant-hub/connections",
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
