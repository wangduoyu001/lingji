import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { chromium } from "@playwright/test";

const state = { authorized: false, revoked: false, scan: null, scanReads: 0, scanRequests: 0, allStates: false, sourceMode: "default", currentWorkNull: true, currentWorkStatus: "accepted", detailDefaultCounts: false, onboardingFailures: 7, onboardingDelay: false, onboardingRelease: false, outage: false, omitHomeCounts: false, pendingOutage: false, pendingResolved: false, reviewDelay: false, reviewRelease: true, cleanupPending: false, runtimeLastError: "cleanup_scan_failed" };
const allStateDiscovered = [
  ["detected", "available"], ["consent", "consent_required"], ["unsupported", "unsupported"], ["authorized", "available"],
  ["scanning", "available"], ["current", "available"], ["degraded", "available"], ["revoked", "available"], ["failed", "available"], ["paused", "available"], ["expired", "available"],
].map(([suffix, status]) => ({ kind: `fixture_${suffix}`, display_name: `测试${suffix}`, candidate_root: `/tmp/${suffix}`, status, capability: "metadata_discovery", reason: status === "unsupported" ? "不读取不透明存储" : null }));
allStateDiscovered.push({ kind: "obsidian", display_name: "Managed Obsidian memory", candidate_root: "/tmp/obsidian", status: "available", capability: "metadata_discovery", reason: null });
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
      const latest = state.allStates ? allStateScans[1] : state.scan ? { ...state.scan } : null;
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
      if (state.allStates) return json(res, 200, allStateScans);
      if (state.scan?.status === "running" && state.completeNextRead) state.scan = { ...state.scan, status: "completed", progress: 1, total: 1, queued: 1, reused: 0, failed: 0, updated: 2, skipped: 3 };
      return json(res, 200, state.scan ? [{ ...state.scan, updated_at: new Date().toISOString() }] : []);
    }
    if (path === "/__test/complete") { state.completeNextRead = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/all-states") { state.allStates = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/omit-home-counts") { state.omitHomeCounts = body.includes("true"); return json(res, 200, { ok: true }); }
    if (path === "/__test/source-mode") { state.sourceMode = body.trim() || "default"; state.allStates = false; state.authorized = false; state.revoked = false; state.scan = null; return json(res, 200, { ok: true, source_mode: state.sourceMode }); }
    if (path === "/__test/current-work-status") { state.currentWorkNull = body.trim() === "null"; state.currentWorkStatus = body.trim() || "accepted"; return json(res, 200, { ok: true, current_work_status: state.currentWorkStatus }); }
    if (path === "/__test/detail-default-counts") { state.detailDefaultCounts = body.includes("true"); return json(res, 200, { ok: true, detail_default_counts: state.detailDefaultCounts }); }
    if (path === "/__test/pending-outage") { state.pendingOutage = body.includes("true"); return json(res, 200, { ok: true, pending_outage: state.pendingOutage }); }
    if (path === "/__test/release-onboarding") { state.onboardingRelease = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/outage") { state.outage = body.includes("true"); return json(res, 200, { ok: true, outage: state.outage }); }
    if (path === "/__test/cleanup-pending") { state.cleanupPending = body.includes("true"); return json(res, 200, { ok: true, cleanup_pending: state.cleanupPending }); }
    if (path === "/api/automatic-memory/authorize") { state.authorized = true; state.revoked = false; return json(res, 200, { source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "authorized" }); }
    if (path === "/api/automatic-memory/scan") { state.scanRequests += 1; state.scanReads = 0; state.scan = state.scanRequests === 2 ? { scan_id: "scan-fixture", source_id: "src-fixture", status: "failed", progress: 0, total: 1, last_error: "fixture failure" } : { scan_id: "scan-fixture", source_id: "src-fixture", status: "running", progress: 0, total: 1 }; return json(res, 200, state.scan); }
    if (path === "/api/automatic-memory/retry") { state.scan = { scan_id: "scan-fixture", source_id: "src-fixture", status: "completed", progress: 1, total: 1, queued: 1, reused: 0, failed: 0, updated: 2, skipped: 3 }; return json(res, 200, state.scan); }
    if (path.startsWith("/api/automatic-memory/scans/")) {
      const detail = state.scan ? { ...state.scan } : { status: "unknown" };
      if (state.detailDefaultCounts) Object.assign(detail, { queued: 0, reused: 0, updated: 0, skipped: 0, failed: 0 });
      return json(res, 200, detail);
    }
    if (path === "/api/automatic-memory/revoke") { state.authorized = false; state.revoked = true; state.scan = null; return json(res, 200, { source_id: "src-fixture", status: "revoked" }); }
    if (path === "/api/work/history") return json(res, 200, { items: [{ work: { work_id: "work-capture-1", title: "整理项目会议记录", status: "completed", source_id: "source-1", updated_at: "2026-08-28T08:00:00Z" }, events: [{ event_id: "event-1", event_type: "completed", detail: { internal: "not primary" } }], outcome: { status: "completed", summary: "已保存 1 条记忆" }, next_action: null, pending_actions: [], failure: null, summary: { source: "项目会议", phase: "已完成", result: "已保存 1 条记忆", next_actor: null, time: "2026-08-28T08:00:00Z", source_id: "source-1" } }], total: 1, has_more: false, limit: 20, offset: 0 });
    if (path === "/api/work/current") return json(res, 200, state.currentWorkNull ? { work: null, events: [], outcome: null, next_action: null } : { work: { work_id: "work-current-1", title: "整理会议记录", status: state.currentWorkStatus, source_id: "source-1" }, events: [], outcome: null, next_action: null });
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
  await fetch(`http://127.0.0.1:${apiPort}/__test/detail-default-counts`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
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
  await page.getByText("这次检查没有完成，原来的记忆不会被删除。", { exact: true }).waitFor();
  await page.getByRole("button", { name: "再次检查" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
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
  await page.locator('[data-source-kind="claude_desktop"]').getByText("Claude 暂不支持自动导入旧记录。", { exact: true }).waitFor();
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
  await page.locator('[data-source-kind="claude_desktop"]').getByText("Claude 暂不支持自动导入旧记录。", { exact: true }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/source-mode`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "claude-consent" });
  await page.waitForTimeout(300);
  await page.locator(".memory-sources-intro").getByRole("button", { name: "现在检查" }).click();
  await page.getByText("暂时没有可连接的记录来源。", { exact: true }).waitFor();
  await page.locator('[data-source-kind="claude_desktop"]').getByRole("heading", { name: "需要确认", exact: true }).waitFor();
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
