import fs from "node:fs";

const root = fs.readFileSync("src/Root.tsx", "utf8");
const page = fs.readFileSync("src/AcceptancePage.tsx", "utf8");
const main = fs.readFileSync("src/main.tsx", "utf8");

for (const [label, source, required] of [
  ["root", root, ["环境验收", "AcceptancePage", "控制中心"]],
  ["page", page, ["/api/acceptance/run", "/api/acceptance/reports", "输入未变化", "只读"]],
  ["main", main, ["<Root />"]],
]) {
  for (const token of required) {
    if (!source.includes(token)) {
      throw new Error(`${label} is missing acceptance UI token: ${token}`);
    }
  }
}

console.log("Acceptance UI smoke passed");
