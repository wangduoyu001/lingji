import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [app, appPages, shell, guide, drawer, overview, startCenter, guidedCss, startCenterCss] = await Promise.all([
  read("../src/App.tsx"),
  read("../src/AppPages.tsx"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/components/PageGuide.tsx"),
  read("../src/components/UsageGuideDrawer.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/components/StartCenterPanel.tsx"),
  read("../src/GuidedUsage.css"),
  read("../src/components/StartCenterPanel.css"),
]);

assert.match(app, /GuidedUsage\.css/);
assert.match(app, /StartCenterPanel\.css/);
assert.match(appPages, /<PageGuide page=\{page\} onNavigate=\{onNavigate\}/);

for (const token of [
  "这页怎么用",
  "什么时候来",
  "连接 AI 与导入记忆",
  "扫描 Codex、Claude Code、WorkBuddy",
  "提交后查看进度",
  "审核候选记忆",
  "模型不可用",
  "仅在明确提示时执行重建",
]) assert.ok(guide.includes(token), `Page guide is missing ${token}`);

assert.match(shell, /UsageGuideDrawer/);
assert.match(shell, /不知道怎么用/);
assert.match(shell, /打开灵机使用说明/);
assert.match(shell, /怎么使用/);

for (const token of [
  "第一次打开灵机怎么做",
  "扫描 AI 软件",
  "导入已有资料",
  "查看处理",
  "审核永久记忆",
  "不会直接成为 Core Memory",
  "高级诊断",
]) assert.ok(drawer.includes(token), `Usage drawer is missing ${token}`);

assert.match(overview, /StartCenterPanel/);
assert.match(overview, /灵机开始中心/);
assert.match(overview, /新用户按顺序完成/);
assert.match(overview, /开始连接 AI/);
assert.match(overview, /部分能力待处理/);
assert.match(overview, /暂未激活，进入向量中心查看原因/);

for (const endpoint of [
  "/api/memory/inspector/status",
  "/api/assistant-hub/status",
  "/api/assistant-hub/connections",
  "/api/codex/current",
  "/api/obsidian/status",
]) assert.ok(startCenter.includes(endpoint), `Start center is missing ${endpoint}`);

for (const token of [
  "唯一推荐下一步",
  "当前工作空间",
  "正式空间",
  "验收空间",
  "全量记忆总览",
  "正式 Vault",
  "来源",
  "对话",
  "消息",
  "永久知识",
  "核心记忆",
  "最近导入",
  "系统与已知问题",
  "已修复并验收",
  "Embedding 与语义检索",
  "不会把未知状态显示成一切正常",
]) assert.ok(startCenter.includes(token), `Start center is missing ${token}`);

for (const cssToken of [
  ".page-guide",
  ".daily-flow-grid",
  ".desktop-usage-guide-button",
  ".desktop-help-button",
  ".usage-guide-backdrop",
  ".usage-guide-drawer",
]) assert.ok(guidedCss.includes(cssToken), `Guided usage styles are missing ${cssToken}`);

for (const cssToken of [
  ".start-center-recommendation",
  ".start-center-memory-grid",
  ".start-center-connection-grid",
  ".start-center-recent-list",
  ".start-center-issue-grid",
]) assert.ok(startCenterCss.includes(cssToken), `Start center styles are missing ${cssToken}`);

console.log("guided-usage-smoke: PASS");
