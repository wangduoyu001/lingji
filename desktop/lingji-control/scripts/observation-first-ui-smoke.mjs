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
  activity,
  attention,
  diagnostics,
  connection,
  currentWork,
  desktopCss,
  releaseCss,
] = await Promise.all([
  read("../src/navigation.ts"),
  read("../src/types.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/App.tsx"),
  read("../src/components/RuntimeBoundary.tsx"),
  read("../src/AppPages.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/pages/ActivityPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/pages/DiagnosticsPage.tsx"),
  read("../src/hooks/useLingJiConnection.ts"),
  read("../src/components/CurrentWorkPanel.tsx"),
  read("../src/DesktopUX.css"),
  read("../src/ReleaseUX.css"),
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
assert.match(boundary, /自动恢复/);
assert.match(boundary, /首次使用/);
assert.match(boundary, /选择一个位置存放灵机资料/);
assert.match(boundary, /开始使用灵机/);
assert.match(boundary, /runtime-advanced-setup/);
assert.equal(boundary.includes("先选择非 C 盘数据目录"), false, "Mac first-use copy must not be Windows-only");

assert.match(connection, /setTimeout\(\(\) => void ensureConnection\(false\), 12_000\)/);
assert.match(connection, /ownerStopped/);
assert.match(connection, /autoRecoveryActive/);
assert.match(connection, /后台自动恢复已暂停/);

assert.match(overview, /灵机自动驾驶/);
assert.match(overview, /AssistantDiscoveryPanel/);
assert.match(overview, /ownerDecisionCount/);
assert.match(overview, /systemIssueCount/);
assert.match(overview, /不会冒充成你的决策/);
assert.match(overview, /overview-technical-summary/);
assert.equal(overview.includes("刷新本机状态"), false, "Overview must not require manual refresh");
assert.equal(overview.includes("健康检查"), false, "Detailed health checks belong in diagnostics");

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
assert.match(currentWork, /系统当前空闲/);
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
assert.match(releaseCss, /\.desktop-runtime-tools/);

console.log("observation-first-ui-smoke: PASS");
