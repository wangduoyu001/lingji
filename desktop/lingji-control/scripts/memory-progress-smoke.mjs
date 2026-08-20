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
assert.match(memory, /\/api\/memory\/review\/candidates\?limit=1&offset=0/);
assert.match(memory, /hasReviewObject/);
assert.match(memory, /候选来源读取失败时，灵机不会用汇总计数制造一个可能为空的审核入口/);
assert.equal(memory.includes("/api/codex/current"), false, "Memory review actions must not depend on Codex summary state");
assert.equal(memory.includes("pending_review_count"), false, "Memory review actions require concrete candidate objects");

// V5 keeps memory progress and work history as separate facts. Memory/document counts may
// describe the second brain, but they must never be converted into fake WorkItems.
assert.match(workFeed, /expectedDocuments/);
assert.match(workFeed, /detailsState/);
assert.match(workFeed, /真实 WorkItem 列表暂时不可用/);
assert.match(workFeed, /不会用记忆数量或静态事件冒充工作履历/);
assert.match(workFeed, /CaptureJobsResponse/);
assert.equal(workFeed.includes("safeRelativePath"), false, "V5 work identity must not be reconstructed from memory paths");
assert.equal(workFeed.includes("event_type"), false, "Memory/runtime events must not be promoted into WorkItems");
assert.match(service, /"precision_state": "not_measured"/);
assert.match(service, /尚未建立验证样本/);
assert.match(css, /\.memory-brief-strip/);

console.log("memory-progress-smoke: PASS");
