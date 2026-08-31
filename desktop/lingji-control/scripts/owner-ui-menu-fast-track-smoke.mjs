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
const conversationOnlyCard = { ...card, memory_id: "conversation-only", kind: "conversation_evidence", topic: "原始讨论记录", conclusion: "原始会话尚未形成长期结论", developments: ["原始会话保留上下文", "尚未写入长期记忆"], source: { ...card.source, conversation_id: "conversation-only-1", conversation_title: "发布计划原始讨论", message_count: 3 }, action: { type: "none", label: "无需处理", reason: "这是原始会话" } };
const noVectorCard = { ...card, memory_id: "memory-no-vector", topic: "未准备语义检索", conclusion: "这是已核对的项目事实", developments: ["事实已由主人确认", "等待语义索引恢复"], source: { ...card.source, label: "事实核对记录", conversation_title: "事实核对会话" }, layers: { ...card.layers, vector: { state: "unavailable", reason: "语义检索暂时不可用" } } };
const longBodyCard = { ...card, memory_id: "memory-long-body", topic: "长正文记忆", conclusion: "项目进展正在按计划推进", developments: ["第一阶段已经完成", "第二阶段等待发布"], source: { ...card.source, label: "项目进展记录", conversation_title: "项目进展同步" } };
const restrictedCard = { ...card, memory_id: "memory-restricted", topic: "受限来源记忆", conclusion: "受限来源的事实摘要", developments: ["仅展示安全摘要", "全文需要主人点选核对"], source: { ...card.source, label: "受限来源", conversation_title: "受限事实核对" }, evidence: [] };
const staleBCard = { ...card, memory_id: "memory-stale-b", current_hash: "hash-memory-stale-b", topic: "延迟竞态普通记忆", conclusion: "B 的独特结论", developments: ["B 的首屏证据独立", "B 的分页状态保持"], source: { ...card.source, label: "B 独立来源", conversation_title: "B 独立会话" }, evidence: [{ message_id: "b-message-1", preview: "B 独特首屏摘要" }] };
const actionRequiredCard = { ...card, memory_id: "memory-action-required", topic: "需要主人确认", conclusion: "主人偏好每周一上午收到摘要", developments: ["偏好来自主人明确表达", "待确认后加入长期记忆"], source: { ...card.source, label: "偏好来源", conversation_title: "主人偏好讨论" }, state: "needs_review", action: { type: "confirm", label: "确认加入长期记忆", reason: "请核对后决定" }, layers: { ...card.layers, permanent: { state: "pending_owner_review" } } };
const actionCards = [
  actionRequiredCard,
  { ...actionRequiredCard, memory_id: "memory-action-edit", topic: "生命周期校验卡片B", conclusion: "编辑后的偏好结论", action: { type: "confirm", label: "编辑确认", reason: "请补充偏好" } },
  { ...actionRequiredCard, memory_id: "memory-action-reject", topic: "生命周期校验卡片C", conclusion: "待拒绝的候选", action: { type: "confirm", label: "拒绝候选", reason: "请说明拒绝理由" } },
  { ...card, memory_id: "memory-action-correct", topic: "生命周期校验卡片D", conclusion: "需要修正的项目事实", action: { type: "correct", label: "修正内容", reason: "请说明修正" } },
  { ...card, memory_id: "memory-action-invalidate", topic: "生命周期校验卡片E", conclusion: "需要标记过时的事实", action: { type: "invalidate", label: "标记已经过时", reason: "请说明原因" } },
  { ...card, memory_id: "memory-action-archive", topic: "生命周期校验卡片F", conclusion: "需要移出当前记忆的旧事实", action: { type: "archive", label: "移出当前记忆", reason: "请说明原因" } },
];
const additionalCurrentCards = Array.from({ length: 24 }, (_, index) => ({ ...card, memory_id: `memory-current-${index + 1}`, topic: `确定性当前记忆${index + 1}`, source: { ...card.source, conversation_id: `conversation-${(index % 3) + 1}` } }));
const historyCards = Array.from({ length: 3 }, (_, index) => ({ ...card, memory_id: `memory-history-${index + 1}`, topic: `确定性历史记忆${index + 1}`, conclusion: `历史结论${index + 1}`, freshness: { state: "superseded", reason: "已由当前版本替代", replacement_id: "memory-card-1" }, action: { type: "history", label: "查看历史" } }));
const historyNoise = Array.from({ length: 19 }, (_, index) => ({ ...card, memory_id: `memory-history-noise-${index + 1}`, topic: `不匹配历史元数据${index + 1}`, freshness: { state: "superseded", reason: "由其他版本替代", replacement_id: `other-current-${index + 1}` }, action: { type: "history", label: "查看历史" } }));
const detailCards = [card, conversationOnlyCard, noVectorCard, longBodyCard, restrictedCard, staleBCard, ...actionCards, ...additionalCurrentCards, ...historyCards];
const actionCardsById = new Map(actionCards.map((item) => [item.memory_id, item]));
const state = { scanRequests: 0, sourceReads: 0, pendingReads: 0, cardListRequests: 0, pauseFailure: false, mutationFail: false, detailUnauthorized: false, initialEvidenceFailure: false, canonicalFailure: false, evidenceFailure: true, evidenceDelay: false, mutations: [], pendingActions: [], requests: [] };

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
    if (url.pathname === "/api/memory/inspector/cards") { state.cardListRequests += 1; const requestedState = url.searchParams.get("state"); const cards = requestedState === "current" ? detailCards.filter((item) => item.freshness?.state === "current") : requestedState === "superseded" ? [...historyCards.slice(0, 1), ...historyNoise, ...historyCards.slice(1)] : detailCards; const offset = Number(url.searchParams.get("offset") || 0); const limit = Number(url.searchParams.get("limit") || 20); return fulfill(route, { items: cards.slice(offset, offset + limit), pagination: { limit, offset, total: cards.length, has_more: offset + limit < cards.length } }); }
    if (url.pathname === "/api/memory/inspector/cards/memory-card-1" && state.detailUnauthorized) return fulfill(route, { detail: { code: "UNAUTHORIZED", message: "token required" } }, 401);
    if (url.pathname === "/api/memory/inspector/cards/memory-card-1") return fulfill(route, { item: { ...card, as_of: "2026-08-28T08:05:00Z", content_hash: "hash-memory-card-1" } });
    if (url.pathname.startsWith("/api/memory/inspector/cards/memory-history-")) { const id = url.pathname.split("/").pop(); return fulfill(route, { item: historyCards.find((item) => item.memory_id === id) }); }
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1") { if (state.canonicalFailure) { state.canonicalFailure = false; return fulfill(route, { detail: { code: "TEMPORARY", message: "temporary canonical failure" } }, 503); } return fulfill(route, { as_of: "2026-08-28T08:05:00Z", item: { memory_id: "memory-card-1", chunks: [{ chunk_id: "chunk-1", text: "下周三发布新版。发布前完成检查清单。", content_hash: "hash-memory-card-1", truncated: false }] } }); }
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1/vector") return fulfill(route, { as_of: "2026-08-28T08:05:00Z", memory_id: "memory-card-1", vector: { state: "available", chunks: [{ chunk_id: "chunk-1", exists: true, source: "live" }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1/source") return fulfill(route, { as_of: "2026-08-28T08:05:00Z", memory_id: "memory-card-1", canonical: { relative_path: "01-Inbox/release.md", citations: [{ chunk_id: "chunk-1", start_line: 1, end_line: 2 }] }, links: [{ source_id: "source-codex", conversation_id: "conversation-1" }] });
    if (url.pathname === "/api/memory/inspector/memories/memory-card-1/evidence") {
      const offset = Number(url.searchParams.get("offset") || 0);
      if (offset === 0 && state.initialEvidenceFailure) { state.initialEvidenceFailure = false; return fulfill(route, { detail: { code: "TEMPORARY", message: "temporary initial evidence failure" } }, 503); }
      if (offset === 20 && state.evidenceFailure) { state.evidenceFailure = false; return fulfill(route, { detail: { code: "TEMPORARY", message: "temporary evidence failure" } }, 503); }
      const items = Array.from({ length: 20 }, (_, index) => {
        const sequence = offset === 20 && index < 2 ? 19 + index : offset + index + 1;
        const messageId = offset === 0 && index < 2 ? `message-card-${index + 1}` : `message-${sequence}`;
        const alternate = offset === 0 && index === 1;
        return { source_id: alternate ? "source-chatgpt" : "source-codex", source_label: alternate ? "ChatGPT聊天记录" : "Codex聊天记录", source_type: alternate ? "chatgpt" : "codex_rollout", conversation_id: alternate ? "conversation-2" : "conversation-1", conversation_title: alternate ? "另一个来源会话" : "发布计划讨论", message_id: messageId, role: index % 2 ? "assistant" : "user", sequence, occurred_at: `2026-08-28T08:${String(sequence).padStart(2, "0")}:00Z`, excerpt: `第 ${sequence} 条来源摘要。`, content: `第 ${sequence} 条来源正文。`, content_hash: `message-hash-${sequence}`, raw_reference: `conversation-1/${messageId}`, truncated: false };
      });
      const result = { as_of: "2026-08-28T08:05:00Z", memory_id: "memory-card-1", items, pagination: { limit: 20, offset, total: 40, has_more: offset === 0 } };
      return state.evidenceDelay && offset === 20 ? setTimeout(() => fulfill(route, result), 500) : fulfill(route, result);
    }
    if (url.pathname === "/api/memory/inspector/cards/conversation-only") return fulfill(route, { item: conversationOnlyCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-no-vector") return fulfill(route, { item: noVectorCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-long-body") return fulfill(route, { item: longBodyCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-restricted") return fulfill(route, { item: restrictedCard });
    if (url.pathname === "/api/memory/inspector/cards/memory-stale-b") return fulfill(route, { item: staleBCard });
    if (url.pathname.startsWith("/api/memory/inspector/cards/") && actionCardsById.has(url.pathname.split("/").pop())) { const id = url.pathname.split("/").pop(); return fulfill(route, { item: actionCardsById.get(id) }); }
    if (url.pathname === "/api/memory/inspector/memories/conversation-only") return fulfill(route, { item: { memory_id: "conversation-only", chunks: [] } });
    if (url.pathname === "/api/memory/inspector/messages" && url.searchParams.get("conversation_id") === "conversation-only-1") return fulfill(route, { items: [{ message_id: "conversation-message-1", role: "user", occurred_at: "2026-08-28T08:03:00Z", content: "这是原始会话里的完整消息。" }] });
    if (url.pathname === "/api/memory/inspector/memories/memory-no-vector") return fulfill(route, { item: { memory_id: "memory-no-vector", chunks: [{ chunk_id: "chunk-no-vector", text: "没有语义向量也应保留正文。", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-no-vector/vector") return setTimeout(() => fulfill(route, { vector: { state: "unavailable", chunks: [] } }, 503), 500);
    if (url.pathname === "/api/memory/inspector/memories/memory-restricted/source") return fulfill(route, { detail: { code: "RESTRICTED", message: "private path /Users/owner/secret" } }, 503);
    if (url.pathname === "/api/memory/inspector/memories/memory-restricted/evidence") return fulfill(route, { memory_id: "memory-restricted", items: [{ message_id: "restricted-message", source_id: "source-restricted", conversation_id: "conversation-restricted", role: "user", sequence: 1, excerpt: "受限来源安全摘要", truncated: true }], pagination: { limit: 20, offset: 0, total: 1, has_more: false } });
    if (url.pathname === "/api/memory/inspector/memories/memory-restricted") return fulfill(route, { item: { memory_id: "memory-restricted", chunks: [{ chunk_id: "chunk-restricted", text: "受限来源正文仍可保留。", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-stale-b") return fulfill(route, { item: { memory_id: "memory-stale-b", chunks: [{ chunk_id: "chunk-stale-b", text: "B 的独特正文。", truncated: false }] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-stale-b/vector") return fulfill(route, { vector: { state: "available", chunks: [] } });
    if (url.pathname === "/api/memory/inspector/memories/memory-stale-b/source") return fulfill(route, { canonical: {}, links: [] });
    if (url.pathname === "/api/memory/inspector/memories/memory-stale-b/evidence") return fulfill(route, { memory_id: "memory-stale-b", items: [{ message_id: "b-message-1", source_id: "source-b", conversation_id: "conversation-b", role: "user", sequence: 1, excerpt: "B 独特首屏摘要", content: "B 独特首屏正文", truncated: false }], pagination: { limit: 20, offset: 0, total: 21, has_more: true } });
    if (url.pathname.startsWith("/api/memory/inspector/memories/") && actionCardsById.has(url.pathname.split("/").pop())) { const id = url.pathname.split("/").pop(); return fulfill(route, { item: { memory_id: id, chunks: [{ chunk_id: `chunk-${id}`, text: `${actionCardsById.get(id).conclusion}的正文。`, truncated: false }] } }); }
    if (url.pathname.startsWith("/api/memory/inspector/memories/") && url.pathname.endsWith("/vector") && actionCardsById.has(url.pathname.split("/").at(-2))) return fulfill(route, { vector: { state: "available", chunks: [] } });
    if (url.pathname.startsWith("/api/memory/inspector/memories/") && url.pathname.endsWith("/source") && actionCardsById.has(url.pathname.split("/").at(-2))) return fulfill(route, { canonical: {}, links: [] });
    if (url.pathname.startsWith("/api/memory/inspector/memories/") && url.pathname.endsWith("/evidence") && actionCardsById.has(url.pathname.split("/").at(-2))) return fulfill(route, { items: [], pagination: { limit: 20, offset: 0, total: 0, has_more: false } });
    if (url.pathname === "/api/memory/review/candidates/memory-action-required/approve" && request.method() === "POST" && state.mutationFail) { state.mutationFail = false; return setTimeout(() => fulfill(route, { detail: { code: "TEMPORARY", message: "delayed mutation failure" } }, 503), 500); }
    if (url.pathname.startsWith("/api/memory/review/candidates/") && request.method() === "POST") { const parts = url.pathname.split("/"); state.mutations.push({ id: parts[5], action: parts[6], body: JSON.parse(request.postData() || "{}") }); return fulfill(route, { ok: true, id: parts[5], status: parts[6] === "reject" ? "rejected" : "active" }); }
    if (url.pathname.startsWith("/api/memory/core/") && request.method() === "POST") { const parts = url.pathname.split("/"); state.mutations.push({ id: parts[4], action: parts[5], body: JSON.parse(request.postData() || "{}") }); return fulfill(route, { ok: true, id: parts[4], status: parts[5] }); }
    if (url.pathname === "/api/memory/inspector/memories/memory-long-body" && url.searchParams.get("cursor") === "chunk-long") return fulfill(route, { as_of: "2026-08-31T08:06:00Z", item: { memory_id: "memory-long-body", chunks: [{ chunk_id: "chunk-long-2", text: "长正文的继续部分。", truncated: false }], next_cursor: null } });
    if (url.pathname === "/api/memory/inspector/memories/memory-long-body") return fulfill(route, { as_of: "2026-08-31T08:05:00Z", item: { memory_id: "memory-long-body", chunks: [{ chunk_id: "chunk-long", text: "长正文的第一段。", truncated: true }], next_cursor: "chunk-long" } });
    if (url.pathname === "/api/memory/inspector/messages/message-card-1") return fulfill(route, { item: { message_id: "message-card-1", content: "这是第一页独特原文。" } });
    if (url.pathname === "/api/memory/inspector/messages/message-card-2") return fulfill(route, { item: { message_id: "message-card-2", content: "这是第二条独特原文。" } });
    if (url.pathname === "/api/memory/inspector/messages/restricted-message") return fulfill(route, { item: { message_id: "restricted-message", content: "受限来源主人显式核对后的全文。" } });
    if (url.pathname.startsWith("/api/memory/inspector/messages/") && url.pathname.split("/").pop() === "restricted-message") return fulfill(route, { item: { message_id: "restricted-message", content: "受限来源主人显式核对后的全文。" } });
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
  const provenanceText = await page.getByRole("dialog").innerText();
  assert.ok(provenanceText.includes("ChatGPT聊天记录") && provenanceText.includes("另一个来源会话"), "each evidence row must render its own source and conversation provenance");
  assert.equal(/source-chatgpt|conversation-2|chatgpt|\{"/.test(provenanceText), false, "evidence provenance must not expose internal IDs, enums, or JSON");
  await page.getByRole("dialog").getByRole("button", { name: "加载更多来源", exact: true }).click();
  assert.equal(await page.locator('[data-testid="evidence-item"]').count(), 20, "a failed next page must preserve the first page");
  await page.getByRole("dialog").getByRole("button", { name: "重试读取来源", exact: true }).click();
  await page.getByRole("dialog").locator('[data-testid="evidence-item"]').nth(37).waitFor();
  assert.equal(await page.locator('[data-testid="evidence-item"]').count(), 38, "load more must append unique evidence only");
  assert.equal(new Set(await page.locator('[data-testid="evidence-item"]').evaluateAll((nodes) => nodes.map((node) => node.textContent))).size, 38, "duplicate evidence must not duplicate DOM rows");
  assert.equal(state.requests.filter((url) => url.includes("/evidence?limit=20&offset=20")).length, 2, "retry must repeat the same next-page offset");
  assert.equal(state.requests.some((url) => url.includes("/evidence?limit=20&offset=40")), false, "load more must not fetch beyond the clicked page");
  assert.equal(await page.getByRole("dialog").getByRole("button", { name: "加载更多来源", exact: true }).count(), 0, "has_more false must hide load more");
  await page.keyboard.press("Escape");
  state.evidenceDelay = true;
  await page.getByRole("button", { name: "发布计划", exact: true }).click();
  await page.getByRole("dialog").getByRole("heading", { name: "发布计划", exact: true }).waitFor();
  await page.getByRole("dialog").locator('[data-testid="evidence-item"]').first().waitFor();
  await page.getByRole("dialog").getByRole("button", { name: "加载更多来源", exact: true }).click();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "延迟竞态普通记忆", exact: true }).click();
  await page.getByRole("dialog").getByRole("heading", { name: "延迟竞态普通记忆", exact: true }).waitFor();
  await page.getByRole("dialog").locator('[data-testid="evidence-item"]').filter({ hasText: "B 独特首屏正文" }).waitFor();
  assert.ok((await page.getByRole("dialog").innerText()).includes("B 独特首屏正文"), "B must render its unique evidence first page");
  assert.equal(await page.getByRole("dialog").getByRole("button", { name: "加载更多来源", exact: true }).count(), 1, "B must retain its own has_more/load-more state");
  await page.waitForTimeout(700);
  assert.ok(state.requests.filter((url) => url.includes("/memories/memory-card-1/evidence?limit=20&offset=20")).length >= 3, "A delayed next-page evidence request must really occur before B is checked");
  assert.equal(await page.getByRole("dialog").getByText("第 20 条来源正文。", { exact: true }).count(), 0, "delayed evidence from A must not appear after switching to B");
  assert.ok((await page.getByRole("dialog").innerText()).includes("B 独特首屏正文"), "B unique evidence must remain after A is released");
  await page.getByRole("dialog").locator("details.owner-memory-technical-details").locator("summary").click();
  const bTechnical = await page.getByRole("dialog").innerText();
  assert.ok(bTechnical.includes("记忆版本：memory-stale-b"), "selected technical identity must remain B");
  assert.equal(bTechnical.includes("memory-card-1"), false, "B detail must not expose A technical identity");
  assert.equal(await page.getByRole("dialog").getByText("来源暂时无法读取，正文不会因此消失。", { exact: true }).count(), 0, "A evidence error must not alter B evidence state");
  state.evidenceDelay = false;
  await page.keyboard.press("Escape");
  state.detailUnauthorized = true;
  await page.getByRole("button", { name: "发布计划", exact: true }).click();
  await page.getByText("请先重新连接灵机", { exact: true }).waitFor();
  await page.getByRole("button", { name: "连接恢复后重试", exact: true }).waitFor();
  state.detailUnauthorized = false;
  await page.getByRole("button", { name: "连接恢复后重试", exact: true }).click();
  await page.getByRole("dialog").getByText("灵机当前记住的内容", { exact: true }).waitFor();
  const detailText = await page.getByRole("dialog").innerText();
  for (const section of ["灵机当前记住的内容", "当前结论", "事情怎么发展", "来源与核对", "原始记录", "结构记录", "语义向量", "长期记忆", "需要不需要主人处理", "备用操作"]) assert.ok(detailText.includes(section), `detail must show ${section}`);
  assert.ok(detailText.includes("下周三发布新版。发布前完成检查清单。"), "preference/decision detail must show readable canonical content");
  assert.ok(detailText.includes("团队讨论了发布日期") && detailText.includes("确认发布前的检查清单"), "decision/progress detail must show developments");
  for (const layer of ["原始记录", "结构记录", "语义向量", "长期记忆"]) assert.ok(detailText.includes(`${layer}\n已有`), `detail must show truthful layer ${layer}`);
  assert.ok(detailText.includes("Codex聊天记录") && detailText.includes("发布计划讨论"), "detail must show readable source software and conversation identity");
  assert.equal(detailText.includes("codex_rollout"), false, "detail must not expose internal source enum");
  assert.equal(await page.getByRole("dialog").getByRole("button", { name: "删除", exact: true }).count(), 0, "detail must not expose physical deletion");
  await page.getByRole("dialog").getByRole("button", { name: "第 1 条来源摘要。", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "查看来源", exact: true }).click();
  await page.getByRole("dialog").getByText("这是第一页独特原文。", { exact: true }).waitFor();
  await page.getByRole("dialog").getByRole("button", { name: "第 2 条来源摘要。", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "查看来源", exact: true }).click();
  await page.getByRole("dialog").getByText("这是第二条独特原文。", { exact: true }).waitFor();
  assert.equal(state.requests.filter((url) => url.endsWith("/messages/message-card-1")).length, 1, "first source message must be read exactly once");
  assert.equal(state.requests.filter((url) => url.endsWith("/messages/message-card-2")).length, 1, "second source message must be read exactly once");
  await page.keyboard.press("Escape");
  state.initialEvidenceFailure = true;
  const initialEvidenceBefore = state.requests.filter((url) => url.includes("/memories/memory-card-1/evidence?limit=20&offset=0")).length;
  await page.getByRole("button", { name: "发布计划", exact: true }).click();
  await page.getByRole("dialog").getByText("来源暂时无法读取，正文不会因此消失。", { exact: true }).waitFor();
  await page.getByRole("dialog").getByRole("button", { name: "重试读取来源", exact: true }).click();
  await page.getByRole("dialog").locator('[data-testid="evidence-item"]').first().waitFor();
  assert.equal(state.requests.filter((url) => url.includes("/memories/memory-card-1/evidence?limit=20&offset=0")).length, initialEvidenceBefore + 2, "initial evidence retry must repeat bounded offset zero");
  await page.keyboard.press("Escape");
  state.canonicalFailure = true;
  const canonicalBefore = state.requests.filter((url) => url.includes("/memories/memory-card-1?chunk_limit=20&max_chars=12000")).length;
  await page.getByRole("button", { name: "发布计划", exact: true }).click();
  await page.getByRole("dialog").getByText("正文暂时无法读取，原始记录仍保留。", { exact: true }).waitFor();
  await page.getByRole("dialog").getByRole("button", { name: "重试读取正文", exact: true }).click();
  await page.getByRole("dialog").getByText("下周三发布新版。发布前完成检查清单。", { exact: true }).waitFor();
  assert.equal(state.requests.filter((url) => url.includes("/memories/memory-card-1?chunk_limit=20&max_chars=12000")).length, canonicalBefore + 2, "canonical retry must issue a bounded reread");
  await page.setViewportSize({ width: 1024, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "1024px detail must not overflow horizontally");
  await page.setViewportSize({ width: 1280, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), "1280px detail must not overflow horizontally");
  await page.getByRole("dialog").getByRole("button", { name: "查看来源", exact: true }).click();
  await page.getByRole("button", { name: "原始讨论记录", exact: true }).click();
  await page.getByRole("dialog").getByText("最新结论：原始会话尚未形成长期结论", { exact: true }).waitFor();
  await page.getByRole("dialog").getByText("这是原始会话里的完整消息。", { exact: true }).waitFor();
  const conversationText = await page.getByRole("dialog").innerText();
  for (const phrase of ["原始会话尚未形成长期结论", "原始会话保留上下文", "Codex聊天记录", "原始记录", "结构记录", "语义向量", "长期记忆"]) assert.ok(conversationText.includes(phrase), `conversation-only detail must show ${phrase}`);
  await page.waitForTimeout(700);
  assert.equal(await page.getByRole("dialog").getByText("这是旧卡片来源正文。", { exact: true }).count(), 0, "a delayed message from the previous selection must not appear in the new card");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "发布计划", exact: true }).click();
  const historyRequestCount = state.requests.filter((url) => url.includes("state=superseded")).length;
  await page.getByRole("dialog").locator("details.owner-memory-technical-details").locator("summary").click();
  assert.equal(state.requests.filter((url) => url.includes("state=superseded")).length, historyRequestCount, "history metadata must not prefetch before explicit technical click");
  await page.getByRole("dialog").getByRole("button", { name: "查看被替代的旧版本", exact: true }).click();
  await page.waitForTimeout(200);
  await page.getByRole("dialog").getByText("确定性历史记忆1", { exact: false }).waitFor();
  assert.ok(state.requests.some((url) => url.includes("/api/memory/inspector/cards?limit=20&offset=0&state=superseded")), "history metadata must use the existing superseded cards API on demand");
  await page.getByRole("dialog").getByRole("button", { name: "查看下一页旧版本", exact: true }).click();
  await page.waitForTimeout(200);
  await page.getByRole("dialog").getByText("确定性历史记忆2", { exact: false }).waitFor();
  assert.ok(state.requests.some((url) => url.includes("/api/memory/inspector/cards?limit=20&offset=20&state=superseded")), "history pagination must advance by the server page offset, not filtered matches");
  assert.equal(await page.getByRole("dialog").getByRole("button", { name: "查看下一页旧版本", exact: true }).count(), 0, "history next-page control must disappear after has_more=false");
  await page.getByRole("dialog").getByRole("button", { name: /打开历史版本：确定性历史记忆1/ }).click();
  await page.getByRole("dialog").getByRole("heading", { name: "历史结论", exact: true }).waitFor();
  const historyDetailText = await page.getByRole("dialog").innerText();
  assert.ok(historyDetailText.includes("这条历史记忆的正文"), "history detail must use a non-current body heading");
  assert.equal(historyDetailText.includes("灵机当前记住的内容"), false, "history detail must not use the current body heading");
  assert.ok(historyDetailText.includes("已由当前版本替代"), "history detail must show freshness reason");
  assert.ok(historyDetailText.includes("已由当前版本替代"), "history detail must show the owner-readable replacement relation");
  await page.getByRole("dialog").locator("details.owner-memory-technical-details").locator("summary").click();
  assert.ok((await page.getByRole("dialog").innerText()).includes("memory-card-1"), "replacement id must remain confined to the technical disclosure");
  assert.equal(historyDetailText.includes("最新结论"), false, "history detail must not label a superseded conclusion as latest");
  assert.equal(historyDetailText.includes("当前结论"), false, "history detail must not use current-conclusion semantics");
  assert.equal(await page.getByRole("dialog").getByRole("button", { name: /确认加入长期记忆|编辑确认|拒绝|修正内容|标记已经过时|移出当前记忆/ }).count(), 0, "history detail must not expose mutation actions");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "原始讨论记录", exact: true }).click();
  await page.getByRole("dialog").getByText("最新结论：原始会话尚未形成长期结论", { exact: true }).waitFor();
  assert.equal(state.requests.some((url) => url.includes("/memories/conversation-only?chunk_limit")), false, "conversation-only detail must not request canonical");
  assert.ok(state.requests.some((url) => url.includes("/api/memory/inspector/messages?conversation_id=conversation-only-1")), "conversation-only detail must use existing messages pagination");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "未准备语义检索", exact: true }).click();
  await page.getByRole("dialog").getByText("没有语义向量也应保留正文。", { exact: true }).waitFor();
  const noVectorText = await page.getByRole("dialog").innerText();
  for (const phrase of ["这是已核对的项目事实", "事实已由主人确认", "事实核对记录", "事实核对会话", "原始记录", "结构记录", "长期记忆"]) assert.ok(noVectorText.includes(phrase), `no-vector detail must show ${phrase}`);
  assert.ok(state.requests.some((url) => url.includes("/memories/memory-no-vector?chunk_limit=20&max_chars=12000")), "ordinary memory with a conversation relation must still request canonical");
  await page.getByRole("dialog").getByText("语义向量状态暂时无法确认", { exact: false }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "受限来源记忆", exact: true }).click();
  await page.getByRole("dialog").getByText("来源暂时无法读取，正文仍可保留。", { exact: true }).waitFor();
  await page.getByRole("dialog").getByText("受限来源正文仍可保留。", { exact: true }).waitFor();
  const restrictedBefore = await page.getByRole("dialog").innerText();
  for (const phrase of ["受限来源的事实摘要", "仅展示安全摘要", "受限来源", "受限事实核对", "原始记录", "结构记录", "语义向量", "长期记忆"]) assert.ok(restrictedBefore.includes(phrase), `restricted detail must show ${phrase}`);
  assert.ok(restrictedBefore.includes("受限来源安全摘要"), "restricted evidence must initially show only its safe excerpt");
  assert.equal(restrictedBefore.includes("受限来源主人显式核对后的全文"), false, "restricted full text must stay hidden before row click");
  assert.equal(state.requests.some((url) => url.endsWith("/messages/restricted-message")), false, "restricted full source must not be prefetched");
  await page.getByRole("dialog").getByRole("button", { name: "受限来源安全摘要", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "查看来源", exact: true }).click();
  await page.waitForTimeout(100);
  assert.ok((await page.getByRole("dialog").innerText()).includes("受限来源主人显式核对后的全文"), "restricted full text must appear after explicit source click");
  assert.equal(state.requests.filter((url) => url.endsWith("/messages/restricted-message")).length, 1, "restricted full source must read exactly the clicked message");
  assert.equal((await page.getByRole("dialog").innerText()).includes("/Users/owner/secret"), false, "restricted source details must not expose raw paths");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "长正文记忆", exact: true }).click();
  await page.getByRole("dialog").getByText("内容较长，下面可以继续读取正文。", { exact: true }).waitFor();
  const longText = await page.getByRole("dialog").innerText();
  for (const phrase of ["项目进展正在按计划推进", "第一阶段已经完成", "项目进展记录", "项目进展同步", "原始记录", "结构记录", "语义向量", "长期记忆"]) assert.ok(longText.includes(phrase), `long-body detail must show ${phrase}`);
  await page.getByRole("button", { name: "继续读取正文", exact: true }).click();
  await page.waitForTimeout(100);
  assert.ok(state.requests.some((url) => url.includes("/memories/memory-long-body?chunk_limit=20&max_chars=12000&cursor=chunk-long")), "continuation must request the returned canonical cursor");
  await page.getByText("长正文的继续部分。", { exact: false }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "需要主人确认", exact: true }).click();
  await page.getByRole("dialog").locator("details.owner-memory-fallback-actions").locator("summary").click();
  await page.getByRole("dialog").getByRole("button", { name: "确认加入长期记忆", exact: true }).waitFor();
  await page.getByRole("dialog").getByText("主人偏好每周一上午收到摘要的正文。", { exact: true }).waitFor();
  page.once("dialog", (dialog) => void dialog.accept());
  state.mutationFail = true;
  await page.getByRole("dialog").getByRole("button", { name: "确认加入长期记忆", exact: true }).click();
  await page.getByRole("button", { name: "原始讨论记录", exact: true }).click();
  await page.getByRole("dialog").getByText("最新结论：原始会话尚未形成长期结论", { exact: true }).waitFor();
  await page.waitForTimeout(700);
  assert.equal(await page.getByText("保存失败，请稍后重试。", { exact: true }).count(), 0, "a delayed mutation error from the previous selection must not appear after switching cards");
  await page.keyboard.press("Escape");

  const runActionFixture = async (topic, buttonName, fields = {}) => {
    await page.getByRole("button", { name: topic, exact: true }).click();
    const actionCard = actionCards.find((item) => item.topic === topic);
    const detailReadsBefore = state.requests.filter((url) => url.endsWith(`/api/memory/inspector/cards/${actionCard.memory_id}`)).length;
    const dialog = page.getByRole("dialog");
    await dialog.locator("details.owner-memory-fallback-actions").locator("summary").click();
    if (fields.edit) await dialog.getByRole("textbox", { name: fields.editLabel ?? "候选编辑内容" }).fill(fields.edit);
    if (fields.reason) await dialog.getByRole("textbox", { name: fields.reasonLabel ?? "拒绝理由" }).fill(fields.reason);
    page.once("dialog", (confirmation) => void confirmation.accept());
    await dialog.getByRole("button", { name: buttonName, exact: true }).click();
    await page.getByText("已保存，当前状态已刷新。", { exact: true }).waitFor();
    const mutation = state.mutations.at(-1);
    assert.equal(mutation.id, actionCard.memory_id, `${topic} must target its own memory`);
    assert.ok(state.requests.filter((url) => url.endsWith(`/api/memory/inspector/cards/${actionCard.memory_id}`)).length > detailReadsBefore, `${topic} must perform a fresh detail GET after success`);
    await page.keyboard.press("Escape");
    return mutation;
  };
  const approved = await runActionFixture("需要主人确认", "确认加入长期记忆");
  assert.equal(approved.action, "approve"); assert.equal(approved.body.expected_content_hash, "hash-memory-card-1");
  const edited = await runActionFixture("生命周期校验卡片B", "编辑确认", { edit: "主人编辑后的偏好", editLabel: "候选编辑内容" });
  assert.equal(edited.action, "edit-approve"); assert.equal(edited.body.content, "主人编辑后的偏好");
  const rejected = await runActionFixture("生命周期校验卡片C", "拒绝", { reason: "主人不接受此候选" });
  assert.equal(rejected.action, "reject"); assert.equal(rejected.body.reason, "主人不接受此候选");
  const corrected = await runActionFixture("生命周期校验卡片D", "修正内容", { edit: "修正后的事实", editLabel: "修正内容", reason: "主人核对后修正", reasonLabel: "修正原因" });
  assert.equal(corrected.action, "correct"); assert.equal(corrected.body.content, "修正后的事实"); assert.equal(corrected.body.reason, "主人核对后修正");
  const invalidated = await runActionFixture("生命周期校验卡片E", "标记已经过时", { reason: "证据已经过期", reasonLabel: "过时原因" });
  assert.equal(invalidated.action, "invalidate"); assert.equal(invalidated.body.reason, "证据已经过期");
  const archived = await runActionFixture("生命周期校验卡片F", "移出当前记忆", { reason: "不再属于当前范围", reasonLabel: "移出原因" });
  assert.equal(archived.action, "archive"); assert.equal(archived.body.reason, "不再属于当前范围");

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
