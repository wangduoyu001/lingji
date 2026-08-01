import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [
  navigation,
  types,
  shell,
  app,
  boundary,
  autopilot,
  pages,
  overview,
  startCenter,
  activity,
  attention,
  diagnostics,
  connection,
  currentWork,
  desktopCss,
  autopilotCss,
  releaseCss,
] = await Promise.all([
  read("../src/navigation.ts"),
  read("../src/types.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/App.tsx"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/components/AutopilotStatusBar.tsx"),
  read("../src/AppPages.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/components/StartCenterPanel.tsx"),
  read("../src/pages/ActivityPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/pages/DiagnosticsPage.tsx"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src/components/CurrentWorkPanel.tsx"),
  read("../src/DesktopUX.css"),
  read("../src/components/AutopilotStatusBar.css"),
  read("../src/ReleaseUX.css"),
]);

for (const page of ["overview", "activity", "attention", "diagnostics"]) {
  assert.ok(types.includes(`| "${page}"`), `PageId is missing ${page}`);
  assert.ok(navigation.includes(`id: "${page}"`), `Primary navigation is missing ${page}`);
  assert.ok(pages.includes(`page === "${page}"`), `AppPages is missing ${page}`);
}

const primaryBlock = navigation.match(/PRIMARY_NAVIGATION:[\s\S]*?\];/)?.[0] ?? "";
assert.equal((primaryBlock.match(/id:/g) ?? []).length, 4, "Primary navigation must contain exactly four entries");
for (const label of ["开始使用", "活动记录", "需要我处理", "高级诊断"]) {
  assert.ok(primaryBlock.includes(label), `Primary navigation is missing ${label}`);
}
for (const forbiddenId of ["assistant_hub", "memory_review", "auto_review", "vector_center", "system_compute", "settings", "logs"]) {
  assert.equal(primaryBlock.includes(`id: "${forbiddenId}"`), false, `${forbiddenId} must not remain a primary navigation entry`);
}

assert.match(shell, /PRIMARY_NAVIGATION\.map/);
assert.equal(shell.includes("NAVIGATION.filter"), false, "Desktop sidebar must not render every advanced page");
assert.match(shell, /desktop-runtime-tools/);
assert.match(shell, /<details/);
assert.match(shell, /返回高级诊断/);

assert.match(app, /autoRecoveryActive/);
assert.match(app, /RuntimeBoundary/);
assert.match(app, /AutopilotStatusBar/);
assert.match(app, /bindingVerification/);
assert.match(app, /autopilotStatus/);

assert.match(boundary, /OWNER PAUSED/);
assert.match(boundary, /AUTO RECOVERY/);
assert.match(boundary, /MANUAL FALLBACK/);
assert.match(boundary, /灵机没有找到可自动使用的非 C 盘目录/);
assert.match(boundary, /确认备用目录/);
assert.equal(
  boundary.includes(">启动核心</button>"),
  false,
  "Routine offline banner must not expose a standalone start-core button",
);

for (const token of [
  "UI只展示状态和进度",
  "DataRoot绑定已验证",
  "当前DataRoot",
  "等待主人授权",
]) assert.ok(autopilot.includes(token), `Autopilot status bar is missing ${token}`);

for (const token of [
  "runtime_auto_configure",
  "runtime_binding_verification",
  "/api/assistant-hub/scan",
  "/api/models/refresh",
  "/api/hardware/refresh",
  "runSafeAutopilot",
]) assert.ok(connection.includes(token), `Connection autopilot is missing ${token}`);
assert.match(connection, /setTimeout\(\(\) => void ensureConnection\(false\), 12_000\)/);
assert.match(connection, /ownerStopped/);
assert.match(connection, /autoRecoveryActive/);
assert.match(connection, /后台自动恢复已暂停/);

assert.match(overview, /状态每 10 秒自动更新/);
assert.match(overview, /StartCenterPanel/);
assert.equal(overview.includes("刷新本机状态"), false, "Overview must not require manual refresh");
assert.equal(overview.includes("健康检查"), false, "Detailed health checks belong in diagnostics");
assert.equal(overview.includes("本地 Provider"), false, "Provider internals belong in diagnostics");
assert.equal(overview.includes("定时任务"), false, "Scheduler internals belong in diagnostics");

for (const token of [
  "灵机当前处理重点",
  "这是查看入口，不影响后台继续运行",
  "灵机自动发现",
  "等待授权来源",
  "查看连接与授权",
]) assert.ok(startCenter.includes(token), `Start center autonomy contract is missing ${token}`);
assert.equal(startCenter.includes("唯一推荐下一步"), false, "Start center must not present the owner as the workflow operator");
assert.equal(
  startCenter.includes("配置存在但尚未激活；全文检索仍可用，后续从向量中心处理"),
  false,
  "Ambiguous vector guidance must not return",
);

assert.match(activity, /每 4 秒自动更新/);
assert.match(activity, /当前任务/);
assert.match(activity, /最近结果/);
assert.equal(activity.includes("刷新看板"), false, "Activity page must not expose manual refresh");

assert.match(attention, /系统不能自行决定/);
assert.match(attention, /暂时不需要你处理/);
assert.match(attention, /部分待办状态暂时未知/);
assert.match(attention, /不会把未知状态显示成一切正常/);
assert.match(attention, /vector-rebuild/);
assert.match(attention, /pending_review_count/);
assert.match(attention, /SHADOW 决策目前是审计历史/);
assert.equal(attention.includes("/api/auto-review/metrics"), false, "Cumulative SHADOW metrics must not masquerade as unresolved owner tasks");
assert.equal(attention.includes("catch {\n      return { current: null }"), false, "Attention polling must not swallow unknown-state failures");

assert.match(diagnostics, /日常不需要进入这里/);
assert.match(diagnostics, /<details/);
assert.match(diagnostics, /ADVANCED_NAVIGATION/);

assert.match(currentWork, /intervalMs: 5_000/);
assert.match(currentWork, /系统当前空闲/);
assert.match(currentWork, /处理进度/);

for (const cssToken of [
  ".observation-hero",
  ".attention-summary",
  ".activity-timeline",
  ".attention-card",
  ".diagnostics-group",
  ".current-work-summary",
]) assert.ok(desktopCss.includes(cssToken), `Desktop observation styles are missing ${cssToken}`);
for (const cssToken of [".autopilot-status-bar", ".autopilot-binding-details"]) {
  assert.ok(autopilotCss.includes(cssToken), `Autopilot styles are missing ${cssToken}`);
}
assert.match(releaseCss, /\.desktop-runtime-tools/);

console.log("observation-first-ui-smoke: PASS");
