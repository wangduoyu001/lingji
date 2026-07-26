import fs from "node:fs";

const page = fs.readFileSync("src/pages/ModelsPage.tsx", "utf8");
const navigation = fs.readFileSync("src/navigation.ts", "utf8");
const routes = fs.readFileSync("src/AppPages.tsx", "utf8");

for (const token of [
  "/api/models/registry",
  "/api/models",
  "/api/models/refresh",
  "已安装模型",
  "正在运行",
  "未完成兼容测试",
  "下载、删除、测速",
  "只读清单",
]) {
  if (!page.includes(token)) throw new Error(`Models page is missing: ${token}`);
}

for (const token of ["AI 与模型", 'id: "models"']) {
  if (!navigation.includes(token)) throw new Error(`Navigation is missing: ${token}`);
}

for (const token of ["ModelsPage", 'page === "models"']) {
  if (!routes.includes(token)) throw new Error(`Page router is missing: ${token}`);
}

console.log("AI and models inventory UI smoke passed");
