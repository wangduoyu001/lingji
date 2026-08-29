import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { chromium } from "@playwright/test";

const state = { authorized: false, revoked: false, scan: null, scanReads: 0, scanRequests: 0, allStates: false, sourceMode: "default", currentWorkNull: true, currentWorkStatus: "accepted", currentWorkMode: "normal", activityMode: "normal", detailCountMode: "missing", onboardingFailures: 7, onboardingDelay: false, onboardingRelease: false, outage: false, omitHomeCounts: false, pendingOutage: false, pendingResolved: false, reviewDelay: false, reviewRelease: true, cleanupPending: false, runtimeLastError: "cleanup_scan_failed" };
const allStateDiscovered = [
  ["detected", "available"], ["consent", "consent_required"], ["unsupported", "unsupported"], ["authorized", "available"],
  ["scanning", "available"], ["current", "available"], ["degraded", "available"], ["revoked", "available"], ["failed", "available"], ["paused", "available"], ["expired", "available"],
].map(([suffix, status]) => ({ kind: `fixture_${suffix}`, display_name: `测试${suffix}`, candidate_root: `/tmp/${suffix}`, status, capability: "metadata_discovery", reason: status === "unsupported" ? "不读取不透明存储" : null }));
allStateDiscovered.push({ kind: "obsidian", display_name: "Managed Obsidian memory", candidate_root: "/tmp/vault", status: "available", capability: "metadata_discovery", reason: null });
allStateDiscovered.push({ kind: "claude_desktop", display_name: "Claude Desktop", candidate_root: "", status: "unsupported", capability: "metadata_discovery", reason: "Claude Desktop has no approved official export schema; opaque storage is not read" });
allStateDiscovered.push({ kind: "codex", display_name: "Codex transcript", candidate_root: "/tmp/codex", status: "available", capability: "metadata_discovery", reason: null });
allStateDiscovered.push({ kind: "chatgpt_export", display_name: "ChatGPT official export", candidate_root: "/tmp/chatgpt", status: "available", capability: "metadata_discovery", reason: null });
allStateDiscovered.push({ kind: "generic", display_name: "Generic AI History Inbox", candidate_root: "/tmp/generic", status: "available", capability: "metadata_discovery", reason: null });
allStateDiscovered.push({ kind: "mystery_kind", display_name: "Raw Internal Kind", candidate_root: "/tmp/mystery", status: "available", capability: "metadata_discovery", reason: null });
const allStateSources = allStateDiscovered.filter((item) => !["detected", "consent", "unsupported"].includes(item.kind.replace("fixture_", "")) && item.status !== "unsupported").map((item) => ({ source_id: `src-${item.kind}`, kind: item.kind, root: item.candidate_root, status: item.kind === "fixture_degraded" ? "degraded" : item.kind === "fixture_revoked" ? "revoked" : item.kind === "fixture_expired" ? "expired" : "authorized", capability: "metadata_discovery" }));
const allStateScans = [
  ["scanning", "running"], ["current", "completed"], ["failed", "failed"], ["paused", "paused"],
].map(([suffix, status]) => ({ scan_id: `scan-${suffix}`, source_id: `src-fixture_${suffix}`, status, progress: status === "completed" ? 1 : 0, total: 1, last_error: status === "failed" ? "fixture failure" : null }));
const json = (res, status, body) => { res.writeHead(status, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, X-LingJi-Token" }); res.end(JSON.stringify(body)); };
const scanDto = (scan) => {
  const dto = { ...scan };
  if (state.detailCountMode === "legacy" || state.detailCountMode === "missing") {
    dto.queued = null;
    dto.reused = null;
  } else if (state.detailCountMode === "explicit-zero") {
    dto.queued = 0;
    dto.reused = 0;
  } else if (state.detailCountMode === "explicit-positive") {
    dto.queued = 2;
    dto.reused = 1;
  }
  const countsPresent = ["queued", "reused"].filter((key) => Number.isInteger(dto[key]));
  dto.queued = countsPresent.includes("queued") ? dto.queued : null;
  dto.reused = countsPresent.includes("reused") ? dto.reused : null;
  dto.counts_present = countsPresent;
  return dto;
};
const server = http.createServer((req, res) => {
  const path = new URL(req.url, "http://127.0.0.1").pathname;
  if (req.method === "OPTIONS") { res.writeHead(204, { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, X-LingJi-Token", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" }); return res.end(); }
  if (req.headers["x-lingji-token"] !== "fixture-token") return json(res, 401, { detail: { code: "UNAUTHORIZED", message: "token required" } });
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    if (path === "/api/overview") return json(res, 200, { health: { status: "healthy" }, memory_runtime: { state: "healthy", as_of: new Date().toISOString(), memory: { documents: 1 } }, queue: { stats: {} } });
    if (path === "/api/automatic-memory/discovered") {
      const response = () => json(res, 200, state.sourceMode === "empty" ? [] : ["claude-only", "claude-consent"].includes(state.sourceMode) ? [{ kind: "claude_desktop", display_name: "Claude Desktop", candidate_root: "", status: state.sourceMode === "claude-consent" ? "consent_required" : "unsupported", capability: "metadata_discovery", reason: "Claude Desktop has no approved official export schema; opaque storage is not read" }] : state.allStates ? allStateDiscovered : [{ kind: "generic_ai_history", display_name: "Generic Inbox", candidate_root: "/tmp/lingji-fixture", status: "available", capability: "metadata_discovery", reason: null }]);
      if (state.outage) return json(res, 503, { detail: { code: "OFFLINE", message: "source service unavailable" } });
      if (state.onboardingDelay && !state.onboardingRelease) { const timer = setInterval(() => { if (state.onboardingRelease) { clearInterval(timer); response(); } }, 20); return; }
      return response();
    }
    if (path === "/api/automatic-memory/sources") {
      const response = () => state.sourceMode !== "default" ? json(res, 200, []) : state.onboardingFailures > 0
        ? (state.onboardingFailures -= 1, json(res, 503, { detail: { code: "TEMPORARY", message: "temporary source read failure" } }))
        : json(res, 200, state.allStates ? allStateSources : state.revoked ? [{ source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "revoked", capability: "metadata_discovery" }] : state.authorized ? [{ source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "authorized", capability: "metadata_discovery" }] : []);
      if (state.outage) return json(res, 503, { detail: { code: "OFFLINE", message: "source service unavailable" } });
      if (state.onboardingDelay && !state.onboardingRelease) { const timer = setInterval(() => { if (state.onboardingRelease) { clearInterval(timer); response(); } }, 20); return; }
      return response();
    }
    if (path === "/api/automatic-memory/summary") {
      const latest = state.allStates ? scanDto(allStateScans[1]) : state.scan ? scanDto(state.scan) : null;
      if (state.omitHomeCounts && latest) {
        delete latest.queued;
        delete latest.reused;
        delete latest.updated;
        delete latest.skipped;
      }
      return json(res, 200, { counts: state.allStates ? { completed: 1, failed: 1 } : state.scan ? { [state.scan.status]: 1 } : {}, total: state.allStates ? allStateScans.length : state.scan ? 1 : 0, latest, progress: state.scan ? { current: state.scan.progress, total: 1 } : { current: null, total: null }, last_error: state.scan?.last_error ?? null, next_action: "wait" });
    }
    if (path === "/api/automatic-memory/runtime") return json(res, 200, { state: state.cleanupPending ? "degraded" : "running", running: true, paused: false, worker_state: true, authorized_watcher_count: 1, automation_mode: "periodic_reconciliation", event_watcher_enabled: false, next_reconciliation_seconds: 900, cleanup_pending: state.cleanupPending, cleanup_error: state.cleanupPending ? "cleanup_scan_failed" : null });
    if (path === "/api/automatic-memory/scans") {
      if (state.allStates) return json(res, 200, allStateScans.map(scanDto));
      if (state.scan?.status === "running" && state.completeNextRead) state.scan = { ...state.scan, status: "completed", progress: 1, total: 1, queued: 1, reused: 0, failed: 0, updated: 2, skipped: 3 };
      return json(res, 200, state.scan ? [{ ...scanDto(state.scan), updated_at: new Date().toISOString() }] : []);
    }
    if (path === "/__test/complete") { state.completeNextRead = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/all-states") { state.allStates = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/omit-home-counts") { state.omitHomeCounts = body.includes("true"); return json(res, 200, { ok: true }); }
    if (path === "/__test/source-mode") { state.sourceMode = body.trim() || "default"; state.allStates = false; state.authorized = false; state.revoked = false; state.scan = null; return json(res, 200, { ok: true, source_mode: state.sourceMode }); }
    if (path === "/__test/current-work-status") { state.currentWorkNull = body.trim() === "null"; state.currentWorkMode = ["empty-scan", "changed-scan"].includes(body.trim()) ? body.trim() : "normal"; state.currentWorkStatus = body.trim() || "accepted"; return json(res, 200, { ok: true, current_work_status: state.currentWorkStatus }); }
    if (path === "/__test/activity-mode") { state.activityMode = body.trim() || "normal"; return json(res, 200, { ok: true, activity_mode: state.activityMode }); }
    if (path === "/__test/seed-latest-empty-scan") { state.sourceMode = "default"; state.authorized = true; state.revoked = false; state.onboardingFailures = 0; state.scan = { scan_id: "scan-empty", source_id: "src-fixture", status: "completed", progress: 1, total: 0, queued: 0, reused: 0, updated: 0, skipped: 0, failed: 0 }; return json(res, 200, { ok: true }); }
    if (path === "/__test/detail-count-mode") { state.detailCountMode = body.trim() || "missing"; return json(res, 200, { ok: true, detail_count_mode: state.detailCountMode }); }
    if (path === "/__test/pending-outage") { state.pendingOutage = body.includes("true"); return json(res, 200, { ok: true, pending_outage: state.pendingOutage }); }
    if (path === "/__test/release-onboarding") { state.onboardingRelease = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/outage") { state.outage = body.includes("true"); return json(res, 200, { ok: true, outage: state.outage }); }
    if (path === "/__test/cleanup-pending") { state.cleanupPending = body.includes("true"); return json(res, 200, { ok: true, cleanup_pending: state.cleanupPending }); }
    if (path === "/api/automatic-memory/authorize") { state.authorized = true; state.revoked = false; return json(res, 200, { source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "authorized" }); }
    if (path === "/api/automatic-memory/scan") { state.scanRequests += 1; state.scanReads = 0; state.scan = state.scanRequests === 2 ? { scan_id: "scan-fixture", source_id: "src-fixture", status: "failed", progress: 0, total: 1, last_error: "fixture failure" } : { scan_id: "scan-fixture", source_id: "src-fixture", status: "running", progress: 0, total: 1 }; return json(res, 200, scanDto(state.scan)); }
    if (path === "/api/automatic-memory/retry") { state.scan = { scan_id: "scan-fixture", source_id: "src-fixture", status: "completed", progress: 1, total: 1, queued: 1, reused: 0, failed: 0, updated: 2, skipped: 3 }; return json(res, 200, scanDto(state.scan)); }
    if (path.startsWith("/api/automatic-memory/scans/")) {
      const detail = state.scan ? scanDto(state.scan) : { status: "unknown" };
      const countFields = ["created", "queued", "reused", "updated", "skipped", "failed"];
      if (state.detailCountMode === "legacy") Object.assign(detail, { queued: null, reused: null, updated: 0, skipped: 0, failed: 0, counts_present: [] });
      if (state.detailCountMode === "explicit-zero") Object.assign(detail, { queued: 0, reused: 0, updated: 0, skipped: 0, failed: 0, counts_present: ["queued", "reused"] });
      if (state.detailCountMode === "explicit-positive") Object.assign(detail, { queued: 2, reused: 1, updated: 3, skipped: 4, failed: 0, counts_present: ["queued", "reused"] });
      if (state.detailCountMode === "missing") { Object.assign(detail, { queued: null, reused: null, counts_present: [] }); for (const field of ["created", "updated", "skipped", "failed"]) delete detail[field]; }
      return json(res, 200, detail);
    }
    if (path === "/api/automatic-memory/revoke") { state.authorized = false; state.revoked = true; state.scan = null; return json(res, 200, { source_id: "src-fixture", status: "revoked" }); }
    if (path === "/api/work/history") {
      const normalItem = { work: { work_id: "work-capture-1", title: "整理项目会议记录", status: "completed", source_id: "source-1", updated_at: "2026-08-28T08:00:00Z" }, events: [{ event_id: "event-1", event_type: "completed", detail: { internal: "not primary" } }], outcome: { status: "completed", summary: "已保存 1 条记忆" }, next_action: null, pending_actions: [], failure: null, summary: { source: "项目会议", phase: "已完成", result: "已保存 1 条记忆", next_actor: null, time: "2026-08-28T08:00:00Z", source_id: "source-1" } };
      const quietScan = (index, sourceId = "src-obsidian") => {
        const occurredAt = `2026-08-28T08:00:0${index}Z`;
        return { work: { work_id: `work-quiet-${sourceId}-${index}`, title: "扫描 obsidian", status: "completed", source_id: sourceId, updated_at: occurredAt }, events: [{ event_id: `event-quiet-${sourceId}-${index}`, event_type: "scan.completed", detail: { original_index: index, source_id: sourceId } }], outcome: { status: "completed", summary: "扫描完成，已检查 0 个来源文件（新增 0，复用 0）" }, next_action: { action_id: `action-quiet-${sourceId}-${index}`, work_id: `work-quiet-${sourceId}-${index}`, description: "灵机", actor: "system" }, pending_actions: [], failure: null, summary: { source: "obsidian", phase: "已完成", result: "成功", next_actor: "system", time: occurredAt, source_id: sourceId } };
      };
      const failedScan = { work: { work_id: "work-failed", title: "扫描 obsidian", status: "failed", source_id: "src-obsidian", updated_at: "2026-08-28T08:01:00Z" }, events: [{ event_id: "event-failed", event_type: "scan.failed", detail: {} }], outcome: { status: "failed", summary: "扫描没有完成" }, next_action: { action_id: "action-failed", work_id: "work-failed", description: "再次检查", actor: "system" }, pending_actions: [], failure: { failure_id: "failure-1", work_id: "work-failed", stage: "scan", reason: "fixture failure", retryable: true }, summary: { source: "obsidian", phase: "没有完成", result: "失败", next_actor: "system", time: "2026-08-28T08:01:00Z", source_id: "src-obsidian" } };
      const changedScan = { work: { work_id: "work-changed", title: "扫描 obsidian", status: "completed", source_id: "src-obsidian", updated_at: "2026-08-28T08:02:00Z" }, events: [{ event_id: "event-changed", event_type: "scan.completed", detail: {} }], outcome: { status: "completed", summary: "扫描完成，已检查 3 个来源文件（新增 1，复用 2）" }, next_action: { action_id: "action-changed", work_id: "work-changed", description: "灵机", actor: "system" }, pending_actions: [], failure: null, summary: { source: "obsidian", phase: "已完成", result: "成功", next_actor: "system", time: "2026-08-28T08:02:00Z", source_id: "src-obsidian" } };
      const runningScan = { work: { work_id: "work-running", title: "扫描 obsidian", status: "running", source_id: "src-obsidian", updated_at: "2026-08-28T08:03:00Z" }, events: [{ event_id: "event-running", event_type: "scan.running", detail: {} }], outcome: null, next_action: null, pending_actions: [], failure: null, summary: { source: "obsidian", phase: "处理中", result: null, next_actor: null, time: "2026-08-28T08:03:00Z", source_id: "src-obsidian" } };
      let items = [normalItem];
      let total = 1;
      let hasMore = false;
      if (state.activityMode === "matrix") items = [quietScan(0), quietScan(1), failedScan, quietScan(2), quietScan(3)];
      if (state.activityMode === "two-sources") items = [quietScan(0, "src-obsidian-a"), quietScan(1, "src-obsidian-b")];
      if (state.activityMode === "changed") items = [quietScan(0), changedScan, quietScan(1)];
      if (state.activityMode === "paged") { items = [quietScan(0), quietScan(1)]; total = 102; hasMore = true; }
      if (state.activityMode === "single") items = [quietScan(0)];
      if (state.activityMode === "running") items = [quietScan(0), runningScan, quietScan(1)];
      if (state.activityMode === "audit") items = [quietScan(0), quietScan(1), quietScan(2)];
      return json(res, 200, { items, total, has_more: hasMore, limit: 20, offset: 0 });
    }
    if (path === "/api/work/current") {
      if (state.currentWorkNull) return json(res, 200, { work: null, events: [], outcome: null, next_action: null });
      if (state.currentWorkMode === "empty-scan") return json(res, 200, { work: { work_id: "work-empty-scan", title: "扫描 obsidian", status: "completed", source_id: "src-obsidian" }, events: [], outcome: { work_id: "work-empty-scan", status: "completed", summary: "扫描完成，已检查 0 个来源文件（新增 0，复用 0）", evidence: { jobs: 0, queued: 0, reused: 0 } }, next_action: { action_id: "next-empty-scan", work_id: "work-empty-scan", description: "灵机", actor: "system" } });
      if (state.currentWorkMode === "changed-scan") return json(res, 200, { work: { work_id: "work-changed-scan", title: "扫描 obsidian", status: "completed", source_id: "src-obsidian" }, events: [], outcome: { work_id: "work-changed-scan", status: "completed", summary: "成功", evidence: { jobs: 2, queued: 2, reused: 0 } }, next_action: { action_id: "next-changed-scan", work_id: "work-changed-scan", description: "灵机", actor: "system" } });
      return json(res, 200, { work: { work_id: "work-current-1", title: "整理会议记录", status: state.currentWorkStatus, source_id: "source-1" }, events: [], outcome: null, next_action: null });
    }
    if (path === "/api/work/pending-actions") {
      if (state.pendingOutage) return json(res, 503, { detail: { code: "PENDING_OFFLINE", message: "pending service unavailable" } });
      return json(res, 200, { pending_actions: state.pendingResolved ? [] : [{ action_id: "action-1", work_id: "work-capture-1", description: "确认这条会议决定是否进入长期记忆", actor: "owner", resolved: false, created_at: "2026-08-28T08:01:00Z" }] });
    }
    if (path === "/api/work/pending-actions/action-1/resolve") { state.pendingResolved = true; return json(res, 200, { action_id: "action-1", work_id: "work-capture-1", resolved: true }); }
    if (path === "/api/memory/review/candidates" || path === "/api/memory/review/candidates/mem-1" || path === "/api/memory/review/candidates/mem-2") {
      const response = () => path.endsWith("mem-1")
        ? json(res, 200, { memory_id: "mem-1", title: "会议决定：下周发布", content: "下周三发布新版。", relative_path: "01-Inbox/AI-Memory/release.md", source_refs: ["message-1"], current_hash: "hash-1", importance: "high", confidence: 0.9, project_ids: ["灵机"], proposed_by: "system", created_at: "2026-08-28T08:02:00Z" })
        : path.endsWith("mem-2")
          ? json(res, 200, { memory_id: "mem-2", title: "另一条候选", content: "第二条候选内容。", relative_path: "01-Inbox/AI-Memory/second.md", source_refs: ["message-2"], current_hash: "hash-2", importance: "medium", confidence: 0.8, project_ids: ["灵机"], proposed_by: "system", created_at: "2026-08-28T08:03:00Z" })
          : json(res, 200, { items: [{ memory_id: "mem-1", title: "会议决定：下周发布", content_preview: "下周三发布新版。", relative_path: "01-Inbox/AI-Memory/release.md", source_refs: ["message-1"], current_hash: "hash-1", importance: "high", confidence: 0.9, project_ids: ["灵机"], proposed_by: "system", created_at: "2026-08-28T08:02:00Z" }, { memory_id: "mem-2", title: "另一条候选", content_preview: "第二条候选内容。", relative_path: "01-Inbox/AI-Memory/second.md", source_refs: ["message-2"], current_hash: "hash-2", importance: "medium", confidence: 0.8, project_ids: ["灵机"], proposed_by: "system", created_at: "2026-08-28T08:03:00Z" }], pagination: { total: 2, limit: 20, offset: 0, has_more: false } });
      if (state.reviewDelay && !state.reviewRelease) { const timer = setInterval(() => { if (state.reviewRelease) { clearInterval(timer); response(); } }, 20); return; }
      return response();
    }
    if (path === "/api/memory/inspector/status") return json(res, 200, { as_of: "2026-08-28T08:03:00Z", sources: { sources: 1, conversations: 1, messages: 1 }, memory: { documents: 1, chunks: 1 }, vector: { state: "available", coverage: 1, rebuild_required: false } });
    if (path === "/api/memory/inspector/sources" || path === "/api/memory/inspector/conversations" || path === "/api/memory/inspector/messages") return json(res, 200, { items: path.endsWith("sources") ? [{ source_id: "source-1", source_type: "codex_session", display_name: "Codex 工作会话", status: "active", updated_at: "2026-08-28T08:02:00Z" }] : path.endsWith("conversations") ? [{ conversation_id: "session-1", source_id: "source-1", title: "发布计划讨论", started_at: "2026-08-28T08:00:00Z", message_count: 1 }] : [{ message_id: "message-1", conversation_id: "session-1", source_id: "source-1", role: "user", author: "主人", occurred_at: "2026-08-28T08:02:00Z", content_preview: "我们确认下周三发布。" }], pagination: { total: 1, limit: 30, offset: 0, has_more: false } });
    if (path === "/api/memory/inspector/conversations/session-1") return json(res, 200, { item: { conversation_id: "session-1", source_id: "source-1", title: "发布计划讨论", started_at: "2026-08-28T08:00:00Z", message_count: 1 } });
    if (path === "/__test/review-delay") { state.reviewDelay = body.includes("true"); state.reviewRelease = !state.reviewDelay; return json(res, 200, { ok: true }); }
    if (path === "/__test/review-release") { state.reviewRelease = body.includes("true"); return json(res, 200, { ok: true }); }
    return json(res, 404, { detail: "not found" });
  });
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const apiPort = server.address().port;
const vite = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", "4178"], { stdio: "ignore" });
try {
  await new Promise((resolve, reject) => {
    const deadline = Date.now() + 15_000;
    const poll = () => fetch("http://127.0.0.1:4178").then(() => resolve()).catch(() => Date.now() < deadline ? setTimeout(poll, 100) : reject(new Error("Vite did not start")));
    poll();
  });
  const installedChrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
  assert.equal((await fetch(`http://127.0.0.1:${apiPort}/api/overview`)).status, 401, "missing token must be rejected");
  assert.equal((await fetch(`http://127.0.0.1:${apiPort}/api/overview`, { headers: { "X-LingJi-Token": "wrong-token" } })).status, 401, "wrong token must be rejected");
  const browser = await chromium.launch({ headless: true, ...(existsSync(installedChrome) ? { executablePath: installedChrome } : {}) });
  const installTauri = async (target) => target.addInitScript(({ port, runtimeLastError }) => {
    window.__TAURI_INTERNALS__ = { invoke: async (command) => {
      if (command === "control_credentials") return { base_url: `http://127.0.0.1:${port}`, token: "fixture-token" };
      if (command === "runtime_bootstrap_status") return { configured: true, c_drive_write_detected: false, active_workspace: "acceptance", data_root_display: "fixture" };
      if (String(command).includes("dialog") || String(command).includes("plugin:dialog")) return "/tmp/lingji-fixture";
      return { healthy: true, managed: true, binary_available: true, host: "127.0.0.1", port: port, last_error: runtimeLastError };
    } };
  }, { port: apiPort, runtimeLastError: state.runtimeLastError });
  state.onboardingFailures = 0;
  state.onboardingDelay = true;
  const racePage = await browser.newPage();
  await installTauri(racePage);
  await racePage.goto("http://127.0.0.1:4178", { waitUntil: "domcontentloaded" });
  try {
    await racePage.locator(".desktop-nav-item").filter({ hasText: "活动记录" }).waitFor({ timeout: 10_000 });
  } catch (reason) {
    console.error("race body:", await racePage.locator("body").innerText());
    throw reason;
  }
  await racePage.locator(".desktop-nav-item").filter({ hasText: "活动记录" }).click();
  await new Promise((resolve) => setTimeout(resolve, 1_100));
  await racePage.getByRole("heading", { name: "活动记录", exact: true }).waitFor();
  assert.equal(await racePage.getByRole("heading", { name: "选择灵机要记住的内容", exact: true }).count(), 0, "delayed onboarding reads cannot redirect after navigation");
  await fetch(`http://127.0.0.1:${apiPort}/__test/release-onboarding`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await new Promise((resolve) => setTimeout(resolve, 500));
  await racePage.getByRole("heading", { name: "活动记录", exact: true }).waitFor();
  await racePage.close();
  state.onboardingDelay = false;
  state.onboardingFailures = 7;
  const page = await browser.newPage();
  await installTauri(page);
  // The app keeps authenticated polling connections open; network-idle is
  // therefore not a meaningful readiness signal. Wait for DOM load and the
  // rendered landing heading instead.
  await page.goto("http://127.0.0.1:4178", { waitUntil: "domcontentloaded" });
  try {
    await page.getByRole("heading", { name: "选择灵机要记住的内容" }).waitFor({ timeout: 30_000 });
  } catch (reason) {
    console.error("rendered body:", await page.locator("body").innerText());
    throw reason;
  }
  await page.getByRole("button", { name: "选择文件夹并开始记忆" }).click();
  await page.getByRole("heading", { name: "已授权", exact: true }).waitFor();
  await page.getByText("打开灵机时会检查，之后每15分钟自动检查一次。", { exact: true }).waitFor();
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查", exact: true }).waitFor();
  assert.equal(await page.getByText("已授权 / 当前", { exact: true }).count(), 0, "source status counters must not be stacked as owner-facing cards");
  assert.equal(await page.getByText("SYSTEM POSTURE", { exact: true }).count(), 0, "internal posture label must stay out of primary UI");
  await page.locator('[data-source-kind="generic_ai_history"]').getByRole("button", { name: "现在检查", exact: true }).click();
  await page.getByRole("heading", { name: "扫描中" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "legacy" });
  await page.getByRole("button", { name: "查看这次检查", exact: true }).click();
  await page.getByText("这次检查正在进行。", { exact: true }).waitFor();
  const runningNewRow = page.locator(".memory-detail-grid > div").filter({ hasText: "新增" });
  assert.equal((await runningNewRow.innerText()).includes("新增\n0"), false, "model-default scan counts must not render as zero");
  assert.ok((await runningNewRow.innerText()).includes("尚未获得"), "missing scan counts must remain unknown");
  assert.equal(await page.getByText("扫描已完成").count(), 0, "running scan cannot show terminal success");
  await fetch(`http://127.0.0.1:${apiPort}/__test/complete`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/outage`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByText("暂时无法读取记忆来源", { exact: false }).waitFor();
  assert.equal(await page.getByText("尚未获得", { exact: true }).count(), 0, "outage must preserve prior snapshot rather than show fake zeros");
  await fetch(`http://127.0.0.1:${apiPort}/__test/outage`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "false" });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
  await page.getByRole("button", { name: "停止记忆", exact: true }).click();
  await page.getByRole("heading", { name: "已撤销" }).waitFor();
  await page.getByRole("button", { name: "选择文件夹并开始记忆" }).waitFor();
  await page.getByRole("button", { name: "选择文件夹并开始记忆" }).click();
  await page.getByRole("heading", { name: "已授权", exact: true }).waitFor();
  await page.locator('[data-source-kind="generic_ai_history"]').getByRole("button", { name: "现在检查", exact: true }).click();
  await page.getByRole("heading", { name: "扫描失败" }).waitFor();
  await page.getByRole("button", { name: "查看这次检查", exact: true }).click();
  await page.locator(".memory-scan-detail").getByText("这次检查没有完成，原来的记忆不会被删除。", { exact: true }).waitFor();
  await page.getByRole("button", { name: "再次检查" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "missing" });
  await page.getByRole("button", { name: "查看这次检查", exact: true }).click();
  const missingCompletedNewRow = page.locator(".memory-detail-grid > div").filter({ hasText: "新增" });
  assert.ok((await missingCompletedNewRow.innerText()).includes("尚未获得"), "missing completed scan counts must remain unknown");
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "legacy" });
  await page.getByRole("button", { name: "查看这次检查", exact: true }).click();
  const legacyCompletedNewRow = page.locator(".memory-detail-grid > div").filter({ hasText: "新增" });
  assert.equal((await legacyCompletedNewRow.innerText()).includes("新增\n0"), false, "legacy completed default zero must remain unknown");
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "explicit-zero" });
  await page.getByRole("button", { name: "查看这次检查", exact: true }).click();
  await page.waitForTimeout(100);
  assert.ok((await page.locator(".memory-detail-grid > div").filter({ hasText: "新增" }).innerText()).includes("新增\n0"), "explicit zero must remain visible");
  const zeroSummary = await (await fetch(`http://127.0.0.1:${apiPort}/api/automatic-memory/summary`, { headers: { "X-LingJi-Token": "fixture-token" } })).json();
  const zeroList = await (await fetch(`http://127.0.0.1:${apiPort}/api/automatic-memory/scans`, { headers: { "X-LingJi-Token": "fixture-token" } })).json();
  assert.equal(zeroSummary.latest.queued, 0, "summary must preserve explicit zero");
  assert.equal(zeroList[0].queued, 0, "list must preserve explicit zero");
  assert.deepEqual(zeroSummary.latest.counts_present, ["queued", "reused"], "summary presence must match detail");
  assert.deepEqual(zeroList[0].counts_present, ["queued", "reused"], "list presence must match detail");
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "explicit-positive" });
  await page.getByRole("button", { name: "查看这次检查", exact: true }).click();
  await page.waitForTimeout(100);
  assert.ok((await page.locator(".memory-detail-grid > div").filter({ hasText: "新增" }).innerText()).includes("新增\n2"), "explicit positive count must remain visible");
  await page.getByRole("button", { name: "活动记录" }).click();
  await page.getByRole("heading", { name: "活动记录" }).waitFor();
  await page.getByRole("button", { name: "运行状态" }).click();
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("目前空闲", { exact: true }).waitFor();
  assert.equal(await page.getByText("状态尚未获得", { exact: true }).count(), 0, "null work must render a clear idle state, not an unknown status");
  assert.equal(await page.getByText("内部错误：cleanup_scan_failed", { exact: true }).count(), 1, "raw runtime error may exist only in collapsed details");
  assert.equal(await page.getByText("内部错误：cleanup_scan_failed", { exact: true }).isVisible(), false, "raw runtime error must stay hidden in primary sidebar");
  assert.equal(await page.getByText("development", { exact: true }).count(), 0, "development channel must stay out of primary sidebar");
  await fetch(`http://127.0.0.1:${apiPort}/__test/current-work-status`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "accepted" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("已接收", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/current-work-status`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "retrying" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("正在重试", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/current-work-status`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "null" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("目前空闲", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/current-work-status`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "empty-scan" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("检查完成，未发现新内容", { exact: false }).waitFor();
  await page.getByText("灵机会继续自动检查", { exact: false }).waitFor();
  assert.equal(await page.getByText("下一步：灵机", { exact: true }).count(), 0, "system next action must be readable Chinese, not a raw actor");
  const currentWorkResult = page.locator(".current-work-readable-line");
  assert.equal(await currentWorkResult.getByText("扫描完成，已检查 0 个来源文件", { exact: false }).count(), 0, "raw automatic scan summary must stay out of ordinary current-work copy");
  const currentWorkDetails = page.locator(".current-work-timeline");
  if (!(await currentWorkDetails.evaluate((node) => node.open))) await currentWorkDetails.locator("summary").click();
  const currentWorkTechnical = await currentWorkDetails.innerText();
  assert.ok(currentWorkTechnical.includes("扫描完成，已检查 0 个来源文件"), "technical details must retain raw scan summary");
  assert.ok(currentWorkTechnical.includes('"jobs": 0'), "technical details must retain scan evidence");
  await fetch(`http://127.0.0.1:${apiPort}/__test/current-work-status`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "changed-scan" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("检查完成，新增 2 条内容", { exact: false }).waitFor();
  assert.equal(await page.getByText("结果：成功", { exact: true }).count(), 0, "generic success must not mask measured changed evidence");
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "explicit-zero" });
  await fetch(`http://127.0.0.1:${apiPort}/__test/seed-latest-empty-scan`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "选择灵机要记住的内容" }).waitFor();
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查", exact: true }).click();
  await page.getByRole("button", { name: "运行状态" }).click();
  await page.getByText(/最近一次检查已完成.*未发现新内容/).waitFor();
  const latestOverview = page.locator(".overview-page");
  assert.equal(await latestOverview.getByText("新增 0 条", { exact: false }).count(), 0, "explicit zero latest scan must not show misleading added-zero copy");
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-count-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "missing" });
  await fetch(`http://127.0.0.1:${apiPort}/__test/current-work-status`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "null" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText(/最近一次检查(已完成|已记录|正在进行)/).waitFor();
  assert.equal(await page.getByText("本次新增", { exact: true }).count(), 0, "scan counts must be summarized in a readable sentence, not stacked as developer metrics");
  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "选择灵机要记住的内容" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/cleanup-pending`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByText("临时文件清理失败：灵机会自动重试，可重试。", { exact: true }).waitFor();
  const cleanupDom = await page.locator("body").innerText();
  assert.equal(cleanupDom.includes("cleanup_scan_failed"), false, "cleanup reason must not be rendered");
  assert.equal(cleanupDom.includes("secret"), false, "cleanup secret must not be rendered");
  await fetch(`http://127.0.0.1:${apiPort}/__test/cleanup-pending`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "false" });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.waitForTimeout(100);
  assert.equal(await page.getByText("临时文件清理失败：灵机会自动重试，可重试。", { exact: true }).count(), 0, "recovered cleanup must clear the notice");
  await fetch(`http://127.0.0.1:${apiPort}/__test/omit-home-counts`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.waitForTimeout(300);
  await page.getByRole("button", { name: "运行状态" }).click();
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  assert.equal(await page.getByText("本次更新", { exact: true }).count(), 0, "missing scan counts must not appear as fake zeros or developer metrics");
  assert.equal(await page.getByText("本次跳过", { exact: true }).count(), 0, "missing scan counts must not appear as fake zeros or developer metrics");
  await page.getByText(/最近一次检查已完成/).waitFor({ timeout: 10_000 });
  const overviewText = await page.locator(".overview-page").innerText();
  assert.ok(overviewText.includes("最近一次检查已完成"), "completed summary without counts must still say it completed");
  assert.equal(overviewText.includes("检查结果尚未获得"), false, "missing summary counts must not become an unknown result on the primary page");
  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "选择灵机要记住的内容" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/all-states`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  for (const heading of ["已发现", "需要确认", "暂不支持", "已授权", "扫描中", "已接管", "需要检查", "已撤销", "扫描失败"]) await page.getByRole("heading", { name: heading }).first().waitFor();
  await page.locator('[data-source-kind="obsidian"]').getByText("Obsidian 长期记忆区", { exact: true }).waitFor();
  await page.locator('[data-source-kind="obsidian"]').getByText("你选择的目录", { exact: false }).waitFor();
  assert.equal(await page.locator('[data-source-kind="obsidian"]').getByText("vault", { exact: true }).count(), 0, "ordinary source card must not expose the root leaf");
  await page.locator('[data-source-kind="claude_desktop"]').getByText("Claude 暂时无法自动导入旧记录；灵机不会读取它的内部数据库。", { exact: true }).waitFor();
  assert.equal(await page.locator('[data-source-kind="claude_desktop"]').getByRole("button", { name: /开始记忆|选择文件夹/ }).count(), 0, "unsupported Claude must not offer an authorization action");
  await page.locator('[data-source-kind="codex"]').getByText("Codex聊天记录", { exact: true }).waitFor();
  await page.locator('[data-source-kind="chatgpt_export"]').getByText("ChatGPT导出记录", { exact: true }).waitFor();
  await page.locator('[data-source-kind="generic"]').getByText("其他AI聊天投递箱", { exact: true }).waitFor();
  await page.locator('[data-source-kind="mystery_kind"]').getByText("其他聊天来源", { exact: true }).waitFor();
  const stateActions = {
    fixture_detected: { allow: ["开始记忆"], deny: ["停止记忆", "现在检查", "暂停检查", "继续检查", "再次检查"] },
    fixture_consent: { allow: ["开始记忆"], deny: ["停止记忆", "现在检查", "暂停检查", "继续检查", "再次检查"] },
    fixture_unsupported: { allow: [], deny: ["开始记忆", "停止记忆", "现在检查", "暂停检查", "继续检查", "再次检查", "查看这次检查"] },
    fixture_authorized: { allow: ["停止记忆", "现在检查"], deny: ["开始记忆", "暂停检查", "继续检查", "再次检查", "查看这次检查"] },
    fixture_scanning: { allow: ["停止记忆", "暂停检查", "查看这次检查"], deny: ["开始记忆", "现在检查", "继续检查", "再次检查"] },
    fixture_current: { allow: ["停止记忆", "现在检查", "查看这次检查"], deny: ["开始记忆", "暂停检查", "继续检查", "再次检查"] },
    fixture_degraded: { allow: ["开始记忆", "停止记忆"], deny: ["现在检查", "暂停检查", "继续检查", "再次检查", "查看这次检查"] },
    fixture_revoked: { allow: ["开始记忆"], deny: ["停止记忆", "现在检查", "暂停检查", "继续检查", "再次检查", "查看这次检查"] },
    fixture_failed: { allow: ["停止记忆", "再次检查", "查看这次检查"], deny: ["开始记忆", "现在检查", "暂停检查", "继续检查"] },
    fixture_paused: { allow: ["停止记忆", "继续检查", "查看这次检查"], deny: ["开始记忆", "现在检查", "暂停检查", "再次检查"] },
    fixture_expired: { allow: ["开始记忆", "停止记忆"], deny: ["现在检查", "暂停检查", "继续检查", "再次检查", "查看这次检查"] },
  };
  for (const [kind, expected] of Object.entries(stateActions)) {
    const card = page.locator(`[data-source-kind="${kind}"]`);
    await card.waitFor();
    const nextStep = await card.locator(".memory-source-next").innerText();
    assert.ok(nextStep.trim(), `${kind} must show a visible next step`);
    for (const label of expected.allow) await card.getByRole("button", { name: label, exact: true }).waitFor();
    for (const label of expected.deny) assert.equal(await card.getByRole("button", { name: label, exact: true }).count(), 0, `${kind} cannot offer ${label}`);
  }
  await page.locator('[data-source-kind="fixture_expired"]').getByText("授权已过期，需要重新授权。", { exact: true }).waitFor();
  await page.locator('[data-source-kind="fixture_paused"]').getByText("已暂停", { exact: false }).waitFor();
  await page.locator('[data-source-kind="fixture_paused"]').getByText("继续检查", { exact: false }).waitFor();

  await fetch(`http://127.0.0.1:${apiPort}/__test/source-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "claude-only" });
  await page.waitForTimeout(300);
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByText("暂时没有可连接的记录来源。", { exact: true }).waitFor();
  await page.locator('[data-source-kind="claude_desktop"]').getByText("Claude 暂时无法自动导入旧记录；灵机不会读取它的内部数据库。", { exact: true }).waitFor();
  await page.locator('[data-source-kind="claude_desktop"]').getByText("请等待 Claude 提供受支持的官方导出，或暂不接入。", { exact: false }).waitFor();
  assert.equal(await page.getByText("Claude Desktop has no approved official export schema; opaque storage is not read", { exact: true }).count(), 0, "Claude raw reason must stay out of ordinary source copy");
  await fetch(`http://127.0.0.1:${apiPort}/__test/source-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "claude-consent" });
  await page.waitForTimeout(300);
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByText("暂时没有可连接的记录来源。", { exact: true }).waitFor();
  await page.locator('[data-source-kind="claude_desktop"]').getByRole("heading", { name: "需要确认", exact: true }).waitFor();
  await page.locator('[data-source-kind="claude_desktop"]').getByText("请等待 Claude 提供受支持的官方导出，或暂不接入。", { exact: false }).waitFor();
  await page.locator('[data-source-kind="claude_desktop"]').getByText("Claude 暂时无法自动导入旧记录；灵机不会读取它的内部数据库。", { exact: true }).waitFor();
  assert.equal(await page.locator('[data-source-kind="claude_desktop"]').getByText("Claude Desktop has no approved official export schema; opaque storage is not read", { exact: true }).count(), 0, "consent-required Claude raw reason must stay out of ordinary source copy");
  assert.equal(await page.locator('[data-source-kind="claude_desktop"]').getByRole("button", { name: /开始记忆|选择文件夹/ }).count(), 0, "consent-required Claude must not offer authorization without an approved path");
  await fetch(`http://127.0.0.1:${apiPort}/__test/source-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "empty" });
  await page.waitForTimeout(300);
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByText("暂时没有可连接的记录来源。", { exact: true }).waitFor();

  await page.locator(".desktop-nav-item").filter({ hasText: "活动记录" }).click();
  await page.getByRole("heading", { name: "活动记录", exact: true }).waitFor();
  await page.getByText("整理项目会议记录", { exact: true }).waitFor();
  await page.getByText("已保存 1 条记忆", { exact: false }).waitFor();
  assert.equal(await page.getByText('"internal":"not primary"', { exact: false }).count(), 0, "raw event JSON must not be primary activity copy");
  assert.equal(await page.getByText("source-1", { exact: true }).count(), 0, "source IDs must stay in collapsed technical details");
  const setActivityMode = async (mode) => fetch(`http://127.0.0.1:${apiPort}/__test/activity-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: mode });
  await setActivityMode("matrix");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 3);
  await page.getByText("近期已检查2次", { exact: false }).first().waitFor();
  assert.equal(await page.locator(".activity-card").count(), 3, "only each adjacent quiet run may be folded");
  await page.getByText("扫描没有完成", { exact: false }).waitFor();
  assert.equal(await page.getByText("扫描完成，已检查 0 个来源文件", { exact: false }).count(), 0, "empty scan raw summary must be normalized in ordinary copy");
  const matrixCards = page.locator(".activity-card");
  const firstMatrixDiagnostics = matrixCards.nth(0).locator(".activity-diagnostics");
  if (!(await firstMatrixDiagnostics.evaluate((node) => node.open))) await firstMatrixDiagnostics.locator("summary").click();
  const firstMatrixAudit = await firstMatrixDiagnostics.innerText();
  assert.ok(firstMatrixAudit.includes("work-quiet-src-obsidian-0"), "first quiet run must retain its first work audit");
  assert.ok(firstMatrixAudit.includes("work-quiet-src-obsidian-1"), "first quiet run must retain every work audit");
  assert.equal(firstMatrixAudit.includes("work-quiet-src-obsidian-2"), false, "a failure must separate later quiet audits");
  const secondMatrixDiagnostics = matrixCards.nth(2).locator(".activity-diagnostics");
  if (!(await secondMatrixDiagnostics.evaluate((node) => node.open))) await secondMatrixDiagnostics.locator("summary").click();
  const secondMatrixAudit = await secondMatrixDiagnostics.innerText();
  assert.ok(secondMatrixAudit.includes("work-quiet-src-obsidian-2"), "second quiet run must retain its first work audit");
  assert.ok(secondMatrixAudit.includes("work-quiet-src-obsidian-3"), "second quiet run must retain every work audit");
  assert.equal(secondMatrixAudit.includes("work-quiet-src-obsidian-0"), false, "separate quiet runs must not share audits");

  await setActivityMode("audit");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 1);
  const auditCard = page.locator(".activity-card").first();
  const ordinaryAuditSurface = auditCard.locator(".activity-card-heading, .activity-card-result, .activity-card-meta");
  for (const workId of ["work-quiet-src-obsidian-0", "work-quiet-src-obsidian-1", "work-quiet-src-obsidian-2"]) {
    assert.equal(await ordinaryAuditSurface.getByText(workId, { exact: false }).count(), 0, "work IDs stay out of ordinary activity copy");
  }
  const auditDetails = auditCard.locator(".activity-diagnostics");
  if (!(await auditDetails.evaluate((node) => node.open))) await auditDetails.locator("summary").click();
  const auditText = await auditDetails.innerText();
  for (const index of [0, 1, 2]) {
    assert.ok(auditText.includes(`work-quiet-src-obsidian-${index}`), `audit must retain work ${index}`);
    assert.ok(auditText.includes(`2026-08-28T08:00:0${index}Z`), `audit must retain original time ${index}`);
    assert.ok(auditText.includes(`event-quiet-src-obsidian-${index}`), `audit must retain event ${index}`);
    assert.ok(auditText.includes(`"original_index": ${index}`), `audit must retain event detail ${index}`);
  }
  assert.ok(auditText.includes("来源 ID：src-obsidian"), "audit must retain source identity");
  assert.ok(auditText.includes("状态码：completed"), "audit must retain original status");

  await setActivityMode("two-sources");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 2);
  assert.equal(await page.locator(".activity-card").count(), 2, "same display name with different source IDs must remain separate");
  assert.equal(await page.getByText("近期已检查1次", { exact: false }).count(), 0, "single quiet records must not claim a repeated count");
  await setActivityMode("changed");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 3);
  await page.getByText("已检查 3 个来源文件", { exact: false }).waitFor();
  assert.equal(await page.locator(".activity-card").count(), 3, "changed scans must remain separate from quiet scans");
  await setActivityMode("paged");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 1);
  await page.getByText("近期已检查2次", { exact: false }).first().waitFor();
  assert.equal(await page.getByText("近期已检查102次", { exact: false }).count(), 0, "quiet count must not use the API-wide total");
  assert.equal(await page.locator(".activity-pager").getByRole("button", { name: "下一页" }).isDisabled(), false, "has_more must keep pagination available");
  await setActivityMode("single");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 1);
  await page.getByText("检查完成，未发现新内容", { exact: false }).waitFor();
  assert.equal(await page.getByText("近期已检查1次", { exact: false }).count(), 0, "single quiet scan must not claim a repeated count");
  await setActivityMode("running");
  await page.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".activity-card").length === 3);
  await page.getByText("处理中", { exact: true }).waitFor();
  assert.equal(await page.locator(".activity-card").count(), 3, "running scan must break quiet runs and remain visible");
  assert.equal(await page.getByText("下一步：灵机", { exact: true }).count(), 0, "ordinary activity must not expose system actor names");
  await setActivityMode("normal");

  await page.locator(".desktop-nav-item").filter({ hasText: "需要我处理" }).click();
  await page.locator("h1").filter({ hasText: "需要我处理" }).waitFor();
  await page.getByText("确认这条会议决定是否进入长期记忆", { exact: true }).waitFor();
  assert.equal(await page.getByText("work-capture-1", { exact: true }).count(), 0, "attention page must not expose work IDs");
  await page.getByRole("button", { name: "完成处理", exact: true }).click();
  await page.getByText("现在没有需要你处理的事项。灵机会继续自动工作。", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/pending-outage`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.getByRole("button", { name: "运行状态" }).click();
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("待办状态暂时无法确认，正在重试", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/pending-outage`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "false" });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("你现在不用做任何事", { exact: true }).waitFor();
  assert.equal(await page.getByText("OWNER WORK FACT", { exact: true }).count(), 0, "internal work label must stay out of primary UI");
  assert.equal(await page.getByText("work-capture-1", { exact: true }).count(), 0, "work identity must stay in collapsed technical details");
  assert.equal(await page.getByText("AUTOMATIC RUNTIME", { exact: true }).count(), 0, "ordinary UI must not use decorative English runtime labels");
  assert.equal(await page.getByText("ADVANCED DIAGNOSTICS", { exact: true }).count(), 0, "ordinary UI must not use decorative English diagnostics labels");

  await page.locator(".desktop-nav-item").filter({ hasText: "高级诊断" }).click();
  await page.locator("details").filter({ hasText: "记忆与项目" }).locator("summary").click();
  await fetch(`http://127.0.0.1:${apiPort}/__test/review-delay`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.getByRole("button", { name: /人工记忆审核/ }).click();
  await page.getByRole("heading", { name: "人工记忆审核", exact: true }).waitFor();
  await page.getByText("正在读取候选记忆…", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/review-release`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.locator(".review-candidate-card").filter({ hasText: "会议决定：下周发布" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/review-release`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "false" });
  await page.locator(".review-candidate-card").filter({ hasText: "会议决定：下周发布" }).click();
  await page.getByText("正在读取候选详情…", { exact: true }).waitFor();
  await page.locator(".review-candidate-card").filter({ hasText: "另一条候选" }).click();
  await fetch(`http://127.0.0.1:${apiPort}/__test/review-release`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.getByRole("heading", { name: "另一条候选", exact: true }).waitFor();
  await page.locator(".review-candidate-card").filter({ hasText: "会议决定：下周发布" }).click();
  await page.getByText("来源：01-Inbox/AI-Memory/release.md", { exact: true }).waitFor();
  await page.getByText("来源引用：message-1", { exact: true }).waitFor();
  await page.getByText("对话：尚未获得", { exact: true }).waitFor();
  await page.getByText("原文片段：尚未获得", { exact: true }).waitFor();
  await page.getByText("当前状态：尚未获得", { exact: true }).waitFor();
  await page.getByText("历史状态：尚未获得", { exact: true }).waitFor();
  await page.getByText("为什么：尚未获得", { exact: true }).waitFor();
  assert.equal(await page.getByText("source_session_id", { exact: false }).count(), 0, "mock-only provenance IDs must not be used");

  await page.locator(".desktop-nav-item").filter({ hasText: "高级诊断" }).click();
  await page.locator("details").filter({ hasText: "采集与任务" }).locator("summary").click();
  await page.getByRole("button", { name: /手动投喂中心/ }).waitFor();
  assert.equal(await page.locator(".desktop-nav-item").filter({ hasText: "主动投喂" }).count(), 0, "legacy Capture must be hidden from navigation");
  await page.setViewportSize({ width: 900, height: 800 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "900px viewport must not horizontally clip");
  await browser.close();
  console.log("e2e_owner_memory_flow: PASS");
} finally {
  vite.kill();
  server.close();
}
