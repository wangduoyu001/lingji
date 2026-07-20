import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../src/pages/MemoryInspectorPage.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");
const navigation = readFileSync(new URL("../src/navigation.ts", import.meta.url), "utf8");
const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

for (const endpoint of [
  "/api/memory/inspector/status",
  "/api/memory/inspector/sources",
  "/api/memory/inspector/conversations",
  "/api/memory/inspector/messages",
  "/api/memory/inspector/memories/",
]) assert.ok(page.includes(endpoint), `missing endpoint ${endpoint}`);

assert.ok(page.includes("LIMIT = 30"), "server pagination limit must remain bounded");
assert.ok(page.includes("setTimeout") && page.includes("300"), "keyword search must be debounced");
assert.ok(page.includes("AbortController") && page.includes("requestId"), "stale request protection is required");
assert.ok(page.includes("需要本地授权或 Token 配置"), "401 state missing");
assert.ok(page.includes("结构化读取模型暂不可用"), "503 state missing");
assert.ok(page.includes("需要重建") && page.includes("无需重建") && page.includes("未知"), "tri-state rebuild labels missing");
assert.ok(page.includes("restricted 受限内容，主动展开"), "restricted content must be collapsed");
assert.ok(api.includes("ApiError") && api.includes("timeoutMs") && api.includes("signal"), "API error/timeout/cancellation contract missing");
assert.ok(navigation.includes("memory_inspector") && app.includes("<MemoryInspectorPage"), "page routing missing");

console.log("memory-inspector-smoke: PASS");
