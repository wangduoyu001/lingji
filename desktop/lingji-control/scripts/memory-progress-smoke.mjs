import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [overview, memory, service, api, css, workFeed] = await Promise.all([
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/MemoryHomePage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/service.py", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/api.py", import.meta.url), "utf8"),
  readFile(new URL("../src/WorkbenchV4.css", import.meta.url), "utf8"),
  readFile(new URL("../src/ownerWorkFeed.ts", import.meta.url), "utf8"),
]);

assert.match(service, /def memory_progress\(/);
assert.match(api, /"\/api\/memory\/progress"/);
assert.match(overview, /高级状态与系统统计/);
assert.match(overview, /记忆发生了什么变化/);
assert.equal(overview.includes("准确率 100%"), false, "Home must never invent retrieval accuracy");
assert.equal(overview.includes("memory-progress-v2-meter"), false, "Aggregate memory meter must not dominate the home page");

assert.match(memory, /第二永久记忆大脑/);
assert.match(memory, /永久记忆/);
assert.match(memory, /可取回片段/);
assert.match(memory, /当前取回能力/);
assert.match(memory, /语义检索状态未完全就绪；全文检索仍可作为基础取回能力/);
assert.match(memory, /为什么能相信它/);
assert.match(memory, /来源证据/);
assert.match(memory, /记忆缺口/);
assert.match(memory, /pagination\?\.has_more/);

assert.match(workFeed, /expectedDocuments/);
assert.match(workFeed, /detailsState/);
assert.match(workFeed, /灵机不会用一个数字代替资料列表/);
assert.match(service, /"precision_state": "not_measured"/);
assert.match(service, /尚未建立验证样本/);
assert.match(css, /\.memory-brief-strip/);

console.log("memory-progress-smoke: PASS");
