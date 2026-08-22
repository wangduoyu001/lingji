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
for (const label of ["运行状态", "活动记录", "需要我处理", "高级诊断"]) {
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
assert.match(boundary, /OWNER PAUSED/);
assert.match(boundary, /AUTO RECOVERY/);
assert.match(boundary, /DATA ROOT REQUIRED/);
assert.match(boundary, /保存配置并启动核心/);
assert.equal(
  boundary.includes(">启动核心</button>"),
  false,
  "Routine offline banner must not expose a standalone start-core button",
);

assert.match(connection, /setTimeout\(\(\) => void ensureConnection\(false\), 12_000\)/);
assert.match(connection, /ownerStopped/);
assert.match(connection, /autoRecoveryActive/);
assert.match(connection, /后台自动恢复已暂停/);

assert.match(overview, /状态每 10 秒自动更新/);
assert.match(overview, /后台自动运行/);
assert.match(overview, /查看待办/);
assert.equal(overview.includes("刷新本机状态"), false, "Overview must not require manual refresh");
assert.equal(overview.includes("健康检查"), false, "Detailed health checks belong in diagnostics");
assert.equal(overview.includes("本地 Provider"), false, "Provider internals belong in diagnostics");
assert.equal(overview.includes("定时任务"), false, "Scheduler internals belong in diagnostics");

// Activity is now a direct projection of the canonical Work Fact endpoint.
assert.match(activity, /\/api\/work\/current/);
assert.match(activity, /intervalMs: 5000/);
assert.match(activity, /当前工作事实/);
assert.match(activity, /执行事件/);
assert.match(activity, /Work ID/);
assert.match(activity, /当前状态未知/);
assert.equal(activity.includes("刷新看板"), false, "Activity page must not expose manual refresh");
assert.equal(activity.includes("/api/jobs"), false, "Activity must not reconstruct work semantics from generic jobs");
assert.equal(activity.includes("/api/codex/current"), false, "Activity must not reconstruct work semantics from Codex status");

// Owner attention only contains unresolved canonical PendingAction facts.
assert.match(attention, /\/api\/work\/pending-actions/);
assert.match(attention, /intervalMs: 8000/);
assert.match(attention, /需要主人处理/);
assert.match(attention, /当前没有需要主人决定的事项/);
assert.match(attention, /不能按 0 项处理/);
assert.match(attention, /action\.action_id/);
assert.match(attention, /action\.work_id/);
assert.equal(attention.includes("vector-rebuild"), false, "Vector diagnostics must not masquerade as owner work without PendingAction");
assert.equal(attention.includes("pending_review_count"), false, "Aggregated review counts must not become a second owner-task truth");
assert.equal(attention.includes("/api/auto-review/metrics"), false, "Cumulative SHADOW metrics must not masquerade as unresolved owner tasks");

assert.match(diagnostics, /日常不需要进入这里/);
assert.match(diagnostics, /<details/);
assert.match(diagnostics, /ADVANCED_NAVIGATION/);

assert.match(currentWork, /\/api\/work\/current/);
assert.match(currentWork, /intervalMs: 5000/);
assert.match(currentWork, /当前没有进行中的工作/);
assert.match(currentWork, /不能把接口不可用当成“没有工作”/);
assert.match(currentWork, /work\?\.work_id/);
assert.match(currentWork, /event\.event_id/);
assert.match(currentWork, /event\.event_type/);

for (const cssToken of [
  ".observation-hero",
  ".attention-summary",
  ".activity-timeline",
  ".attention-card",
  ".diagnostics-group",
  ".current-work-summary",
]) assert.ok(desktopCss.includes(cssToken), `Desktop observation styles are missing ${cssToken}`);
assert.match(releaseCss, /\.desktop-runtime-tools/);

console.log("observation-first-ui-smoke: PASS");
