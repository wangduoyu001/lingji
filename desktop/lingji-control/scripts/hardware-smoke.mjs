import fs from "node:fs";

const page = fs.readFileSync("src/pages/SystemComputePage.tsx", "utf8");
const navigation = fs.readFileSync("src/navigation.ts", "utf8");
const settings = fs.readFileSync("src/pages/SettingsPage.tsx", "utf8");
const registry = fs.readFileSync("../../src/control/settings_governance.py", "utf8");

for (const token of [
  "/api/hardware/capabilities",
  "/api/hardware/telemetry",
  "/api/hardware/refresh",
  "/api/compute/policy",
  "自动选择",
  "GPU 优先",
  "仅使用 CPU",
  "不代表某个模型一定能运行",
]) {
  if (!page.includes(token)) throw new Error(`Hardware page is missing: ${token}`);
}

for (const token of ["系统与算力", 'id: "system_compute"']) {
  if (!navigation.includes(token)) throw new Error(`Navigation is missing: ${token}`);
}

if (!/snapshot\?*\.groups/.test(settings) || settings.includes("GROUP_LABELS")) {
  throw new Error("Settings page must consume backend-owned groups");
}
if (!registry.includes('"hardware_compute"') || !registry.includes('"系统与算力"')) {
  throw new Error("Backend Settings Registry is missing the hardware_compute group metadata");
}

console.log("Hardware capability UI smoke passed");
