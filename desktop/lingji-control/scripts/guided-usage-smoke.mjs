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
  "开始投喂内容",
  "提交后查看进度",
  "审核候选记忆",
  "模型不可用",
  "仅在明确提示时执行重建",
]) assert.ok(guide.includes(token), `Page guide is missing ${token}`);

assert.match(shell, /UsageGuideDrawer/);
assert.match(shell, /不知道怎么用/);
assert.match(shell, /打开灵机使用说明/);
assert.match(shell, /怎么使用/);
assert.match(shell, /日常使用/);

for (const token of [
  "灵机到底怎么用",
  "日常使用只走四步",
  "投喂资料",
  "查看处理",
  "审核记忆",
  "处理异常",
  "高级诊断什么时候用",
]) assert.ok(drawer.includes(token), `Usage drawer is missing ${token}`);

assert.match(overview, /日常只需要这四步/);
assert.match(overview, /从这里开始使用灵机/);
assert.match(overview, /打开投喂中心/);
assert.match(overview, /进入记忆审核/);
assert.match(overview, /正常情况下按 1 → 2 → 3 使用/);

for (const cssToken of [
  ".page-guide",
  ".daily-flow-grid",
  ".desktop-usage-guide-button",
  ".desktop-help-button",
  ".usage-guide-backdrop",
  ".usage-guide-drawer",
]) assert.ok(css.includes(cssToken), `Guided usage styles are missing ${cssToken}`);

console.log("guided-usage-smoke: PASS");
