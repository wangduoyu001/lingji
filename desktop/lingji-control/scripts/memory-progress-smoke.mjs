import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [overview, service, api] = await Promise.all([
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/service.py", import.meta.url), "utf8"),
  readFile(new URL("../../../src/control/api.py", import.meta.url), "utf8"),
]);

assert.match(service, /def memory_progress\(/);
assert.match(api, /"\/api\/memory\/progress"/);
assert.match(overview, /记忆进度看板/);
assert.match(overview, /正在收纳/);
assert.match(overview, /自动更新/);
assert.match(overview, /可验证取回/);
assert.match(service, /"precision_state": "not_measured"/);
assert.match(service, /尚未建立验证样本/);
console.log("memory-progress-smoke: PASS");
