import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pendingActionsFrom } from "../src/contracts/workFact.ts";
import { formatWorkFactResult, formatWorkFactTitle } from "../src/components/workFactPresentation.ts";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");
const [contract, overview, activity, attention, panel] = await Promise.all([
  read("../src/contracts/workFact.ts"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/pages/ActivityPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/components/CurrentWorkPanel.tsx"),
]);

for (const field of ["work_id", "event_id", "event_type", "outcome", "next_action", "pending_actions", "failure"]) {
  assert.ok(contract.includes(field), `Work Fact contract is missing ${field}`);
}
for (const source of [activity, attention, panel]) {
  assert.match(source, /usePollingResource/);
  assert.match(source, /\/api\/work\//);
  assert.equal(source.includes("localMemoryLoopMock"), false);
}
assert.match(overview, /<CurrentWorkPanel/);
assert.equal(overview.includes("localMemoryLoopMock"), false);
assert.match(activity, /resource\.error/);
assert.match(activity, /resource\.stale/);
assert.match(activity, /\/api\/work\/history\?limit=20&offset=/);
assert.match(activity, /查看技术详情/);
assert.match(activity, /尚未获得/);
assert.match(attention, /resource\.error/);
assert.match(attention, /resource\.stale/);
assert.match(attention, /pending-actions\/\$\{encodeURIComponent\(action\.action_id\)\}\/resolve/);
assert.match(attention, /保存中…/);
assert.match(attention, /我已确认，继续处理/);
assert.match(panel, /work_id/);
assert.equal(contract.includes("items: "), false, "Work Fact must not maintain the legacy items contract");
assert.deepEqual(pendingActionsFrom({ pending_actions: [{ action_id: "action-1", work_id: "work-1", description: "确认" }] })?.map((action) => action.action_id), ["action-1"]);
assert.equal(pendingActionsFrom({ pending_actions: [null] }), null, "null pending action must be treated as unknown");
assert.equal(pendingActionsFrom({ pending_actions: [{}] }), null, "pending action without an id must be treated as unknown");
assert.equal(pendingActionsFrom({ pending_actions: [{ action_id: "   " }] }), null, "blank pending action id must be treated as unknown");
assert.equal(formatWorkFactTitle("扫描 codex_rollout"), "检查 Codex聊天记录");
assert.equal(formatWorkFactTitle("扫描 codex_transcript"), "检查 Codex聊天记录");
assert.equal(formatWorkFactTitle("扫描 codex_history"), "检查 Codex聊天记录");
assert.equal(formatWorkFactTitle("扫描 codex"), "检查 Codex聊天记录");
assert.equal(formatWorkFactTitle("扫描 chatgpt_history"), "检查 ChatGPT 导出记录");
assert.equal(formatWorkFactTitle("扫描 obsidian"), "检查 Obsidian 长期记忆区");
assert.equal(formatWorkFactTitle("扫描 generic"), "检查其他聊天来源");
assert.equal(formatWorkFactResult({ work: null, events: [], next_action: null, pending_actions: [], failure: null, outcome: { work_id: "w", status: "failed", summary: "unsupported automatic-memory source kind: chatgpt_history" } }), "这个来源暂不支持自动接入，其他记忆不受影响");
console.log("work-fact-smoke: PASS");
