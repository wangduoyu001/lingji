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
const detectedOnly = {
  kind: "generic_ai_history",
  display_name: "其他AI聊天投递箱",
  candidate_root: "/safe/fixture/generic",
  status: "available",
  file_count: 1,
  byte_count: 512,
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
const scanRunning = { ...scan, scan_id: "scan-running", source_id: "source-other", status: "running", progress: 1, total: 4 };
const card = {
  memory_id: "memory-card-1",
  kind: "memory",
  state: "active",
  topic: "发布计划",
  developments: ["团队讨论了发布日期", "确认发布前的检查清单"],
  conclusion: null,
  freshness: { state: "current", reason: "最近证据仍有效", latest_evidence_at: null },
  source: { label: "Codex聊天记录", type: "codex_rollout", conversation_title: "发布计划讨论", conversation_id: "conversation-1", status: "active", message_count: 2, latest_evidence_at: "2026-08-28T08:03:00Z", source_id: source.source_id },
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
const historicalCard = { ...card, memory_id: "memory-card-old", topic: "旧版发布计划", conclusion: "旧结论", freshness: { state: "superseded", reason: "已被新结论覆盖" }, action: { type: "history", label: "查看历史" } };
const conversationOnlyCard = { ...card, memory_id: "conversation-only", kind: "conversation_evidence", topic: "原始讨论记录", source: { ...card.source, conversation_id: "conversation-only-1", conversation_title: "发布计划原始讨论" }, action: { type: "none", label: "无需处理", reason: "这是原始会话" } };
const noVectorCard = { ...card, memory_id: "memory-no-vector", topic: "未准备语义检索", layers: { ...card.layers, vector: { state: "unavailable", reason: "语义检索暂时不可用" } } };
const longBodyCard = { ...card, memory_id: "memory-long-body", topic: "长正文记忆" };
const restrictedCard = { ...card, memory_id: "memory-restricted", topic: "受限来源记忆", source: { ...card.source, label: "受限来源" } };
const actionRequiredCard = { ...card, memory_id: "memory-action-required", topic: "需要主人确认", state: "needs_review", action: { type: "confirm", label: "确认加入长期记忆", reason: "请核对后决定" }, layers: { ...card.layers, permanent: { state: "pending_owner_review" } } };
const additionalCurrentCards = Array.from({ length: 31 }, (_, index) => ({ ...card, memory_id: `memory-current-${index + 1}`, topic: `确定性当前记忆${index + 1}`, source: { ...card.source, conversation_id: `conversation-${(index % 3) + 1}` } }));
const historyCards = Array.from({ length: 3 }, (_, index) => ({ ...card, memory_id: `memory-history-${index + 1}`, topic: `确定性历史记忆${index + 1}`, freshness: { state: "superseded", reason: "已被新版本替代" }, action: { type: "history", label: "查看历史" } }));
const detailCards = [card, conversationOnlyCard, noVectorCard, longBodyCard, restrictedCard, actionRequiredCard, ...additionalCurrentCards, ...historyCards];
const state = { scanRequests: 0, sourceReads: 0, pendingReads: 0, cardListRequests: 0, pauseFailure: false, mutationFail: false, detailUnauthorized: false, pendingActions: [], requests: [] };

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
      return { healthy: true, managed: true, binary_available: false, host: "127.0.0.1", port: 8766 };
    } };
  });
  await page.route(`${apiOrigin}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    state.requests.push(url.pathname + (url.search || ""));
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, X-LingJi-Token", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" } });
    if (request.headers()["x-lingji-token"] !== "fixture-token") return fulfill(route, { detail: { code: "UNAUTHORIZED", message: "token required" } }, 401);
    if (url.pathname === "/api/overview") return fulfill(route, { health: { status: "healthy" }, memory_runtime: { state: "configuration_required", as_of: "2026-08-28T08:03:00Z" }, queue: { stats: {} } });
    if (url.pathname === "/api/automatic-memory/discovered") { state.sourceReads += 1; return fulfill(route, [discovered, detectedOnly]); }
    if (url.pathname === "/api/automatic-memory/sources") { state.sourceReads += 1; return fulfill(route, [source]); }
    if (url.pathname === "/api/automatic-memory/scans") { state.sourceReads += 1; return fulfill(route, state.scanRequests ? [{ ...scan, status: "running" }, { ...scanRunning }] : [scan, scanRunning]); }
    if (url.pathname === "/api/automatic-memory/scans/scan-codex") return fulfill(route, { ...scan, status: "failed", last_error: "fixture failure: /private/secret" });
    if (url.pathname === "/api/automatic-memory/summary") { state.sourceReads += 1; return fulfill(route, { counts: { completed: 3, running: 1, failed: 1 }, total: 5, latest: scan, progress: { current: 1, total: 2 }, next_action: "wait" }); }
    if (url.pathname === "/api/automatic-memory/runtime") { state.sourceReads += 1; return fulfill(route, { state: "running", running: true, paused: false, automation_mode: "periodic_reconciliation", event_watcher_enabled: false, next_reconciliation_seconds: 900 }); }
    if (url.pathname === "/api/automatic-memory/scan" && request.method() === "POST") { state.scanRequests += 1; return fulfill(route, { ...scan, status: "running" }); }
    if (url.pathname === "/api/automatic-memory/pause" && request.method() === "POST" && state.pauseFailure) return fulfill(route, { detail: { code: "PAUSE_FAILED", message: "raw backend detail /private/secret" } }, 503);
    if (url.pathname === "/api/memory/inspector/cards-summary") return fulfill(route, { cards: 37, conversations: 3, messages: 36, permanent: 13, vectorized: 32, owner_review: 1 });
    if (url.pathname === "/api/memory/inspector/cards") { state.cardListRequests += 1; const requestedState = url.searchParams.get("state"); const cards = requestedState === "current" ? detailCards.filter((item) => item.freshness?.state === "current") : detailCards; const offset = Number(url.searchParams.get("offset") || 0); const limit = Number(url.searchParams.get("limit") || 20); return fulfill(route, { items: cards.slice(offset, offset + limit), pagination: { limit, offset, total: cards.length, has_more: offset + limit < cards.length } }); }
    if (url.pathname === "/api/memory/inspector/cards/memory-card-1" && state.detailUnauthorized) return fulfill(route, { detail: { code: "UNAUTHORIZED", message: "token required" } }, 401);
    if (url.pathname === "/api/memory/inspector/cards/memory-card-1") return fulfill(route, { item: { ...card, as_of: "2026-08-28T08:05:00Z", content_hash: "hash-memory-card-1" } });
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1") return fulfill(route, { as_of: "2026-08-28T08:05:00Z", item: { memory_id: "memory-card-1", chunks: [{ chunk_id: "chunk-1", text: "下周三发布新版。发布前完成检查清单。", content_hash: "hash-memory-card-1", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1/vector") return fulfill(route, { as_of: "2026-08-28T08:05:00Z", memory_id: "memory-card-1", vector: { state: "available", chunks: [{ chunk_id: "chunk-1", exists: true, source: "live" }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1/source") return fulfill(route, { as_of: "2026-08-28T08:05:00Z", memory_id: "memory-card-1", canonical: { relative_path: "01-Inbox/release.md", citations: [{ chunk_id: "chunk-1", start_line: 1, end_line: 2 }] }, links: [{ source_id: "source-codex", conversation_id: "conversation-1" }] });
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1/evidence") {
      const offset = Number(url.searchParams.get("offset") || 0);
      const items = Array.from({ length: 20 }, (_, index) => ({ source_id: "source-codex", conversation_id: "conversation-1", message_id: `message-${offset + index + 1}`, role: index % 2 ? "assistant" : "user", sequence: offset + index + 1, occurred_at: `2026-08-28T08:${String(offset + index).padStart(2, "0")}:00Z`, excerpt: `第 ${offset + index + 1} 条来源摘要。`, content: `第 ${offset + index + 1} 条来源正文。`, content_hash: `message-hash-${offset + index + 1}`, raw_reference: `conversation-1/message-${offset + index + 1}`, truncated: false }));
      return fulfill(route, { as_of: "2026-08-28T08:05:00Z", memory_id: "memory-card-1", items, pagination: { limit: 20, offset, total: 40, has_more: offset === 0 } });
    }
    if (url.pathname === "/api/memory/inspector/cards/conversation-only") return fulfill(route, { item: conversationOnlyCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-no-vector") return fulfill(route, { item: noVectorCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-long-body") return fulfill(route, { item: longBodyCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-restricted") return fulfill(route, { item: restrictedCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-action-required") return fulfill(route, { item: actionRequiredCard });
    if (url.pathname === "/api/memory/inspector/memories/conversation-only") return fulfill(route, { item: { memory_id: "conversation-only", chunks: [] } });
    if (url.pathname === "/api/memory/inspector/messages" && url.searchParams.get("conversation_id") === "conversation-only-1") return fulfill(route, { items: [{ message_id: "conversation-message-1", role: "user", occurred_at: "2026-08-28T08:03:00Z", content: "这是原始会话里的完整消息。" }] });
    if (url.pathname === "/api/memory/inspector/memories/memory-no-vector") return fulfill(route, { item: { memory_id: "memory-no-vector", chunks: [{ chunk_id: "chunk-no-vector", text: "没有语义向量也应保留正文。", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-no-vector/vector") return setTimeout(() => fulfill(route, { vector: { state: "unavailable", chunks: [] } }, 503), 500);
    if (url.pathname === "/api/memory/inspector/memories/memory-restricted/source") return fulfill(route, { detail: { code: "RESTRICTED", message: "private path /Users/owner/secret" } }, 503);
    if (url.pathname === "/api/memory/inspector/memories/memory-restricted") return fulfill(route, { item: { memory_id: "memory-restricted", chunks: [{ chunk_id: "chunk-restricted", text: "受限来源正文仍可保留。", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-action-required") return fulfill(route, { item: { memory_id: "memory-action-required", chunks: [{ chunk_id: "chunk-action", text: "需要主人确认的正文。", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-action-required/vector") return fulfill(route, { vector: { state: "available", chunks: [] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-action-required/source") return fulfill(route, { canonical: {}, links: [] });
    if (url.pathname === "/api/memory/inspector/memories/memory-action-required/evidence") return fulfill(route, { items: [], pagination: { limit: 20, offset: 0, total: 0, has_more: false } });
    if (url.pathname === "/api/memory/review/candidates/memory-action-required/approve" && request.method() === "POST" && state.mutationFail) { state.mutationFail = false; return setTimeout(() => fulfill(route, { detail: { code: "TEMPORARY", message: "delayed mutation failure" } }, 503), 500); }
    if (url.pathname === "/api/memory/review/candidates/memory-action-required/approve" && request.method() === "POST") return fulfill(route, { ok: true });
    if (url.pathname === "/api/memory/inspector/memories/memory-long-body" && url.searchParams.get("cursor") === "chunk-long") return fulfill(route, { as_of: "2026-08-31T08:06:00Z", item: { memory_id: "memory-long-body", chunks: [{ chunk_id: "chunk-long-2", text: "长正文的继续部分。", truncated: false }], next_cursor: null } });
    if (url.pathname === "/api/memory/inspector/memories/memory-long-body") return fulfill(route, { as_of: "2026-08-31T08:05:00Z", item: { memory_id: "memory-long-body", chunks: [{ chunk_id: "chunk-long", text: "长正文的第一段。", truncated: true }], next_cursor: "chunk-long" } });
    if (url.pathname === "/api/memory/inspector/messages/message-1") return setTimeout(() => fulfill(route, { item: { message_id: "message-1", content: "这是旧卡片来源正文。" } }), 500);
    if (url.pathname === "/api/work/pending-actions") { state.pendingReads += 1; return fulfill(route, { pending_actions: state.pendingActions }); }
    if (url.pathname === "/api/work/current") return fulfill(route, { work: null, events: [], outcome: null, next_action: null });
    if (url.pathname === "/api/work/history") return fulfill(route, { items: [], total: 0, has_more: false, limit: 3, offset: 0 });
    return fulfill(route, { detail: "not found" }, 404);
  });

  await page.goto(viteOrigin, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "需要先完成设置", exact: true }).count(), 0, "healthy Core must not be presented as setup required by a memory runtime warning");

  const sidebarStatusText = await page.locator(".desktop-sidebar-status").innerText();
  assert.equal(sidebarStatusText.includes("8766"), false, "ordinary runtime warning must not expose the control port");

  const primaryLabels = await page.locator(".desktop-nav-primary .desktop-nav-item strong").allTextContents();
  assert.deepEqual(primaryLabels, ["首页", "记忆内容", "需要我", "记忆来源"], "ordinary navigation must have exactly four destinations");
  assert.deepEqual(await page.locator(".desktop-nav-primary .desktop-nav-item").evaluateAll((buttons) => buttons.map((button) => button.getAttribute("aria-label"))), ["首页", "记忆内容", "需要我", "记忆来源"], "ordinary navigation must expose exact accessible labels");
  assert.equal(await page.locator(".desktop-nav-primary").getByRole("button", { name: "活动记录", exact: true }).count(), 0, "activity must stay out of the ordinary sidebar");
  const advanced = page.locator("details.desktop-advanced-disclosure");
  assert.equal(await advanced.count(), 1, "advanced diagnostics must be a single disclosure");
  assert.equal(await advanced.evaluate((node) => node.open), false, "advanced diagnostics must be collapsed by default");
  await advanced.locator("summary").click();
  await advanced.getByRole("button", { name: "打开高级诊断", exact: true }).waitFor();
  await advanced.getByRole("button", { name: "打开高级诊断", exact: true }).click();
  await page.locator(".desktop-content").getByRole("heading", { name: "高级诊断", exact: true }).waitFor();
  const taskGroup = page.locator("details.diagnostics-group").filter({ hasText: "采集与任务" });
  await taskGroup.locator("summary").click();
  await taskGroup.getByRole("button", { name: "活动记录", exact: true }).waitFor();
  await taskGroup.getByRole("button", { name: "活动记录", exact: true }).click();
  await page.locator(".desktop-content").getByRole("heading", { name: "活动记录", exact: true }).first().waitFor();
  await page.locator(".desktop-nav-item").filter({ hasText: "首页" }).click();
  await page.getByRole("heading", { name: "首页", exact: true }).waitFor();
  await advanced.locator("summary").click();
  assert.equal(await advanced.evaluate((node) => node.open), false, "advanced diagnostics disclosure must close again");

  assert.equal(await page.locator(".overview-next-step").count(), 0, "Home must not present a manual next-step control");
  await page.getByText("目前不需要你处理", { exact: true }).waitFor();
  const homeText = await page.locator(".overview-page").innerText();
  assert.equal(/memory-card-1|source-codex|\{/.test(homeText), false, "Home ordinary copy must not expose IDs or JSON");

  state.pendingActions = [{ action_id: "action-fixture", work_id: "work-fixture", description: "确认发布计划" }];
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "灵机运行正常", exact: true }).waitFor();
  await page.getByText("有一件事需要你决定", { exact: true }).waitFor();
  await page.locator(".desktop-nav-item").filter({ hasText: "需要我" }).click();
  await page.getByRole("heading", { name: "需要我", exact: true }).waitFor();
  await page.getByText("确认发布计划", { exact: true }).waitFor();
  assert.ok(state.pendingReads > 0, "attention page must read the shared pending-actions endpoint on activation");
  state.pendingActions = [null];
  await page.locator(".desktop-nav-item").filter({ hasText: "首页" }).click();
  await page.getByRole("heading", { name: "首页", exact: true }).waitFor();
  await page.getByText("待办正在自动确认，当前不把未读取当作“没有待办”。", { exact: true }).waitFor();
  await page.locator(".desktop-nav-item").filter({ hasText: "需要我" }).click();
  await page.getByText("暂时无法确认需要你处理的事项，正在重试。", { exact: true }).waitFor();
  state.pendingActions = [{}];
  await page.locator(".desktop-nav-item").filter({ hasText: "首页" }).click();
  await page.getByRole("heading", { name: "首页", exact: true }).waitFor();
  await page.getByText("待办正在自动确认，当前不把未读取当作“没有待办”。", { exact: true }).waitFor();
  state.pendingActions = [];
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "首页", exact: true }).waitFor();
  await page.getByText("目前不需要你处理", { exact: true }).waitFor();

  await page.locator(".desktop-nav-item").filter({ hasText: "记忆内容" }).click();
  await page.getByRole("heading", { name: "记忆内容", exact: true }).first().waitFor();
  const cardsText = await page.locator(".owner-memory-card-grid").innerText();
  assert.equal(state.requests.some((url) => url.includes("/api/memory/inspector/memories/")), false, "ordinary card rendering must not prefetch canonical, vector, source or evidence bodies");
  assert.equal(state.requests.some((url) => url.includes("/api/memory/inspector/messages/")), false, "ordinary card rendering must not prefetch message bodies");
  assert.equal(await page.getByText("旧版发布计划", { exact: true }).count(), 0, "ordinary memory stream must never show superseded cards");
  assert.equal(await page.locator(".owner-memory-card").count(), 20, "ordinary memory stream must keep the first current page");
  assert.equal(await page.getByText("确定性历史记忆1", { exact: true }).count(), 0, "superseded history must never appear in the ordinary current page");
  assert.equal(await page.locator(".owner-memory-card-grid").getByRole("button", { name: /确认加入长期记忆|扫描|暂停|删除|移出/ }).count(), 0, "routine card actions must stay out of the main card surface");
  assert.ok(cardsText.includes("当前可确认：团队讨论了发布日期"), "a current card without a conclusion must show a sourced, honest current fact");
  assert.ok(cardsText.includes("2026"), "missing freshness time must fall back to the source evidence time");
  for (const field of ["当前可确认：", "来源：", "原始记录：", "结构记录：", "语义向量：", "长期记忆：", "可信提示："]) assert.ok(cardsText.includes(field), `memory card must show ${field}`);
  assert.equal(/memory-card-1|source-codex|\{/.test(cardsText), false, "memory card ordinary copy must not expose IDs or JSON");
  await page.locator(".owner-memory-card-title").first().click();
  await page.getByRole("dialog").waitFor();
  await page.getByRole("dialog").getByText("当前可确认：团队讨论了发布日期", { exact: true }).waitFor();
  assert(state.requests.some((url) => url.endsWith("/api/memory/inspector/cards/memory-card-1")), "selected detail must re-read the selected card");
  assert(state.requests.some((url) => url.endsWith("/api/memory/inspector/memories/memory-card-1?chunk_limit=20&max_chars=12000")), "selected detail must request bounded canonical content");
  assert(state.requests.some((url) => url.endsWith("/api/memory/inspector/memories/memory-card-1/vector")), "selected detail must request vector state");
  assert(state.requests.some((url) => url.endsWith("/api/memory/inspector/memories/memory-card-1/source")), "selected detail must request canonical/source provenance");
  assert(state.requests.some((url) => url.endsWith("/api/memory/inspector/memories/memory-card-1/evidence?limit=20&offset=0")), "selected detail must request only the first bounded evidence page");
  assert.equal(state.requests.some((url) => url.includes("/evidence?limit=20&offset=20")), false, "later evidence pages must not be prefetched");
  assert.equal(await page.locator('[data-testid="evidence-item"]').count(), 20, "first evidence page must be bounded to 20 items");
  await page.getByRole("dialog").getByRole("button", { name: "加载更多来源", exact: true }).click();
  await page.getByRole("dialog").locator('[data-testid="evidence-item"]').nth(39).waitFor();
  assert.equal(await page.locator('[data-testid="evidence-item"]').count(), 40, "load more must append exactly one next page");
  assert.equal(state.requests.filter((url) => url.includes("/evidence?limit=20&offset=20")).length, 1, "load more must request the next page once");
  assert.equal(state.requests.some((url) => url.includes("/evidence?limit=20&offset=40")), false, "load more must not fetch beyond the clicked page");
  await page.keyboard.press("Escape");
  state.detailUnauthorized = true;
  await page.getByRole("button", { name: "发布计划", exact: true }).click();
  await page.getByText("请先重新连接灵机", { exact: true }).waitFor();
  await page.getByRole("button", { name: "重新连接并重试", exact: true }).waitFor();
  state.detailUnauthorized = false;
  await page.getByRole("button", { name: "重新连接并重试", exact: true }).click();
  await page.getByRole("dialog").getByText("灵机当前记住的内容", { exact: true }).waitFor();
  const detailText = await page.getByRole("dialog").innerText();
  for (const section of ["灵机当前记住的内容", "当前结论", "事情怎么发展", "来源与核对", "原始记录", "结构记录", "语义向量", "长期记忆", "需要不需要主人处理", "备用操作"]) assert.ok(detailText.includes(section), `detail must show ${section}`);
  assert.ok(detailText.includes("下周三发布新版。发布前完成检查清单。"), "preference/decision detail must show readable canonical content");
  assert.ok(detailText.includes("团队讨论了发布日期") && detailText.includes("确认发布前的检查清单"), "decision/progress detail must show developments");
  for (const layer of ["原始记录", "结构记录", "语义向量", "长期记忆"]) assert.ok(detailText.includes(`${layer}\n已有`), `detail must show truthful layer ${layer}`);
  assert.ok(detailText.includes("Codex聊天记录") && detailText.includes("发布计划讨论"), "detail must show readable source software and conversation identity");
  assert.equal(detailText.includes("codex_rollout"), false, "detail must not expose internal source enum");
  assert.equal(await page.getByRole("dialog").getByRole("button", { name: "删除", exact: true }).count(), 0, "detail must not expose physical deletion");
  await page.setViewportSize({ width: 1024, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "1024px detail must not overflow horizontally");
  await page.setViewportSize({ width: 1280, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "1280px detail must not overflow horizontally");
  await page.getByRole("dialog").getByRole("button", { name: "查看来源", exact: true }).click();
  await page.getByRole("button", { name: "原始讨论记录", exact: true }).click();
  await page.getByRole("dialog").getByText("这是原始会话，尚未形成长期记忆", { exact: true }).waitFor();
  await page.getByRole("dialog").getByText("这是原始会话里的完整消息。", { exact: true }).waitFor();
  await page.waitForTimeout(700);
  assert.equal(await page.getByRole("dialog").getByText("这是旧卡片来源正文。", { exact: true }).count(), 0, "a delayed message from the previous selection must not appear in the new card");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "原始讨论记录", exact: true }).click();
  await page.getByRole("dialog").getByText("这是原始会话，尚未形成长期记忆", { exact: true }).waitFor();
  assert.equal(state.requests.some((url) => url.includes("/memories/conversation-only?chunk_limit")), false, "conversation-only detail must not request canonical");
  assert.ok(state.requests.some((url) => url.includes("/api/memory/inspector/messages?conversation_id=conversation-only-1")), "conversation-only detail must use existing messages pagination");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "未准备语义检索", exact: true }).click();
  await page.getByRole("dialog").getByText("没有语义向量也应保留正文。", { exact: true }).waitFor();
  assert.ok(state.requests.some((url) => url.includes("/memories/memory-no-vector?chunk_limit=20&max_chars=12000")), "ordinary memory with a conversation relation must still request canonical");
  await page.getByRole("dialog").getByText("语义向量状态暂时无法确认", { exact: false }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "受限来源记忆", exact: true }).click();
  await page.getByRole("dialog").getByText("来源暂时无法读取，正文仍可保留。", { exact: true }).waitFor();
  await page.getByRole("dialog").getByText("受限来源正文仍可保留。", { exact: true }).waitFor();
  assert.equal((await page.getByRole("dialog").innerText()).includes("/Users/owner/secret"), false, "restricted source details must not expose raw paths");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "长正文记忆", exact: true }).click();
  await page.getByRole("dialog").getByText("内容较长，下面可以继续读取正文。", { exact: true }).waitFor();
  await page.getByRole("button", { name: "继续读取正文", exact: true }).click();
  await page.waitForTimeout(100);
  assert.ok(state.requests.some((url) => url.includes("/memories/memory-long-body?chunk_limit=20&max_chars=12000&cursor=chunk-long")), "continuation must request the returned canonical cursor");
  await page.getByText("长正文的继续部分。", { exact: false }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "需要主人确认", exact: true }).click();
  await page.getByRole("dialog").locator("details.owner-memory-fallback-actions").locator("summary").click();
  await page.getByRole("dialog").getByRole("button", { name: "确认加入长期记忆", exact: true }).waitFor();
  await page.getByRole("dialog").getByText("需要主人确认的正文。", { exact: true }).waitFor();
  page.once("dialog", (dialog) => void dialog.accept());
  state.mutationFail = true;
  await page.getByRole("dialog").getByRole("button", { name: "确认加入长期记忆", exact: true }).click();
  await page.getByRole("button", { name: "原始讨论记录", exact: true }).click();
  await page.getByRole("dialog").getByText("这是原始会话，尚未形成长期记忆", { exact: true }).waitFor();
  await page.waitForTimeout(700);
  assert.equal(await page.getByText("保存失败，请稍后重试。", { exact: true }).count(), 0, "a delayed mutation error from the previous selection must not appear after switching cards");
  await page.keyboard.press("Escape");

  await page.evaluate(() => { Object.defineProperty(document, "hidden", { configurable: true, value: true }); document.dispatchEvent(new Event("visibilitychange")); });
  const hiddenSourceReads = state.sourceReads;
  await page.locator(".desktop-nav-item").filter({ hasText: "记忆来源" }).click();
  await page.getByRole("heading", { name: "记忆来源", exact: true }).first().waitFor();
  const sourceCard = page.locator('[data-source-kind="codex_rollout"]');
  await sourceCard.waitFor();
  assert.ok(state.sourceReads > hiddenSourceReads, "activating a hidden source page must still perform its first real read");
  await page.evaluate(() => { Object.defineProperty(document, "hidden", { configurable: true, value: false }); document.dispatchEvent(new Event("visibilitychange")); });
  const sourceSummary = await page.locator(".memory-sources-summary").innerText();
  for (const phrase of ["发现 2 个来源", "已授权 1 个", "已接管 1 个", "已完成检查 3 次"]) assert.ok(sourceSummary.includes(phrase), `source aggregate must show ${phrase}`);
  assert.ok(sourceSummary.includes("发现 2 个来源") && sourceSummary.includes("已接管 1 个"), "detection and takeover counts must stay distinct");
  assert.equal(sourceSummary.includes("已完成检查 2 次"), false, "completed aggregate must not use the truncated mixed-status scan list length");
  await sourceCard.getByText("文件数：2", { exact: true }).waitFor();
  await sourceCard.getByText("占用空间：2048 字节", { exact: true }).waitFor();
  assert.equal((await sourceCard.locator(".memory-source-metadata").innerText()).includes("/safe/fixture"), false, "source truth must not expose a filesystem path");
  await sourceCard.locator("details.memory-source-fallback-actions").locator("summary").click();
  await sourceCard.getByRole("button", { name: "现在检查", exact: true }).click();
  await page.getByRole("heading", { name: "扫描中", exact: true }).waitFor();
  assert.equal(state.scanRequests, 1, "source action must trigger the existing scan API");
  state.pauseFailure = true;
  await sourceCard.getByRole("button", { name: "暂停检查", exact: true }).click();
  await page.getByText("来源操作没有完成，请稍后重试。", { exact: true }).waitFor();
  const sourcePageText = await page.locator(".memory-sources-page").innerText();
  assert.equal(sourcePageText.includes("raw backend detail /private/secret"), false, "ordinary source errors must not expose raw backend details");
  await sourceCard.getByRole("button", { name: "查看这次检查", exact: true }).click();
  const detailGrid = page.locator(".memory-scan-detail .memory-detail-grid");
  await detailGrid.waitFor();
  assert.equal((await detailGrid.innerText()).includes("fixture failure"), false, "last_error must stay out of ordinary scan results");
  const technicalDetail = page.locator(".memory-scan-detail details");
  await technicalDetail.locator("summary").click();
  assert.ok((await technicalDetail.innerText()).includes("fixture failure: /private/secret"), "last_error must remain available in technical details");

  await page.locator(".desktop-nav-item").filter({ hasText: "需要我" }).click();
  await page.getByRole("heading", { name: "需要我", exact: true }).waitFor();
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
