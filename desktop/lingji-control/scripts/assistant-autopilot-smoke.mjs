import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [overview, attention, command, codex, api, discovery, imports, boundary, connection, bootstrap, autopilotEngine, autopilotApi, runtimeEntrypoint] = await Promise.all([
  read("../src/pages/OverviewPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/components/GlobalOwnerCommand.tsx"),
  read("../src/pages/CodexWorkspacePage.tsx"),
  read("../../../src/control/capture_api.py"),
  read("../../../src/assistant_hub/discovery.py"),
  read("../../../src/assistant_hub/imports.py"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src-tauri/src/runtime_bootstrap.rs"),
  read("../../../src/autopilot/engine.py"),
  read("../../../src/control/autopilot_api.py"),
  read("../../../run_control_api.py"),
]);

assert.match(overview, /\/api\/assistant-hub\/status/);
assert.match(overview, /detectedAssistants/);
assert.match(overview, /主动发现/);
assert.match(overview, /发现不等于已授权、已接管或已执行/);
assert.match(overview, /\/api\/memory\/review\/candidates/);
assert.match(overview, /buildOwnerAttentionItems/);
assert.match(overview, /hasReviewConsistencyIssue/);
assert.match(overview, /ownerAttentionSummary/);
assert.match(overview, /\/api\/capture\/jobs\?limit=24&offset=0/);
assert.match(overview, /有 WorkItem 才显示结果/);
assert.equal(overview.includes("已发现 ${detectedAssistants.length} 个可接管工具"), false, "Detection must not be presented as takeover");
assert.equal(overview.includes("buildWorkflow"), false, "Home must not use aggregate stage cards");
assert.equal(overview.includes("Metric"), false, "Home must not render technical metric tiles");

assert.match(attention, /\/api\/assistant-hub\/status/);
assert.match(attention, /\/api\/memory\/review\/candidates/);
assert.match(attention, /import-candidates\/\$\{encodeURIComponent\(item\.candidate\.candidate_id\)\}\/authorize/);
assert.match(attention, /AUTHORIZE_ASSISTANT_IMPORT_/);
assert.match(attention, /读取正文会跨过隐私边界/);
assert.match(attention, /所以停下来等你/);
assert.match(attention, /灵机自己处理/);
assert.match(attention, /不把运维工作冒充成主人待办/);
assert.equal(attention.includes("pending_review_count"), false, "Owner inbox must not create actions from a summary count");

assert.match(command, /\/api\/capture\/text/);
assert.match(command, /source_type: "text"/);
assert.match(command, /owner_command_bar/);
assert.match(command, /资料 \$\{captureId\}/);
assert.match(command, /处理任务 \$\{jobId\}/);
assert.match(command, /记忆结果以“记忆”页面的真实证据为准/);
assert.match(command, /当前全局入口只执行可验证的记录和导航指令/);

assert.match(codex, /Codex 工作记录/);
assert.match(codex, /不是灵机新建了聊天窗口/);
assert.match(codex, /已识别工作记录/);
assert.match(codex, /15_000/);

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
assert.equal(autopilotApi.includes("@app.post"), false, "Autopilot API remains read-only");
assert.match(runtimeEntrypoint, /AutopilotEngine/);
assert.match(runtimeEntrypoint, /register_autopilot_routes/);
assert.match(runtimeEntrypoint, /autopilot\.start\(\)/);
assert.match(runtimeEntrypoint, /autopilot\.stop\(\)/);

for (const route of [
  "/api/assistant-hub/status",
  "/api/assistant-hub/scan",
  "/api/assistant-hub/import-plan",
  "/api/assistant-hub/import-candidates/{candidate_id}/authorize",
  "/api/assistant-hub/import-selected-file",
]) assert.ok(api.includes(route), `Missing assistant route ${route}`);

assert.match(discovery, /content_read": False/);
assert.match(discovery, /followlinks=False/);
assert.match(discovery, /\.codex/);
assert.match(discovery, /\.claude/);
assert.match(imports, /_MAX_SCAN_DEPTH = 2/);
assert.match(imports, /candidate_id/);
assert.match(imports, /resolve_authorized_candidate/);

console.log("assistant-autopilot-smoke: PASS");
