import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const desktopDir = fileURLToPath(new URL("..", import.meta.url));
const apiOrigin = "http://127.0.0.1:8766";
const viteOrigin = "http://127.0.0.1:4179";
const source = {
  source_id: "source-codex",
  kind: "codex_rollout",
  root: "/safe/fixture/codex",
  status: "authorized",
  capability: "metadata_discovery",
};
const discovered = {
  kind: "codex_rollout",
  display_name: "Codex聊天记录",
  candidate_root: source.root,
  status: "available",
  file_count: 2,
  byte_count: 2048,
  earliest_mtime: 1760000000,
  latest_mtime: 1760003600,
  capability: "metadata_discovery",
  reason: null,
};
const scan = {
  scan_id: "scan-codex",
  source_id: source.source_id,
  status: "completed",
  progress: 1,
  total: 2,
  queued: 1,
  reused: 1,
  updated: 0,
  skipped: 0,
  failed: 0,
  counts_present: ["queued", "reused"],
  updated_at: "2026-08-28T08:03:00Z",
};
const card = {
  memory_id: "memory-card-1",
  kind: "memory",
  state: "active",
  topic: "发布计划",
  developments: ["团队讨论了发布日期", "确认发布前的检查清单"],
  conclusion: "当前结论是下周三发布。",
  freshness: { state: "current", reason: "最近证据仍有效", latest_evidence_at: "2026-08-28T08:03:00Z" },
  source: { label: "Codex聊天记录", status: "active", message_count: 2, latest_evidence_at: "2026-08-28T08:03:00Z", source_id: source.source_id },
  layers: {
    raw: { state: "available" },
    structured: { state: "available" },
    vector: { state: "complete" },
    permanent: { state: "complete" },
  },
  trust: { state: "trusted", confidence: 0.98 },
  action: { type: "correct", label: "修正内容", reason: "请核对后决定" },
  current_hash: "hash-memory-card-1",
  evidence: [{ message_id: "message-1", preview: "下周三发布", occurred_at: "2026-08-28T08:03:00Z" }],
};
const state = { scanRequests: 0 };

const json = (body) => JSON.stringify(body);
const fulfill = (route, body, status = 200) => route.fulfill({
  status,
  contentType: "application/json",
  headers: { "Access-Control-Allow-Origin": "*" },
  body: json(body),
});

const vite = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", "4179"], {
  cwd: desktopDir,
  stdio: "ignore",
});

try {
  await new Promise((resolve, reject) => {
    const deadline = Date.now() + 15_000;
    const poll = () => fetch(viteOrigin).then(() => resolve()).catch(() => {
      if (Date.now() >= deadline) reject(new Error("Vite did not start"));
      else setTimeout(poll, 100);
    });
    poll();
  });

  const installedChrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
  const browser = await chromium.launch({ headless: true, ...(existsSync(installedChrome) ? { executablePath: installedChrome } : {}) });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.addInitScript(() => {
    window.__TAURI_INTERNALS__ = { invoke: async (command) => {
      if (command === "control_credentials") return { base_url: "http://127.0.0.1:8766", token: "fixture-token" };
      if (command === "runtime_bootstrap_status") return { configured: true, c_drive_write_detected: false, active_workspace: "acceptance", data_root_display: "fixture" };
      return { healthy: true, managed: true, binary_available: true, host: "127.0.0.1", port: 8766 };
    } };
  });
  await page.route(`${apiOrigin}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, X-LingJi-Token", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" } });
    if (request.headers()["x-lingji-token"] !== "fixture-token") return fulfill(route, { detail: { code: "UNAUTHORIZED", message: "token required" } }, 401);
    if (url.pathname === "/api/overview") return fulfill(route, { health: { status: "healthy" }, memory_runtime: { state: "healthy", as_of: "2026-08-28T08:03:00Z" }, queue: { stats: {} } });
    if (url.pathname === "/api/automatic-memory/discovered") return fulfill(route, [discovered]);
    if (url.pathname === "/api/automatic-memory/sources") return fulfill(route, [source]);
    if (url.pathname === "/api/automatic-memory/scans") return fulfill(route, [{ ...scan, status: state.scanRequests ? "running" : scan.status }]);
    if (url.pathname === "/api/automatic-memory/summary") return fulfill(route, { counts: { completed: 1 }, total: 1, latest: scan, progress: { current: 1, total: 2 }, next_action: "wait" });
    if (url.pathname === "/api/automatic-memory/runtime") return fulfill(route, { state: "running", running: true, paused: false, automation_mode: "periodic_reconciliation", event_watcher_enabled: false, next_reconciliation_seconds: 900 });
    if (url.pathname === "/api/automatic-memory/scan" && request.method() === "POST") { state.scanRequests += 1; return fulfill(route, { ...scan, status: "running" }); }
    if (url.pathname === "/api/memory/inspector/cards-summary") return fulfill(route, { cards: 1, conversations: 1, messages: 2, permanent: 1, vectorized: 1, owner_review: 0 });
    if (url.pathname === "/api/memory/inspector/cards") return fulfill(route, { items: [card], pagination: { limit: 20, offset: 0, total: 1, has_more: false } });
    if (url.pathname === "/api/memory/inspector/cards/memory-card-1") return fulfill(route, { item: card });
    if (url.pathname === "/api/work/pending-actions") return fulfill(route, { pending_actions: [] });
    if (url.pathname === "/api/work/current") return fulfill(route, { work: null, events: [], outcome: null, next_action: null });
    if (url.pathname === "/api/work/history") return fulfill(route, { items: [], total: 0, has_more: false, limit: 3, offset: 0 });
    return fulfill(route, { detail: "not found" }, 404);
  });

  await page.goto(viteOrigin, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();

  const primaryLabels = await page.locator(".desktop-nav-primary .desktop-nav-item strong").allTextContents();
  assert.deepEqual(primaryLabels, ["首页", "记忆内容", "需要我", "记忆来源"], "ordinary navigation must have exactly four destinations");
  const advanced = page.locator("details.desktop-advanced-disclosure");
  assert.equal(await advanced.count(), 1, "advanced diagnostics must be a single disclosure");
  assert.equal(await advanced.evaluate((node) => node.open), false, "advanced diagnostics must be collapsed by default");
  await advanced.locator("summary").click();
  await advanced.getByRole("button", { name: "打开高级诊断", exact: true }).waitFor();
  await advanced.locator("summary").click();
  assert.equal(await advanced.evaluate((node) => node.open), false, "advanced diagnostics disclosure must close again");

  const nextStep = page.locator(".overview-next-step");
  await nextStep.getByRole("heading", { name: "下一步", exact: true }).waitFor();
  await nextStep.getByText("灵机会继续自动检查", { exact: false }).waitFor();
  await page.getByText("你现在不用做任何事", { exact: true }).waitFor();
  const homeText = await page.locator(".overview-page").innerText();
  assert.equal(/memory-card-1|source-codex|\{/.test(homeText), false, "Home ordinary copy must not expose IDs or JSON");

  await page.locator(".desktop-nav-item").filter({ hasText: "记忆内容" }).click();
  await page.getByRole("heading", { name: "记忆内容", exact: true }).first().waitFor();
  const cardsText = await page.locator(".owner-memory-card-grid").innerText();
  for (const field of ["最新结论：", "来源：", "原始记录：", "结构记录：", "语义向量：", "长期记忆：", "可信提示：", "建议："]) assert.ok(cardsText.includes(field), `memory card must show ${field}`);
  assert.equal(/memory-card-1|source-codex|\{/.test(cardsText), false, "memory card ordinary copy must not expose IDs or JSON");
  await page.locator(".owner-memory-card-title").click();
  await page.getByRole("dialog").waitFor();
  await page.keyboard.press("Escape");

  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "选择灵机要记住的内容", exact: true }).waitFor();
  const sourceCard = page.locator('[data-source-kind="codex_rollout"]');
  await sourceCard.getByText("文件数：2", { exact: true }).waitFor();
  await sourceCard.getByText("占用空间：2048 字节", { exact: true }).waitFor();
  assert.equal((await sourceCard.locator(".memory-source-metadata").innerText()).includes("/safe/fixture"), false, "source truth must not expose a filesystem path");
  await sourceCard.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.getByRole("heading", { name: "扫描中", exact: true }).waitFor();
  assert.equal(state.scanRequests, 1, "source action must trigger the existing scan API");

  await page.locator(".desktop-nav-item").filter({ hasText: "需要我" }).click();
  await page.getByRole("heading", { name: "需要我处理", exact: true }).waitFor();
  await page.getByText("现在没有需要你处理的事项。灵机会继续自动工作。", { exact: true }).waitFor();
  const attentionText = await page.locator(".observation-page").innerText();
  assert.equal(/source-codex|memory-card-1|\{/.test(attentionText), false, "zero-attention ordinary copy must not expose technical fields");

  await page.setViewportSize({ width: 1024, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "1024px owner views must not overflow horizontally");
  await page.setViewportSize({ width: 1280, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "1280px owner views must not overflow horizontally");
  await browser.close();
  console.log("owner-ui-menu-fast-track-smoke: PASS");
} finally {
  vite.kill();
}
