import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [app, appPages, shell, guide, drawer, overview, css] = await Promise.all([
  read("../src/App.tsx"),
  read("../src/AppPages.tsx"),
  read("../src/components/DesktopShell.tsx"),
  read("../src/components/PageGuide.tsx"),
  read("../src/components/UsageGuideDrawer.tsx"),
  read("../src/pages/OverviewPage.tsx"),
  read("../src/GuidedUsage.css"),
]);

assert.match(app, /GuidedUsage\.css/);
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

assert.match(overview, /新用户按顺序完成/);
assert.match(overview, /先把你的 AI 和已有记忆接进来/);
assert.match(overview, /打开 AI 助手中心/);
assert.match(overview, /进入记忆审核/);
assert.match(overview, /开始连接 AI/);
assert.match(overview, /第一次按 1 → 2 → 3 完成设置/);

for (const cssToken of [
  ".page-guide",
  ".daily-flow-grid",
  ".desktop-usage-guide-button",
  ".desktop-help-button",
  ".usage-guide-backdrop",
  ".usage-guide-drawer",
]) assert.ok(css.includes(cssToken), `Guided usage styles are missing ${cssToken}`);

console.log("guided-usage-smoke: PASS");
