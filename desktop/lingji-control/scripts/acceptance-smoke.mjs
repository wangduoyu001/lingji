import fs from "node:fs";

const app = fs.readFileSync("src/App.tsx", "utf8");
const navigation = fs.readFileSync("src/navigation.ts", "utf8");
const page = fs.readFileSync("src/pages/AcceptancePage.tsx", "utf8");
const main = fs.readFileSync("src/main.tsx", "utf8");

for (const [label, source, required] of [
  ["app", app, ["AcceptancePage", 'page === "acceptance"']],
  ["navigation", navigation, ["环境验收", 'id: "acceptance"']],
  ["page", page, ["/api/acceptance/run", "/api/acceptance/reports", "输入未变化", "只读取"]],
  ["main", main, ["<Root />"]],
]) {
  for (const token of required) {
    if (!source.includes(token)) {
      throw new Error(`${label} is missing acceptance UI token: ${token}`);
    }
  }
}

console.log("Acceptance UI smoke passed");
