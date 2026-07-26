import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = async (path) => readFile(resolve(here, path), "utf8");

const [app, shell, navigation, page, memoryReview] = await Promise.all([
  source("../src/App.tsx"),
  source("../src/components/DesktopShell.tsx"),
  source("../src/navigation.ts"),
  source("../src/pages/AutoReviewPage.tsx"),
  source("../src/pages/MemoryReviewPage.tsx"),
]);

assert.match(app, /DesktopShell/);
assert.match(shell, /PRIMARY_NAVIGATION/);
assert.match(shell, /connectionState/);
assert.match(navigation, /id: "auto_review"/);
assert.match(navigation, /ADVANCED_NAVIGATION/);
assert.equal((navigation.match(/group: "observe"/g) ?? []).length, 4);

for (const endpoint of [
  "/api/auto-review/status",
  "/api/auto-review/metrics",
  "/api/auto-review/decisions",
  "/api/auto-review/evaluate/",
  "/api/auto-review/feedback",
]) {
  assert.ok(page.includes(endpoint), `Missing Shadow endpoint usage: ${endpoint}`);
}

assert.match(page, /SHADOW/);
assert.match(page, /不会批准、拒绝、合并、删除或写入长期记忆/);
assert.match(page, /mutation_count/);
assert.match(memoryReview, /唯一的记忆变更入口/);

for (const forbidden of [
  "/api/auto-review/approve",
  "/api/auto-review/reject",
  "/api/auto-review/delete",
  "/api/auto-review/execute",
  "/api/auto-review/active",
]) {
  assert.equal(page.includes(forbidden), false, `Forbidden execution endpoint found: ${forbidden}`);
}

console.log("auto-review-shadow-smoke: PASS");
