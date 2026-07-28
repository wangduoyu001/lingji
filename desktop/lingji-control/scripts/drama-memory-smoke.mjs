import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFile(resolve(here, path), "utf8");

const [page, navigation, pages, types, api, service, batch, importer, repository] = await Promise.all([
  read("../src/pages/DramaPage.tsx"),
  read("../src/navigation.ts"),
  read("../src/AppPages.tsx"),
  read("../src/types.ts"),
  read("../../../src/control/drama_api.py"),
  read("../../../src/plugins/drama_intelligence/service.py"),
  read("../../../src/plugins/drama_intelligence/batch.py"),
  read("../../../src/plugins/drama_intelligence/importer.py"),
  read("../../../src/plugins/drama_intelligence/repository.py"),
]);

for (const token of [
  "Drama Memory 状态",
  "导入单部剧本",
  "批量导入目录",
  "搜索剧本记忆",
  "source_ref",
  "15 * 60 * 1000",
  "30 * 60 * 1000",
  "扫描版 PDF",
  "编剧 Agent",
  "等待检索验收通过",
]) assert.ok(page.includes(token), `Drama page is missing ${token}`);

assert.match(navigation, /id: "drama"/);
assert.match(pages, /page === "drama"/);
assert.match(types, /\| "drama"/);

for (const route of [
  "/api/drama/status",
  "/api/drama/library",
  "/api/drama/import",
  "/api/drama/import-directory",
  "/api/drama/search",
]) assert.ok(api.includes(route), `Drama API is missing ${route}`);

for (const token of [
  "lingji_drama_",
  "DramaRepository",
  "QdrantSemanticProvider",
  "SemanticPoint",
  "match_reasons",
  "source_map.json",
]) assert.ok(service.includes(token), `Drama service is missing ${token}`);

for (const token of ["failed_count", "duplicate_count", "SUPPORTED_EXTENSIONS", "relative_path"])
  assert.ok(batch.includes(token), `Drama batch import is missing ${token}`);

for (const extension of [".txt", ".md", ".docx", ".pdf", ".srt", ".vtt", ".ass"])
  assert.ok(importer.includes(extension), `Drama importer is missing ${extension}`);

for (const token of ["CREATE TABLE IF NOT EXISTS dramas", "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts", "source_ref", "source_sha256 TEXT NOT NULL UNIQUE"])
  assert.ok(repository.includes(token), `Drama repository is missing ${token}`);

assert.equal(page.includes("自动生成100集"), false, "V1 must not expose uncontrolled full-series generation");
console.log("drama-memory-smoke: PASS");
