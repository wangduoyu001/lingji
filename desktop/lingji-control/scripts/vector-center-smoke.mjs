import fs from "node:fs";

const pagePath = "src/pages/VectorCenterPage.tsx";
if (!fs.existsSync(pagePath)) throw new Error("VectorCenterPage.tsx is missing");

const page = fs.readFileSync(pagePath, "utf8");
const navigation = fs.readFileSync("src/navigation.ts", "utf8");
const types = fs.readFileSync("src/types.ts", "utf8");
const app = fs.readFileSync("src/App.tsx", "utf8");

for (const token of ["vector_center", "向量中心", "Embedding、Qdrant 与索引覆盖率"]) {
  if (!navigation.includes(token)) throw new Error(`Navigation is missing ${token}`);
}
if (!types.includes('"vector_center"')) throw new Error("PageId is missing vector_center");
for (const token of ["VectorCenterPage", 'page === "vector_center"']) {
  if (!app.includes(token)) throw new Error(`App shell is missing ${token}`);
}
for (const endpoint of ["/api/memory/status", "/api/vector/status", "/api/vector/coverage"]) {
  if (!page.includes(endpoint)) throw new Error(`Vector Center is missing ${endpoint}`);
}
for (const token of ["coverage", "CoverageBar", "missing_chunk_ids", "rebuild_required", "需要安全重建新的 Collection"]) {
  if (!page.includes(token)) throw new Error(`Vector Center is missing ${token}`);
}
if (!page.includes("Promise.allSettled")) throw new Error("Vector Center must load endpoints independently");
if (/api\.(post|patch)\s*\(/.test(page)) throw new Error("Vector Center contains a write API call");
if (/https?:\/\//.test(page) || /127\.0\.0\.1|localhost/.test(page)) throw new Error("Vector Center contains a direct service URL");
if (/8765|8767/.test(page)) throw new Error("Vector Center references a forbidden port");

const appLines = app.split(/\r?\n/).length;
if (appLines > 100) throw new Error(`App.tsx is too large: ${appLines} lines`);

console.log(`Vector Center smoke passed; App.tsx=${appLines} lines`);
