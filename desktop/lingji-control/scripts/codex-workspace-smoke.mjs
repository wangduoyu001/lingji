import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("../src/pages/CodexWorkspacePage.tsx", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../src/pages/codexWorkspaceApi.ts", import.meta.url), "utf8");
const nav = fs.readFileSync(new URL("../src/navigation.ts", import.meta.url), "utf8");
const contract = fs.readFileSync(new URL("../src/pages/codexWorkspaceContract.ts", import.meta.url), "utf8");
const dashboard = fs.readFileSync(new URL("../src/components/CurrentWorkPanel.tsx", import.meta.url), "utf8");

assert.match(nav, /codex_workspace/);
for (const path of ["/api/codex/projects/resolve", "/api/codex/projects", "/api/codex/current", "/api/codex/sessions", "/api/activity", "/api/context/project"]) assert.ok(api.includes(path), path);
// Codex workspace remains an advanced detail page. The global current-work panel
// now projects the canonical Work Fact read model instead of reconstructing state
// from Codex project/session aggregates.
assert.match(dashboard, /\/api\/work\/current/);
assert.match(dashboard, /work\?\.work_id/);
assert.match(dashboard, /outcome\?\.summary/);
assert.match(dashboard, /next_action\?\.description/);
assert.doesNotMatch(dashboard, /\/api\/codex\/current/);
assert.match(page, /Session 详情/); assert.doesNotMatch(page, /transcript/i); assert.doesNotMatch(page, /absolute_path|input_path/);
assert.match(api, /after_id=/); assert.match(contract, /ACTIVE_POLL_MS = 1000/); assert.match(contract, /IDLE_POLL_MS = 5000/);
assert.match(page, /document\.hidden/); assert.match(page, /visibilitychange/);
assert.match(page, /AbortController/); assert.match(page, /listRequestId/); assert.match(page, /activityRequestId/);
assert.match(page, /Context Pack/); assert.match(page, /navigator\.clipboard\.writeText\(contextPack\.markdown\)/);
assert.match(page, /progress_current/); assert.match(page, /progress_total/);
assert.match(page, /Memory Inspector/);
console.log("codex-workspace-smoke: PASS");
