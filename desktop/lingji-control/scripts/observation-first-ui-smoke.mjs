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
  pages,
  overview,
  workFeed,
  activity,
  attention,
  diagnostics,
  connection,
  currentWork,
  desktopCss,
  releaseCss,
  autopilotCss,
  ownerWorkCss,
] = await Promise.all([
  read("../src/navigation.ts"),
  read("../src/types.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/App.tsx"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/AppPages.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/ownerWorkFeed.ts"),
  read("../src/pages/ActivityPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/pages/DiagnosticsPage.tsx"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src/components/CurrentWorkPanel.tsx"),
  read("../src/DesktopUX.css"),
  read("../src/ReleaseUX.css"),
  read("../src/AssistantAutopilot.css"),
  read("../src/OwnerWorkFeed.css"),
]);

for (const page of ["overview", "activity", "attention", "diagnostics"]) {
  assert.ok(types.includes(`| "${page}"`), `PageId is missing ${page}`);
  assert.ok(navigation.includes(`id: "${page}"`), `Primary navigation is missing ${page}`);
  assert.ok(pages.includes(`page === "${page}"`), `AppPages is missing ${page}`);
}

const primaryBlock = navigation.match(/PRIMARY_NAVIGATION:[\s\S]*?\];/)?.[0] ?? "";
assert.equal((primaryBlock.match(/id:/g) ?? []).length, 4, "Primary navigation must contain exactly four entries");
for (const label of ["首页", "正在做什么", "需要我决定", "高级工具"]) {
  assert.ok(primaryBlock.includes(label), `Primary navigation is missing ${label}`);
}
for (const forbiddenId of ["memory_review", "auto_review", "vector_center", "system_compute", "settings", "logs"]) {
  assert.equal(primaryBlock.includes(`id: "${forbiddenId}"`), false, `${forbiddenId} must not remain a primary navigation entry`);
}

assert.match(shell, /PRIMARY_NAVIGATION\.map/);
assert.equal(shell.includes("NAVIGATION.filter"), false, "Desktop sidebar must not render every advanced page");
assert.match(shell, /desktop-runtime-tools/);
assert.match(shell, /<details/);
assert.match(shell, /返回高级诊断/);

assert.match(app, /autoRecoveryActive/);
assert.match(app, /RuntimeBoundary/);
assert.match(app, /OwnerWorkFeed\.css/);
assert.equal(app.includes("OwnerHomeV2.css"), false, "Failed Owner Home v2 stylesheet must not remain active");
assert.match(boundary, /自动恢复/);
assert.match(boundary, /自动准备未完成/);
assert.match(boundary, /让灵机重新自动准备/);
assert.match(boundary, /手动选择位置/);
assert.match(boundary, /runtime-advanced-setup/);
assert.equal(boundary.includes("首次使用"), false, "Normal first launch must not be framed as a manual setup wizard");
assert.equal(boundary.includes("选择一个位置存放灵机资料"), false, "Manual storage selection must be fallback-only");

assert.match(connection, /runtime_autoconfigure/);
assert.match(connection, /automaticBootstrap/);
assert.match(connection, /setTimeout\(\(\) => void ensureConnection\(false\), 12_000\)/);
assert.match(connection, /ownerStopped/);
assert.match(connection, /autoRecoveryActive/);
assert.match(connection, /后台自动恢复已暂停/);

assert.match(overview, /owner-work-home/);
assert.match(overview, /你现在需要做什么/);
assert.match(overview, /灵机现在在做什么/);
assert.match(overview, /资料工作清单/);
assert.match(overview, /每一份资料，都说清楚做到哪了/);
assert.match(overview, /灵机已做/);
assert.match(overview, /下一步/);
assert.match(overview, /现在不用你做任何事/);
assert.match(overview, /\/api\/memory\/inspector\/memories\?limit=20&offset=0/);
assert.match(overview, /buildOwnerWorkFeed/);
assert.match(overview, /feed\.detailsState === "unavailable"/);
assert.match(overview, /需要你处理/);
assert.match(overview, /系统统计与高级状态/);
assert.match(overview, /AssistantDiscoveryPanel/);
assert.match(overview, /CurrentWorkPanel/);
assert.equal(overview.includes("buildWorkflow"), false, "Aggregate seven-stage cards must not remain the home primary structure");
assert.equal(overview.includes("autopilot-flow-surface"), false, "Failed seven-stage home surface must be removed");
assert.equal(overview.includes("overview-technical-summary"), false, "Technical health dashboard must not remain on the daily home surface");
assert.equal(overview.includes("Metric"), false, "Daily home must not render a grid of technical metrics");
assert.equal(overview.includes("刷新本机状态"), false, "Overview must not require manual refresh");

assert.match(workFeed, /memory\.title/);
assert.match(workFeed, /resultLinks/);
assert.match(workFeed, /ownerActionRequired/);
assert.match(workFeed, /灵机不会用一个数字代替资料列表/);
assert.match(workFeed, /safeRelativePath/);
assert.match(workFeed, /safeFilename/);
assert.equal(workFeed.includes("payload.text"), false, "Owner feed must not project captured body text");
assert.equal(workFeed.includes("raw_snapshot"), false, "Owner feed must not project raw snapshot paths");

assert.match(activity, /每 4 秒自动更新/);
assert.match(activity, /当前任务/);
assert.match(activity, /最近结果/);
assert.equal(activity.includes("刷新看板"), false, "Activity page must not expose manual refresh");

assert.match(attention, /暂时不需要你决定/);
assert.match(attention, /部分决策状态暂时未知/);
assert.match(attention, /不会把未知状态显示成一切正常/);
assert.match(attention, /assistant-import-authorization/);
assert.match(attention, /vector-rebuild/);
assert.match(attention, /pending_review_count/);
assert.match(attention, /系统异常与自动处理/);
assert.match(attention, /普通故障、重试和诊断不再混进你的决策数量/);

assert.match(diagnostics, /日常不需要进入这里/);
assert.match(diagnostics, /<details/);
assert.match(diagnostics, /ADVANCED_NAVIGATION/);

assert.match(currentWork, /intervalMs: 5_000/);
assert.match(currentWork, /if \(!activity && pendingReviewCount === 0 && !resource\.error\) return null/);
assert.match(currentWork, /当前真实任务/);
assert.match(currentWork, /current-work-progress/);
assert.match(currentWork, /aria-label={`任务进度/);
assert.match(currentWork, /onPendingReviewCount/);
assert.match(currentWork, /工作细节/);

for (const cssToken of [
  ".observation-hero",
  ".attention-summary",
  ".activity-timeline",
  ".attention-card",
  ".diagnostics-group",
]) assert.ok(desktopCss.includes(cssToken), `Desktop observation styles are missing ${cssToken}`);
for (const cssToken of [
  ".assistant-autopilot-passive",
  ".assistant-passive-row",
  ".autopilot-background-issue",
  ".runtime-manual-fallback",
]) assert.ok(autopilotCss.includes(cssToken), `Autopilot styles are missing ${cssToken}`);
for (const cssToken of [
  ".owner-action-hero",
  ".owner-now-card",
  ".owner-work-list",
  ".owner-work-item",
  ".owner-work-fact",
  ".owner-work-stats",
]) assert.ok(ownerWorkCss.includes(cssToken), `Owner Work Feed styles are missing ${cssToken}`);
assert.equal(ownerWorkCss.includes("repeat(7"), false, "Owner home must not return to a seven-card stage grid");
assert.match(releaseCss, /\.desktop-runtime-tools/);

console.log("observation-first-ui-smoke: PASS");
