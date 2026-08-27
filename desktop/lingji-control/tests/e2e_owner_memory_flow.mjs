import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { chromium } from "@playwright/test";

const state = { authorized: false, revoked: false, scan: null, scanReads: 0, scanRequests: 0, allStates: false, onboardingFailures: 7, onboardingDelay: false, onboardingRelease: false, outage: false, omitHomeCounts: false };
const allStateDiscovered = [
  ["detected", "available"], ["consent", "consent_required"], ["unsupported", "unsupported"], ["authorized", "available"],
  ["scanning", "available"], ["current", "available"], ["degraded", "available"], ["revoked", "available"], ["failed", "available"], ["paused", "available"], ["expired", "available"],
].map(([suffix, status]) => ({ kind: `fixture_${suffix}`, display_name: `测试${suffix}`, candidate_root: `/tmp/${suffix}`, status, capability: "metadata_discovery", reason: status === "unsupported" ? "不读取不透明存储" : null }));
const allStateSources = allStateDiscovered.filter((item) => !["detected", "consent", "unsupported"].includes(item.kind.replace("fixture_", ""))).map((item) => ({ source_id: `src-${item.kind}`, kind: item.kind, root: item.candidate_root, status: item.kind === "fixture_degraded" ? "degraded" : item.kind === "fixture_revoked" ? "revoked" : item.kind === "fixture_expired" ? "expired" : "authorized", capability: "metadata_discovery" }));
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
      const response = () => json(res, 200, state.allStates ? allStateDiscovered : [{ kind: "generic_ai_history", display_name: "Generic Inbox", candidate_root: "/tmp/lingji-fixture", status: "available", capability: "metadata_discovery", reason: null }]);
      if (state.outage) return json(res, 503, { detail: { code: "OFFLINE", message: "source service unavailable" } });
      if (state.onboardingDelay && !state.onboardingRelease) { const timer = setInterval(() => { if (state.onboardingRelease) { clearInterval(timer); response(); } }, 20); return; }
      return response();
    }
    if (path === "/api/automatic-memory/sources") {
      const response = () => state.onboardingFailures > 0
        ? (state.onboardingFailures -= 1, json(res, 503, { detail: { code: "TEMPORARY", message: "temporary source read failure" } }))
        : json(res, 200, state.allStates ? allStateSources : state.revoked ? [{ source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "revoked", capability: "metadata_discovery" }] : state.authorized ? [{ source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "authorized", capability: "metadata_discovery" }] : []);
      if (state.outage) return json(res, 503, { detail: { code: "OFFLINE", message: "source service unavailable" } });
      if (state.onboardingDelay && !state.onboardingRelease) { const timer = setInterval(() => { if (state.onboardingRelease) { clearInterval(timer); response(); } }, 20); return; }
      return response();
    }
    if (path === "/api/automatic-memory/summary") {
      const latest = state.allStates ? allStateScans[1] : state.scan ? { ...state.scan } : null;
      if (state.omitHomeCounts && latest) {
        delete latest.updated;
        delete latest.skipped;
      }
      return json(res, 200, { counts: state.allStates ? { completed: 1, failed: 1 } : state.scan ? { [state.scan.status]: 1 } : {}, total: state.allStates ? allStateScans.length : state.scan ? 1 : 0, latest, progress: state.scan ? { current: state.scan.progress, total: 1 } : { current: null, total: null }, last_error: state.scan?.last_error ?? null, next_action: "wait" });
    }
    if (path === "/api/automatic-memory/runtime") return json(res, 200, { state: "running", running: true, paused: false, worker_state: true, authorized_watcher_count: 1 });
    if (path === "/api/automatic-memory/scans") {
      if (state.allStates) return json(res, 200, allStateScans);
      if (state.scan?.status === "running" && state.completeNextRead) state.scan = { ...state.scan, status: "completed", progress: 1, total: 1, queued: 1, reused: 0, failed: 0, updated: 2, skipped: 3 };
      return json(res, 200, state.scan ? [{ ...state.scan, updated_at: new Date().toISOString() }] : []);
    }
    if (path === "/__test/complete") { state.completeNextRead = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/all-states") { state.allStates = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/omit-home-counts") { state.omitHomeCounts = body.includes("true"); return json(res, 200, { ok: true }); }
    if (path === "/__test/release-onboarding") { state.onboardingRelease = true; return json(res, 200, { ok: true }); }
    if (path === "/__test/outage") { state.outage = body.includes("true"); return json(res, 200, { ok: true, outage: state.outage }); }
    if (path === "/api/automatic-memory/authorize") { state.authorized = true; state.revoked = false; return json(res, 200, { source_id: "src-fixture", kind: "generic_ai_history", root: "/tmp/lingji-fixture", status: "authorized" }); }
    if (path === "/api/automatic-memory/scan") { state.scanRequests += 1; state.scanReads = 0; state.scan = state.scanRequests === 2 ? { scan_id: "scan-fixture", source_id: "src-fixture", status: "failed", progress: 0, total: 1, last_error: "fixture failure" } : { scan_id: "scan-fixture", source_id: "src-fixture", status: "running", progress: 0, total: 1 }; return json(res, 200, state.scan); }
    if (path === "/api/automatic-memory/retry") { state.scan = { scan_id: "scan-fixture", source_id: "src-fixture", status: "completed", progress: 1, total: 1, queued: 1, reused: 0, failed: 0, updated: 2, skipped: 3 }; return json(res, 200, state.scan); }
    if (path.startsWith("/api/automatic-memory/scans/")) return json(res, 200, state.scan ?? { status: "unknown" });
    if (path === "/api/automatic-memory/revoke") { state.authorized = false; state.revoked = true; state.scan = null; return json(res, 200, { source_id: "src-fixture", status: "revoked" }); }
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
  const installTauri = async (target) => target.addInitScript(({ port }) => {
    window.__TAURI_INTERNALS__ = { invoke: async (command) => {
      if (command === "control_credentials") return { base_url: `http://127.0.0.1:${port}`, token: "fixture-token" };
      if (command === "runtime_bootstrap_status") return { configured: true, c_drive_write_detected: false, active_workspace: "acceptance", data_root_display: "fixture" };
      if (String(command).includes("dialog") || String(command).includes("plugin:dialog")) return "/tmp/lingji-fixture";
      return { healthy: true, managed: true, binary_available: true, host: "127.0.0.1", port: port };
    } };
  }, { port: apiPort });
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
  assert.equal(await racePage.getByRole("heading", { name: "让灵机知道哪些内容可以接管", exact: true }).count(), 0, "delayed onboarding reads cannot redirect after navigation");
  await fetch(`http://127.0.0.1:${apiPort}/__test/release-onboarding`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await new Promise((resolve) => setTimeout(resolve, 500));
  await racePage.getByRole("heading", { name: "活动记录", exact: true }).waitFor();
  await racePage.close();
  state.onboardingDelay = false;
  state.onboardingFailures = 7;
  const page = await browser.newPage();
  await installTauri(page);
  await page.goto("http://127.0.0.1:4178", { waitUntil: "networkidle" });
  try {
    await page.getByRole("heading", { name: "让灵机知道哪些内容可以接管" }).waitFor({ timeout: 30_000 });
  } catch (reason) {
    console.error("rendered body:", await page.locator("body").innerText());
    throw reason;
  }
  await page.getByRole("button", { name: "选择文件夹并授权" }).click();
  await page.getByRole("heading", { name: "已授权", exact: true }).waitFor();
  await page.getByRole("button", { name: "立即扫描" }).click();
  await page.getByRole("heading", { name: "扫描中" }).waitFor();
  assert.equal(await page.getByText("扫描已完成").count(), 0, "running scan cannot show terminal success");
  await fetch(`http://127.0.0.1:${apiPort}/__test/complete`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await page.getByRole("button", { name: "重新读取" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/outage`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.getByRole("button", { name: "重新读取" }).click();
  await page.getByText("暂时无法读取记忆来源", { exact: false }).waitFor();
  assert.equal(await page.getByText("尚未获得", { exact: true }).count(), 0, "outage must preserve prior snapshot rather than show fake zeros");
  await fetch(`http://127.0.0.1:${apiPort}/__test/outage`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "false" });
  await page.getByRole("button", { name: "重新读取" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
  await page.getByRole("button", { name: "撤销" }).click();
  await page.getByRole("heading", { name: "已撤销" }).waitFor();
  await page.getByRole("button", { name: "选择文件夹并授权" }).waitFor();
  await page.getByRole("button", { name: "选择文件夹并授权" }).click();
  await page.getByRole("heading", { name: "已授权", exact: true }).waitFor();
  await page.getByRole("button", { name: "立即扫描" }).click();
  await page.getByRole("heading", { name: "扫描失败" }).waitFor();
  await page.getByRole("button", { name: "重试" }).click();
  await page.getByRole("heading", { name: "已接管" }).waitFor();
  await page.getByRole("button", { name: "活动记录" }).click();
  await page.getByRole("heading", { name: "活动记录" }).waitFor();
  await page.getByRole("button", { name: "运行状态" }).click();
  await page.getByRole("heading", { name: "运行正常", exact: true }).waitFor();
  const metricValue = async (title) => page.locator(".metric").filter({ hasText: title }).locator("strong").innerText();
  const waitMetric = async (title, expected, message) => {
    const deadline = Date.now() + 10_000;
    let value = "";
    while (Date.now() < deadline) {
      value = await metricValue(title);
      if (value === expected) return;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    assert.equal(value, expected, message);
  };
  await waitMetric("本次新增", "1", "Home must render the backend added count");
  await waitMetric("本次更新", "2", "Home must render the backend updated count");
  await waitMetric("本次跳过", "3", "Home must render the backend skipped count");
  await waitMetric("本次失败", "0", "Home must render the backend failed count");
  assert.equal(await page.locator(".observation-live-state").getByText("尚未获得", { exact: true }).count(), 1, "unknown queue activity must be neutral");
  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "让灵机知道哪些内容可以接管" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/omit-home-counts`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" }, body: "true" });
  await page.getByRole("button", { name: "重新读取" }).click();
  await page.getByRole("button", { name: "运行状态" }).click();
  await page.getByRole("heading", { name: "运行正常", exact: true }).waitFor();
  assert.equal(await metricValue("本次更新"), "尚未获得", "Home must keep absent updated count neutral");
  assert.equal(await metricValue("本次跳过"), "尚未获得", "Home must keep absent skipped count neutral");
  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "让灵机知道哪些内容可以接管" }).waitFor();
  await fetch(`http://127.0.0.1:${apiPort}/__test/all-states`, { method: "POST", headers: { "X-LingJi-Token": "fixture-token" } });
  await page.getByRole("button", { name: "重新读取" }).click();
  for (const heading of ["已发现", "需要确认", "暂不支持", "已授权", "扫描中", "已接管", "需要检查", "已撤销", "扫描失败"]) await page.getByRole("heading", { name: heading }).first().waitFor();
  const stateActions = {
    fixture_detected: { allow: ["授权"], deny: ["撤销", "立即扫描", "暂停", "继续", "重试"] },
    fixture_consent: { allow: ["授权"], deny: ["撤销", "立即扫描", "暂停", "继续", "重试"] },
    fixture_unsupported: { allow: [], deny: ["授权", "撤销", "立即扫描", "暂停", "继续", "重试", "查看结果"] },
    fixture_authorized: { allow: ["撤销", "立即扫描"], deny: ["授权", "暂停", "继续", "重试", "查看结果"] },
    fixture_scanning: { allow: ["撤销", "暂停", "查看结果"], deny: ["授权", "立即扫描", "继续", "重试"] },
    fixture_current: { allow: ["撤销", "立即扫描", "查看结果"], deny: ["授权", "暂停", "继续", "重试"] },
    fixture_degraded: { allow: ["授权", "撤销"], deny: ["立即扫描", "暂停", "继续", "重试", "查看结果"] },
    fixture_revoked: { allow: ["授权"], deny: ["撤销", "立即扫描", "暂停", "继续", "重试", "查看结果"] },
    fixture_failed: { allow: ["撤销", "重试", "查看结果"], deny: ["授权", "立即扫描", "暂停", "继续"] },
    fixture_paused: { allow: ["撤销", "继续", "查看结果"], deny: ["授权", "立即扫描", "暂停", "重试"] },
    fixture_expired: { allow: ["授权", "撤销"], deny: ["立即扫描", "暂停", "继续", "重试", "查看结果"] },
  };
  for (const [kind, expected] of Object.entries(stateActions)) {
    const card = page.locator(`[data-source-kind="${kind}"]`);
    await card.waitFor();
    const nextStep = await card.locator(".memory-source-facts > div").nth(2).locator("strong").innerText();
    assert.ok(nextStep.trim(), `${kind} must show a visible next step`);
    for (const label of expected.allow) await card.getByRole("button", { name: label, exact: true }).waitFor();
    for (const label of expected.deny) assert.equal(await card.getByRole("button", { name: label, exact: true }).count(), 0, `${kind} cannot offer ${label}`);
  }
  await page.locator('[data-source-kind="fixture_expired"]').getByText("授权已过期，需要重新授权。", { exact: true }).waitFor();
  await page.locator('[data-source-kind="fixture_paused"]').getByText("已暂停", { exact: false }).waitFor();
  await page.locator('[data-source-kind="fixture_paused"]').getByText("继续扫描", { exact: false }).waitFor();
  await browser.close();
  console.log("e2e_owner_memory_flow: PASS");
} finally {
  vite.kill();
  server.close();
}
