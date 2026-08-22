import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { formatWorkDetail } from "../src/contracts/workFact.ts";

const here = dirname(fileURLToPath(import.meta.url));
const contract = await readFile(resolve(here, "../src/contracts/workFact.ts"), "utf8");
const currentPanel = await readFile(resolve(here, "../src/components/CurrentWorkPanel.tsx"), "utf8");
const activityPage = await readFile(resolve(here, "../src/pages/ActivityPage.tsx"), "utf8");
const attentionPage = await readFile(resolve(here, "../src/pages/AttentionPage.tsx"), "utf8");
const routes = await readFile(resolve(here, "../../../src/control/work_routes.py"), "utf8");
const api = await readFile(resolve(here, "../../../src/control/api.py"), "utf8");

for (const field of [
  "work_id",
  "event_id",
  "event_type",
  "action_id",
  "description",
  "created_at",
  "updated_at",
  "completed_at",
]) {
  assert.match(contract, new RegExp(`\\b${field}\\b`), `missing canonical Work Fact field: ${field}`);
}

for (const status of ["pending", "accepted", "running", "completed", "failed", "skipped"]) {
  assert.match(contract, new RegExp(`"${status}"`), `missing WorkStatus ${status}`);
}
assert.doesNotMatch(contract, /"queued"/, "desktop must not keep the old queued WorkStatus");
assert.match(contract, /"success" \| "failure" \| "skipped"/);
assert.match(contract, /Record<string, unknown>/);

for (const endpoint of [
  "/api/work/current",
  "/api/work/recent",
  "/api/work/pending-actions",
  "/api/work/timeline/{work_id}",
  "/api/work/{work_id}",
]) {
  assert.ok(routes.includes(endpoint), `formal work route missing: ${endpoint}`);
}
assert.match(api, /register_work_routes\(app, control, secured, translate_error=translate_error\)/);

assert.match(currentPanel, /resource\.error && !resource\.data/);
assert.match(currentPanel, /不能把接口不可用当成“没有工作”/);
assert.match(currentPanel, /work\?\.work_id/);
assert.match(currentPanel, /next_action\?\.description/);
assert.match(currentPanel, /event\.event_id/);
assert.match(currentPanel, /event\.event_type/);

assert.match(activityPage, /resource\.error && !resource\.data/);
assert.match(activityPage, /当前状态未知/);
assert.match(activityPage, /work\?\.work_id/);
assert.match(activityPage, /event\.event_id/);
assert.match(activityPage, /event\.event_type/);

assert.match(attentionPage, /resource\.error && !resource\.data/);
assert.match(attentionPage, /不能按 0 项处理/);
assert.match(attentionPage, /action\.action_id/);
assert.match(attentionPage, /action\.description/);
assert.match(attentionPage, /action\.work_id/);

assert.equal(formatWorkDetail({ capture_id: "capture-1" }), '{"capture_id":"capture-1"}');
assert.equal(formatWorkDetail({}), "无附加信息");
assert.equal(formatWorkDetail(null), "无附加信息");

console.log("work-fact-smoke: PASS");
