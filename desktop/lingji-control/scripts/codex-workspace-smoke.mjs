import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("../src/pages/CodexWorkspacePage.tsx", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../src/pages/codexWorkspaceApi.ts", import.meta.url), "utf8");
const nav = fs.readFileSync(new URL("../src/navigation.ts", import.meta.url), "utf8");
const contract = fs.readFileSync(new URL("../src/pages/codexWorkspaceContract.ts", import.meta.url), "utf8");
const dashboard = fs.readFileSync(new URL("../src/components/CurrentWorkPanel.tsx", import.meta.url), "utf8");

assert.match(nav, /codex_workspace/);
for (const path of ["/api/codex/projects/resolve", "/api/codex/projects", "/api/codex/current", "/api/codex/sessions", "/api/activity", "/api/context/project"]) assert.ok(api.includes(path), path);
assert.match(dashboard, /当前项目/); assert.match(dashboard, /Codex 工作记录/); assert.match(dashboard, /无活动记录/); assert.match(dashboard, /未绑定/);
assert.match(page, /Codex 工作记录/); assert.match(page, /工作记录详情/); assert.match(page, /不是灵机新建了聊天窗口/);
assert.doesNotMatch(page, /transcript/i); assert.doesNotMatch(page, /absolute_path|input_path/);
assert.match(api, /after_id=/); assert.match(contract, /ACTIVE_POLL_MS = 1000/); assert.match(contract, /IDLE_POLL_MS = 5000/);
assert.match(page, /document\.hidden/); assert.match(page, /visibilitychange/);
assert.match(page, /AbortController/); assert.match(page, /listRequestId/); assert.match(page, /activityRequestId/);
assert.match(page, /Context Pack/); assert.match(page, /navigator\.clipboard\.writeText\(contextPack\.markdown\)/);
assert.match(page, /progress_current/); assert.match(page, /progress_total/);
assert.match(page, /查看这条记录如何进入记忆/);
console.log("codex-workspace-smoke: PASS");
