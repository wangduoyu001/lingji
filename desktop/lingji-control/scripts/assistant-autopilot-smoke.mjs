import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [panel, currentWork, overview, attention, codex, api, discovery, imports, styles, boundary, connection, bootstrap] = await Promise.all([
  read("../src/components/AssistantDiscoveryPanel.tsx"),
  read("../src/components/CurrentWorkPanel.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/pages/CodexWorkspacePage.tsx"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/discovery.py"),
  read("../../../src/assistant_hub/imports.py"),
  read("../src/AssistantAutopilot.css"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src-tauri/src/runtime_bootstrap.rs"),
]);

assert.match(panel, /\/api\/assistant-hub\/status/);
assert.match(panel, /intervalMs: 15_000/);
assert.match(panel, /已自动接管/);
assert.match(panel, /元数据会在后台持续同步/);
assert.match(panel, /允许读取，后面自动处理/);
assert.match(panel, /AUTHORIZE_ASSISTANT_IMPORT_/);
assert.match(panel, /AUTHORIZE_SELECTED_ASSISTANT_IMPORT/);
assert.match(panel, /onOwnerDecisionCount/);
assert.match(panel, /来源详情与手动导入/);
assert.match(panel, /元数据自动读取/);
assert.match(panel, /正文读取需授权/);
assert.match(panel, /永久记忆需审核/);
assert.equal(panel.includes("assistant-autopilot-summary"), false, "Discovery summary tiles must not dominate the daily UI");
assert.equal(panel.includes("setInterval"), false, "Assistant discovery should reuse the polling resource");

assert.match(currentWork, /onPendingReviewCount/);
assert.match(currentWork, /Codex 工作记录/);
assert.match(currentWork, /没有前台任务；自动发现、状态检查和维护仍在后台继续/);
assert.match(currentWork, /current-work-details/);

assert.match(overview, /owner-autopilot-home/);
assert.match(overview, /ownerDecisionCount/);
assert.match(overview, /systemIssueCount/);
assert.match(overview, /没有需要你操作的事项/);
assert.match(overview, /灵机会先自行重试、恢复和保留证据/);
assert.equal(overview.includes("overview-technical-summary"), false, "Daily home must not expose the technical metric dashboard");
assert.equal(overview.includes("Metric"), false, "Daily home must not render technical metric tiles");

assert.match(attention, /\/api\/assistant-hub\/status/);
assert.match(attention, /AI 历史资料等待读取授权/);
assert.match(attention, /是否重建向量索引需要确认/);
assert.match(attention, /普通故障、重试和诊断不再混进你的决策数量/);
assert.match(attention, /系统异常与自动处理/);
assert.match(attention, /你现在不用做任何决定/);

assert.match(codex, /Codex 工作记录/);
assert.match(codex, /不是灵机新建了聊天窗口/);
assert.match(codex, /已识别工作记录/);
assert.match(codex, /15_000/);
assert.equal(codex.includes("<h2>项目对话</h2>"), false);

assert.match(boundary, /自动准备未完成/);
assert.match(boundary, /让灵机重新自动准备/);
assert.match(boundary, /手动选择位置/);
assert.equal(boundary.includes("选择一个位置存放灵机资料"), false, "Normal first launch must not require manual storage selection");
assert.match(connection, /runtime_autoconfigure/);
assert.match(connection, /automaticBootstrap/);
assert.match(bootstrap, /LINGJI_ACCEPTANCE_DATA_ROOT/);
assert.match(bootstrap, /configure_default/);
assert.match(bootstrap, /auto_selected/);
assert.match(bootstrap, /persisted acceptance workspace is never reused/);

for (const route of [
  "/api/assistant-hub/status",
  "/api/assistant-hub/scan",
  "/api/assistant-hub/import-plan",
  "/api/assistant-hub/import-candidates/{candidate_id}/authorize",
  "/api/assistant-hub/import-selected-file",
]) assert.ok(api.includes(route), `Missing assistant autopilot route ${route}`);

assert.match(discovery, /content_read": False/);
assert.match(discovery, /followlinks=False/);
assert.match(discovery, /\.codex/);
assert.match(discovery, /\.claude/);
assert.match(imports, /_MAX_SCAN_DEPTH = 2/);
assert.match(imports, /candidate_id/);
assert.match(imports, /resolve_authorized_candidate/);

for (const token of [
  ".assistant-autopilot-panel",
  ".assistant-autopilot-passive",
  ".assistant-passive-row",
  ".owner-only-source-action",
  ".current-work-inline-facts",
  ".current-work-details",
  ".attention-system-details",
  ".runtime-advanced-setup",
  ".runtime-manual-fallback",
  ".codex-session-explainer",
]) assert.ok(styles.includes(token), `Missing assistant autopilot style ${token}`);

console.log("assistant-autopilot-smoke: PASS");
