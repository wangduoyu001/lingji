import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [navigation, types, shell, app, pages, overview, memory, activity, attention, command, inspector, review, capture, css, workFeed] = await Promise.all([
  read("../src/navigation.ts"),
  read("../src/types.ts"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/App.tsx"),
  read("../src/AppPages.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/pages/MemoryHomePage.tsx"),
  read("../src/pages/ActivityPage.tsx"),
  read("../src/pages/AttentionPage.tsx"),
  read("../src/components/GlobalOwnerCommand.tsx"),
  read("../src/pages/MemoryInspectorPage.tsx"),
  read("../src/pages/MemoryReviewPage.tsx"),
  read("../src/pages/CaptureCenterPage.tsx"),
  read("../src/WorkbenchV4.css"),
  read("../src/ownerWorkFeed.ts"),
]);

for (const page of ["overview", "memory", "activity", "attention", "diagnostics"]) {
  assert.ok(types.includes(`| "${page}"`), `PageId is missing ${page}`);
  assert.ok(navigation.includes(`id: "${page}"`), `Primary navigation is missing ${page}`);
  assert.ok(pages.includes(`page === "${page}"`), `AppPages is missing ${page}`);
}
const primaryBlock = navigation.match(/PRIMARY_NAVIGATION:[\s\S]*?\];/)?.[0] ?? "";
assert.equal((primaryBlock.match(/id:/g) ?? []).length, 5, "V4 primary navigation must contain exactly five entries");
for (const label of ["首页", "记忆", "工作", "需要我", "高级"]) assert.ok(primaryBlock.includes(label));
for (const forbiddenId of ["memory_review", "auto_review", "vector_center", "system_compute", "settings", "logs"]) assert.equal(primaryBlock.includes(`id: "${forbiddenId}"`), false);

assert.match(app, /WorkbenchV4\.css/);
assert.match(shell, /第二永久记忆大脑/);
assert.match(shell, /GlobalOwnerCommand/);
assert.match(shell, /运行与诊断详情/);
assert.match(shell, /<details className="desktop-runtime-tools v4-runtime-details"/);
assert.equal(shell.includes("desktop-release-line"), false, "Release internals must not dominate the daily sidebar");

for (const token of ["现在需要你吗", "刚刚替你做了什么", "现在正在做什么", "接下来灵机会做什么", "记忆发生了什么变化", "主动发现"]) assert.ok(overview.includes(token), `Home is missing ${token}`);
for (const route of ["/api/memory/review/candidates", "/api/assistant-hub/status", "/api/codex/current", "/api/memory/inspector/memories"]) assert.ok(overview.includes(route), `Home is missing real source ${route}`);
assert.match(overview, /reviewMismatch/);
assert.match(overview, /不会给你一个会打开空页面的“去处理”按钮/);
assert.match(overview, /buildOwnerWorkFeed/);
assert.equal(overview.includes("CurrentWorkPanel"), false);
assert.equal(overview.includes("AssistantDiscoveryPanel"), false);
assert.equal(overview.includes("Metric"), false);
assert.equal(overview.includes("buildWorkflow"), false);

for (const token of ["第二永久记忆大脑", "灵机到底记住了什么", "记住了什么", "为什么能相信它", "来源证据", "记忆缺口"]) assert.ok(memory.includes(token), `Memory home is missing ${token}`);
assert.match(memory, /\/api\/memory\/inspector\/memories/);
assert.match(memory, /\/api\/memory\/inspector\/status/);
assert.match(memory, /\/source/);
assert.match(memory, /\/vector/);
assert.match(memory, /disabled={!pagination\?\.has_more}/);
assert.match(memory, /来源路径未公开/);
assert.match(memory, /没有证据时，灵机不会拿通用模板猜/);

for (const token of ["工作履历", "发生了什么", "灵机做了什么", "结果", "下一步", "技术记录"]) assert.ok(activity.includes(token), `Work history is missing ${token}`);
assert.match(activity, /\/api\/jobs\?limit=80/);
assert.match(activity, /\/api\/codex\/current/);

for (const token of ["需要我", "真实待办", "每个按钮背后都有一个真实对象", "灵机自己处理"]) assert.ok(attention.includes(token), `Owner inbox is missing ${token}`);
assert.match(attention, /\/api\/memory\/review\/candidates/);
assert.match(attention, /\/api\/assistant-hub\/status/);
assert.match(attention, /import-candidates\/\$\{encodeURIComponent\(item\.candidate\.candidate_id\)\}\/authorize/);
assert.match(attention, /AUTHORIZE_ASSISTANT_IMPORT_/);

assert.match(command, /metaKey \|\| event\.ctrlKey/);
assert.match(command, /\/api\/capture\/text/);
assert.match(command, /owner_command_bar/);
assert.match(command, /当前全局入口只执行可验证的记录和导航指令/);

assert.match(review, /disabled={!hasMore}/);
assert.match(inspector, /hasMore={hasMore\.source}/);
assert.match(inspector, /disabled={!hasMore}/);
assert.match(capture, /setHasMore/);
assert.match(capture, /disabled={!hasMore}/);

for (const token of [".workbench-shell-v4", ".owner-command-bar", ".v4-brief-hero", ".memory-browser-layout", ".work-history-layout", ".attention-object-card"]) assert.ok(css.includes(token), `V4 visual system is missing ${token}`);
assert.match(workFeed, /safeRelativePath/);
assert.equal(workFeed.includes("payload.text"), false, "Owner work feed must not project captured body text");

console.log("observation-first-ui-smoke: PASS");
