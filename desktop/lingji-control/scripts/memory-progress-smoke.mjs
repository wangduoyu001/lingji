import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [overview, service, api, css] = await Promise.all([
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/service.py", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/api.py", import.meta.url), "utf8"),
  readFile(new URL("../src/OwnerHomeV2.css", import.meta.url), "utf8"),
]);

assert.match(service, /def memory_progress\(/);
assert.match(api, /"\/api\/memory\/progress"/);
assert.match(overview, /memory-progress-v2/);
assert.match(overview, /记忆进度/);
assert.match(overview, /索引覆盖/);
assert.match(overview, /更新中/);
assert.match(overview, /已完成/);
assert.match(overview, /retrieval\.precision_message/);
assert.match(service, /"precision_state": "not_measured"/);
assert.match(service, /尚未建立验证样本/);
assert.match(css, /\.memory-progress-v2-meter/);
assert.equal(overview.includes("准确率 100%"), false, "Memory progress must never invent retrieval accuracy");
console.log("memory-progress-smoke: PASS");
