import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [overview, service, api, css, workFeed] = await Promise.all([
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/service.py", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/api.py", import.meta.url), "utf8"),
  readFile(new URL("../src/OwnerWorkFeed.css", import.meta.url), "utf8"),
  readFile(new URL("../src/ownerWorkFeed.ts", import.meta.url), "utf8"),
]);

assert.match(service, /def memory_progress\(/);
assert.match(api, /"\/api\/memory\/progress"/);
assert.match(overview, /系统统计与高级状态/);
assert.match(overview, /索引覆盖/);
assert.match(overview, /retrieval\.precision_message/);
assert.match(overview, /资料工作清单/);
assert.match(workFeed, /expectedDocuments/);
assert.match(workFeed, /detailsState/);
assert.match(workFeed, /灵机不会用一个数字代替资料列表/);
assert.match(service, /"precision_state": "not_measured"/);
assert.match(service, /尚未建立验证样本/);
assert.match(css, /\.owner-work-stat-grid/);
assert.equal(overview.includes("准确率 100%"), false, "Memory progress must never invent retrieval accuracy");
assert.equal(overview.includes("memory-progress-v2-meter"), false, "Aggregate memory meter must no longer dominate the home page");
console.log("memory-progress-smoke: PASS");
