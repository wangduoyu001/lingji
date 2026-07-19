import fs from "node:fs";

const requiredFiles = [
  "src/navigation.ts",
  "src/types.ts",
  "src/hooks/useLingJiConnection.ts",
  "src/components/ui.tsx",
  "src/components/settings/SettingField.tsx",
  "src/pages/OverviewPage.tsx",
  "src/pages/SystemComputePage.tsx",
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
const systemCompute = fs.readFileSync("src/pages/SystemComputePage.tsx", "utf8");
const settings = fs.readFileSync("src/pages/SettingsPage.tsx", "utf8");
const field = fs.readFileSync("src/components/settings/SettingField.tsx", "utf8");
const navigation = fs.readFileSync("src/navigation.ts", "utf8");

for (const token of ["NAVIGATION", "useLingJiConnection", "OverviewPage", "SystemComputePage", "SettingsPage", "AcceptancePage"]) {
  if (!app.includes(token)) throw new Error(`App shell is missing ${token}`);
}

for (const token of ["/api/hardware/capabilities", "/api/hardware/telemetry", "/api/compute/policy", "候选设备", "模型一定能运行"]) {
  if (!systemCompute.includes(token)) throw new Error(`System compute page is missing ${token}`);
}

for (const token of ["只显示已修改", "恢复本组默认", "取消未保存修改", "搜索设置", "系统与算力"]) {
  if (!settings.includes(token)) throw new Error(`Settings page is missing ${token}`);
}

for (const token of ["使用系统默认", "主人已修改", "为什么推荐", "什么时候修改", "恢复默认"]) {
  if (!field.includes(token)) throw new Error(`Setting field is missing ${token}`);
}

for (const token of ["系统与算力", "环境验收", "设置", "主动投喂", "媒体分析"]) {
  if (!navigation.includes(token)) throw new Error(`Navigation is missing ${token}`);
}

const appLines = app.split("\n").length;
if (appLines > 100) throw new Error(`App.tsx is still too large: ${appLines} lines`);

console.log(`Modular UI smoke passed; App.tsx=${appLines} lines`);
