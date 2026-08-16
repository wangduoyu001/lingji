import fs from "node:fs";

const requiredFiles = [
  "src/AppPages.tsx",
  "src/navigation.ts",
  "src/types.ts",
  "src/WorkbenchV4.css",
  "src/hooks/useLingJiConnection.ts",
  "src/components/ui.tsx",
  "src/components/DesktopShell.tsx",
  "src/components/GlobalOwnerCommand.tsx",
  "src/components/RuntimeBoundary.tsx",
  "src/components/NavIcon.tsx",
  "src/components/settings/SettingField.tsx",
  "src/pages/OverviewPage.tsx",
  "src/pages/MemoryHomePage.tsx",
  "src/pages/ActivityPage.tsx",
  "src/pages/AttentionPage.tsx",
  "src/pages/DiagnosticsPage.tsx",
  "src/pages/BrainStatusPage.tsx",
  "src/pages/VectorCenterPage.tsx",
  "src/pages/SystemComputePage.tsx",
  "src/pages/ModelsPage.tsx",
  "src/pages/JobsPage.tsx",
  "src/pages/CapturePage.tsx",
  "src/pages/MediaPage.tsx",
  "src/pages/StoragePage.tsx",
  "src/pages/BackupsPage.tsx",
  "src/pages/AcceptancePage.tsx",
  "src/pages/SettingsPage.tsx",
  "src/pages/LogsPage.tsx",
];

for (const file of requiredFiles) {
  if (!fs.existsSync(file)) throw new Error(`Missing modular UI file: ${file}`);
}

const app = fs.readFileSync("src/App.tsx", "utf8");
const shell = fs.readFileSync("src/components/DesktopShell.tsx", "utf8");
const routes = fs.readFileSync("src/AppPages.tsx", "utf8");
const systemCompute = fs.readFileSync("src/pages/SystemComputePage.tsx", "utf8");
const vectorCenter = fs.readFileSync("src/pages/VectorCenterPage.tsx", "utf8");
const settings = fs.readFileSync("src/pages/SettingsPage.tsx", "utf8");
const field = fs.readFileSync("src/components/settings/SettingField.tsx", "utf8");
const navigation = fs.readFileSync("src/navigation.ts", "utf8");

for (const token of ["NAVIGATION", "useLingJiConnection", "AppPages", "DesktopShell", "RuntimeBoundary", "WorkbenchV4.css"]) {
  if (!app.includes(token)) throw new Error(`App shell is missing ${token}`);
}
for (const token of ["desktop-sidebar", "desktop-toolbar", "NavIcon", "PRIMARY_NAVIGATION", "GlobalOwnerCommand", "第二永久记忆大脑"]) {
  if (!shell.includes(token)) throw new Error(`Desktop shell is missing ${token}`);
}
for (const token of [
  "OverviewPage",
  "MemoryHomePage",
  "ActivityPage",
  "AttentionPage",
  "DiagnosticsPage",
  "BrainStatusPage",
  "VectorCenterPage",
  "SystemComputePage",
  "ModelsPage",
  "SettingsPage",
  "AcceptancePage",
]) {
  if (!routes.includes(token)) throw new Error(`Page router is missing ${token}`);
}

for (const token of ["/api/hardware/capabilities", "/api/hardware/telemetry", "/api/compute/policy", "候选设备", "模型一定能运行"]) {
  if (!systemCompute.includes(token)) throw new Error(`System compute page is missing ${token}`);
}
for (const token of ["/api/memory/status", "/api/vector/status", "/api/vector/coverage", "向量覆盖率"]) {
  if (!vectorCenter.includes(token)) throw new Error(`Vector Center page is missing ${token}`);
}
for (const token of ["只显示已修改", "恢复本组默认", "取消未保存修改", "搜索设置"]) {
  if (!settings.includes(token)) throw new Error(`Settings page is missing ${token}`);
}
if (!/snapshot\?*\.groups/.test(settings)) throw new Error("Settings page must consume backend groups");
if (settings.includes("GROUP_LABELS")) throw new Error("Settings page must not duplicate backend group labels");
for (const token of ["使用系统默认", "主人已修改", "为什么推荐", "什么时候修改", "恢复默认"]) {
  if (!field.includes(token)) throw new Error(`Setting field is missing ${token}`);
}

const primaryBlock = navigation.match(/PRIMARY_NAVIGATION:[\s\S]*?\];/)?.[0] ?? "";
if ((primaryBlock.match(/id:/g) ?? []).length !== 5) throw new Error("V4 primary navigation must contain exactly five entries");
for (const token of ["首页", "记忆", "工作", "需要我", "高级"]) {
  if (!primaryBlock.includes(token)) throw new Error(`V4 primary navigation is missing ${token}`);
}
for (const token of ["脑状态", "Codex 工作记录", "向量中心", "系统与算力", "AI 与模型", "环境验收", "设置", "添加资料", "媒体分析", "icon:"]) {
  if (!navigation.includes(token)) throw new Error(`Navigation is missing ${token}`);
}

const appLines = app.split(/\r?\n/).length;
if (appLines > 105) throw new Error(`App.tsx is still too large: ${appLines} lines`);

console.log(`Modular UI smoke passed; App.tsx=${appLines} lines`);
