import assert from "node:assert/strict";
import { actionEvidence, MemorySourcesApi, mergeSourceFacts, ownerSourceName, scanStatusLabel, scanTerminalEvidence, sourceMetadataEvidence, sourceStateLabel, countLabel } from "../src/pages/memorySourcesApi.ts";
import { LingJiApi } from "../src/api.ts";
import { readFileSync } from "node:fs";

const calls = [];
const originalFetch = globalThis.fetch;
globalThis.window = globalThis;
const responses = {
  "/api/automatic-memory/discovered": [
    { kind: "codex_transcript", display_name: "Codex transcript", candidate_root: "/tmp/codex", status: "available", capability: "metadata_discovery", reason: null },
    { kind: "claude_desktop", display_name: "Claude Desktop", candidate_root: "", status: "unsupported", capability: "metadata_discovery", reason: "Claude Desktop has no approved official export schema; opaque storage is not read" },
  ],
  "/api/automatic-memory/sources": [
    { source_id: "src-codex", kind: "codex_transcript", root: "/tmp/codex", status: "authorized", capability: "metadata_discovery", policy_version: "automatic-memory-source-v1" },
  ],
  "/api/automatic-memory/scans": [
    { scan_id: "scan-codex", source_id: "src-codex", status: "completed", progress: 2, total: 2, queued: 1, reused: 1, updated_at: "2026-08-27T01:02:00Z", last_error: null },
  ],
  "/api/automatic-memory/summary": { counts: { completed: 1 }, total: 1, latest: { scan_id: "scan-codex", source_id: "src-codex", status: "completed", progress: 2, total: 2, queued: 1, reused: 1 }, progress: { current: 2, total: 2 }, last_error: null, next_action: "wait" },
  "/api/automatic-memory/runtime": { state: "running", running: true, paused: false, scheduler_heartbeat_age: null, scheduler_heartbeat_reason: "unavailable", worker_state: true, authorized_watcher_count: 1, last_global_error: null },
};

globalThis.fetch = async (url, init = {}) => {
  const path = new URL(url).pathname;
  calls.push({ path, method: init.method ?? "GET", body: init.body ? JSON.parse(init.body) : null });
  if (init.method === "POST") {
    return new Response(JSON.stringify({ scan_id: "scan-next", source_id: "src-codex", status: path.endsWith("/scan") ? "running" : "authorized" }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  return new Response(JSON.stringify(responses[path]), { status: 200, headers: { "Content-Type": "application/json" } });
};

const client = new LingJiApi();
client.configure("http://127.0.0.1:8766", "test");
const api = new MemorySourcesApi(client);
const snapshot = await api.snapshot();
const pageSource = readFileSync(new URL("../src/pages/MemorySourcesPage.tsx", import.meta.url), "utf8");
assert.match(pageSource, /临时文件清理失败：灵机会自动重试，可重试/);
assert.match(pageSource, /cleanup_pending/);
assert.doesNotMatch(pageSource, /String\(snapshot\.runtime\?\.cleanup_error/);
assert.equal(snapshot.sources.length, 2);
assert.equal(snapshot.sources.find((item) => item.kind === "codex_transcript")?.state, "current");
assert.equal(snapshot.sources.find((item) => item.kind === "claude_desktop")?.state, "unsupported");
assert.equal(snapshot.sources.find((item) => item.kind === "claude_desktop")?.detail, "Claude 暂不支持自动导入旧记录；灵机不会读取它的内部数据库。");
assert.match(snapshot.sources.find((item) => item.kind === "claude_desktop")?.nextAction ?? "", /暂不支持|不要读取|官方导出/);
assert.equal(ownerSourceName({ kind: "obsidian", display_name: "Managed Obsidian memory" }), "Obsidian 长期记忆区");
assert.equal(sourceStateLabel("available"), "已发现");
assert.equal(scanStatusLabel("completed"), "已完成");
assert.equal(countLabel(null), "尚未获得");
assert.deepEqual(sourceMetadataEvidence({ file_count: 2, byte_count: 2048, earliest_mtime: 1760000000, latest_mtime: 1760003600 }), {
  fileCount: "2",
  byteCount: "2048 字节",
  earliestMtime: "2025-10-09 08:53:20 UTC",
  latestMtime: "2025-10-09 09:53:20 UTC",
});
assert.deepEqual(sourceMetadataEvidence({ file_count: null, byte_count: undefined, earliest_mtime: null, latest_mtime: Number.NaN }), {
  fileCount: "尚未获得",
  byteCount: "尚未获得",
  earliestMtime: "尚未获得",
  latestMtime: "尚未获得",
});
assert.equal(mergeSourceFacts([{ kind: "generic_ai_history", candidate_root: "/tmp/inbox", status: "available" }], [], []).length, 1);
const running = mergeSourceFacts(responses["/api/automatic-memory/discovered"], responses["/api/automatic-memory/sources"], [{ ...responses["/api/automatic-memory/scans"][0], status: "running", updated_at: "2026-08-27T02:00:00Z" }]);
assert.equal(actionEvidence({ ...snapshot, sources: running }, "src-codex", "scan"), true);
assert.equal(scanTerminalEvidence({ ...snapshot, sources: running }, "src-codex"), false, "running scan cannot show terminal success");
const expired = mergeSourceFacts([{ kind: "codex_transcript", display_name: "Codex transcript", candidate_root: "/tmp/codex", status: "available" }], [{ source_id: "src-codex", kind: "codex_transcript", root: "/tmp/codex", status: "expired" }], []);
assert.match(expired[0].detail, /授权已过期，需要重新授权/);
const stateFixtures = [
  ["detected", { status: "available" }, [], []],
  ["consent_required", { status: "consent_required", reason: "需要主人确认" }, [], []],
  ["unsupported", { status: "unsupported", reason: "不读取不透明存储" }, [], []],
  ["authorized", { status: "available" }, [{ source_id: "src-state", status: "authorized" }], []],
  ["scanning", { status: "available" }, [{ source_id: "src-state", status: "authorized" }], [{ source_id: "src-state", scan_id: "scan-state", status: "running" }]],
  ["current", { status: "available" }, [{ source_id: "src-state", status: "authorized" }], [{ source_id: "src-state", scan_id: "scan-state", status: "completed" }]],
  ["degraded", { status: "available" }, [{ source_id: "src-state", status: "degraded" }], []],
  ["revoked", { status: "available" }, [{ source_id: "src-state", status: "revoked" }], []],
  ["failed", { status: "available" }, [{ source_id: "src-state", status: "authorized" }], [{ source_id: "src-state", scan_id: "scan-state", status: "failed", last_error: "fixture failure" }]],
];
for (const [expected, discovered, authorized, scans] of stateFixtures) {
  const source = mergeSourceFacts([{ kind: "state", display_name: "测试来源", candidate_root: "/tmp/state", ...discovered }], authorized.map((item) => ({ kind: "state", root: "/tmp/state", ...item })), scans.map((item) => ({ scan_id: "scan-state", ...item })))[0];
  assert.equal(source.state, expected);
  assert.ok(source.nextAction.length > 0, `${expected} needs a next step`);
  assert.equal(source.detail.includes("/tmp/state"), false, `${expected} must not lead with an absolute path`);
}

await api.authorize(snapshot.sources[0]);
await api.scan("src-codex");
assert.equal(calls.at(-2).path, "/api/automatic-memory/authorize");
assert.equal(calls.at(-2).body.owner_confirmed, true);
assert.equal(calls.at(-1).path, "/api/automatic-memory/scan");
assert.equal(calls.at(-1).body.source_id, "src-codex");
globalThis.fetch = originalFetch;
console.log("automatic-memory-sources-smoke: PASS");
