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
  "这页怎么看",
  "什么时候来",
  "查看自动处理进度",
  "灵机会自动扫描安全元数据",
  "只有读取正文或修改外部配置时才确认授权",
  "仅在明确提示时批准重建",
]) assert.ok(guide.includes(token), `Page guide is missing ${token}`);
assert.equal(guide.includes("先点击扫描我的 AI 软件"), false, "Page guide must not make scanning a required owner step");

assert.match(shell, /UsageGuideDrawer/);
assert.match(shell, /不知道怎么用/);
assert.match(shell, /打开灵机使用说明/);
assert.match(shell, /怎么使用/);

for (const token of [
  "灵机会主动工作，你主要负责观察和授权",
  "自动运行与主人边界",
  "灵机自动发现",
  "灵机自动处理",
  "需要时请求授权",
  "主人最终定稿",
  "不会直接成为 Core Memory",
  "高级诊断与手动干预",
]) assert.ok(drawer.includes(token), `Usage drawer is missing ${token}`);
assert.equal(drawer.includes("首次设置流程"), false, "Usage drawer must not present a mandatory manual setup sequence");
assert.equal(drawer.includes("先连接 AI 和导入资料"), false, "Usage drawer must not make the owner drive routine setup");

assert.match(overview, /StartCenterPanel/);
for (const token of [
  "灵机运行观察台",
  "灵机会主动启动、发现、处理、重试和恢复",
  "当前空闲，不需要操作",
  "灵机如何主动工作",
  "自动干活，必要时才打扰主人",
  "下面是运行机制，不是要求你逐项点击的操作流程",
  "查看灵机正在做什么",
  "后台正在诊断模型、Provider 与索引状态",
]) assert.ok(overview.includes(token), `Overview autonomy contract is missing ${token}`);
assert.match(overview, /部分能力待处理/);
assert.equal(overview.includes("新用户按顺序完成"), false, "Overview must not present a manual onboarding sequence");
assert.equal(overview.includes("开始连接 AI"), false, "Overview must not require the owner to start routine AI discovery");
assert.equal(overview.includes("等待你的下一步"), false, "Idle system must not imply the owner is blocking progress");

for (const endpoint of [
  "/api/memory/inspector/status",
  "/api/assistant-hub/status",
  "/api/assistant-hub/connections",
  "/api/codex/current",
  "/api/obsidian/status",
]) assert.ok(startCenter.includes(endpoint), `Start center is missing ${endpoint}`);

for (const token of [
  "灵机当前处理重点",
  "当前工作空间",
  "正式空间",
  "验收空间",
  "正式 Vault",
  "来源",
  "对话",
  "消息",
  "永久知识",
  "核心记忆",
  "灵机自动发现",
  "等待授权来源",
  "自动处理记录",
  "系统与已知问题",
  "自动维护",
  "Embedding 与语义检索",
  "不会把未知状态显示成一切正常",
]) assert.ok(startCenter.includes(token), `Start center is missing ${token}`);
assert.equal(startCenter.includes("唯一推荐下一步"), false, "Start center must not make the owner the workflow engine");
assert.equal(
  startCenter.includes("配置存在但尚未激活；全文检索仍可用，后续从向量中心处理"),
  false,
  "Ambiguous vector guidance must not return",
);

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
