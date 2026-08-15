import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  panel, currentWork, overview, workFeed, attention, codex, api, discovery, imports, styles,
  boundary, connection, bootstrap, autopilotEngine, autopilotApi, runtimeEntrypoint,
] = await Promise.all([
  read("../src/components/AssistantDiscoveryPanel.tsx"),
  read("../src/components/CurrentWorkPanel.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/ownerWorkFeed.ts"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/pages/CodexWorkspacePage.tsx"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/discovery.py"),
  read("../../../src/assistant_hub/imports.py"),
  read("../src/AssistantAutopilot.css"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src-tauri/src/runtime_bootstrap.rs"),
  read("../../../src/autopilot/engine.py"),
  read("../../../src/control/autopilot_api.py"),
  read("../../../run_control_api.py"),
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
assert.match(currentWork, /if \(!activity && pendingReviewCount === 0 && !resource\.error\) return null/);
assert.match(currentWork, /当前真实任务/);
assert.match(currentWork, /current-work-details/);

assert.match(overview, /\/api\/autopilot\/status/);
assert.match(overview, /autopilot\.owner_actions/);
assert.match(overview, /AI 历史等待你授权读取/);
assert.match(overview, /候选记忆等待你确认/);
assert.match(overview, /向量索引是否重建需要你确认/);
assert.match(overview, /你现在需要做什么/);
assert.match(overview, /灵机现在在做什么/);
assert.match(overview, /资料工作清单/);
assert.match(overview, /buildOwnerWorkFeed/);
assert.match(workFeed, /ownerActionRequired/);
assert.match(workFeed, /需要你确认这条候选是否保留/);
assert.equal(overview.includes("buildWorkflow"), false, "Autopilot home must not use aggregate stage cards as the primary story");
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

assert.match(autopilotEngine, /class AutopilotEngine/);
assert.match(autopilotEngine, /StartupHealthChecker/);
assert.match(autopilotEngine, /release_stale/);
assert.match(autopilotEngine, /vector_rebuild_required/);
assert.match(autopilotEngine, /不会自动执行不可逆操作/);
assert.match(autopilotEngine, /不会无限循环/);
assert.equal(autopilotEngine.includes(".retry("), false, "Autopilot must not retry exhausted/cancelled jobs indefinitely");
assert.equal(autopilotEngine.includes("rebuild_collection"), false, "Autopilot must not silently rebuild Qdrant");
assert.equal(autopilotEngine.includes("approve_memory"), false, "Autopilot must not approve permanent memory");

assert.match(autopilotApi, /\/api\/autopilot\/status/);
assert.match(autopilotApi, /x_lingji_token/);
assert.equal(autopilotApi.includes("@app.post"), false, "Phase 4 Autopilot API is read-only");

assert.match(runtimeEntrypoint, /AutopilotEngine/);
assert.match(runtimeEntrypoint, /register_autopilot_routes/);
assert.match(runtimeEntrypoint, /autopilot\.start\(\)/);
assert.match(runtimeEntrypoint, /autopilot\.stop\(\)/);
assert.match(runtimeEntrypoint, /finally:/);

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
