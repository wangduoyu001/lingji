import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = (path) => readFile(resolve(here, path), "utf8");

const [review, workspace, autoReview, inspector, loopStyles, inspectorStyles] = await Promise.all([
  source("../src/pages/MemoryReviewPage.tsx"),
  source("../src/pages/CodexWorkspacePage.tsx"),
  source("../src/pages/AutoReviewPage.tsx"),
  source("../src/pages/MemoryInspectorPage.tsx"),
  source("../src/pages/LocalMemoryLoop.css"),
  source("../src/pages/MemoryInspectorPage.css"),
]);

for (const token of [
  "memory-review-hero",
  "review-workbench",
  "review-candidate-card",
  "review-detail-panel",
  "review-action-dock",
  "确认加入长期记忆",
  "拒绝理由（必填）",
]) assert.ok(review.includes(token), `Memory Review is missing ${token}`);

for (const token of [
  "codex-workspace-hero",
  "workspace-browser-grid",
  "project-rail-card",
  "session-card",
  "工作记录详情",
  "activity-timeline",
  "Context Pack",
  "查看这条记录如何进入记忆",
]) assert.ok(workspace.includes(token), `Codex Workspace is missing ${token}`);

for (const token of [
  "auto-review-hero",
  "auto-review-workbench",
  "auto-review-decision-card",
  "决策解释",
  "只读评估",
  "SHADOW",
  "mutation_count",
]) assert.ok(autoReview.includes(token), `Auto Review is missing ${token}`);

assert.match(inspector, /inspector-columns/);
assert.match(inspector, /relation-panel/);
assert.match(inspector, /restricted 受限内容/);

for (const token of [
  ".workspace-hero",
  ".review-workbench",
  ".workspace-browser-grid",
  ".auto-review-workbench",
  ".workspace-empty-detail",
]) assert.ok(loopStyles.includes(token), `Memory workspace styles are missing ${token}`);

for (const token of [
  ".inspector-status",
  ".inspector-filters",
  ".inspector-columns",
  ".relation-panel",
  ".memory-detail",
]) assert.ok(inspectorStyles.includes(token), `Inspector styles are missing ${token}`);

assert.equal(review.includes("永久删除"), false);
assert.equal(autoReview.includes("/api/auto-review/approve"), false);
assert.equal(autoReview.includes("/api/auto-review/reject"), false);
assert.equal(autoReview.includes("/api/auto-review/active"), false);

console.log("memory-workspace-ui-smoke: PASS");
