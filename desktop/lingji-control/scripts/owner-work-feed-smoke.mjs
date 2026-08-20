import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildOwnerWorkFeed } from "../src/ownerWorkFeed.ts";

const here = dirname(fileURLToPath(import.meta.url));
const jobsPage = await readFile(resolve(here, "../src/pages/JobsPage.tsx"), "utf8");
assert.match(jobsPage, /\/api\/capture\/jobs\?limit=200&offset=0/);
assert.equal(jobsPage.includes("/api/jobs"), false, "advanced jobs UI must not read raw queue rows");
assert.equal(jobsPage.includes("last_error"), false, "advanced jobs UI must not render raw errors");
assert.match(jobsPage, /outcome_summary/);
assert.match(jobsPage, /error_message/);

const completedJob = {
  job_id: "LJ-JOB-1",
  work_item_id: "LJ-JOB-1",
  capture_id: "LJ-CAP-1",
  title: "ChatGPT 导入 2026-08",
  source_type: "chatgpt_export",
  status: "completed",
  outcome_state: "succeeded",
  outcome_summary: "新增 1 条，索引同步完成。",
  next_actor: "none",
  next_action: "工作已完成；可从结果对象或记忆页面继续查看。",
  result_refs: { memory_id: "MEM-1" },
  result_object_ids: ["DOC-1"],
  completed_at: "2026-08-16T00:30:00+08:00",
  payload: { text: "TOP_SECRET_BODY", input_path: "/Users/private/secret.json" },
};

const runningJob = {
  job_id: "LJ-JOB-2",
  work_item_id: "LJ-JOB-2",
  capture_id: "LJ-CAP-2",
  title: "产品视频素材",
  source_type: "media",
  status: "running",
  outcome_state: "running",
  outcome_summary: "正在执行解析和整理。",
  next_actor: "system",
  next_action: "继续当前执行直到产生真实结果。",
  updated_at: "2026-08-16T00:31:00+08:00",
};

const feed = buildOwnerWorkFeed({
  jobsResponse: {
    items: [runningJob, completedJob],
    pagination: { limit: 24, offset: 0, total: 2, has_more: false },
  },
  expectedDocuments: 2,
});

assert.equal(feed.detailsState, "ready");
assert.equal(feed.summary.expectedDocuments, 2);
assert.equal(feed.summary.needsOwner, 0, "work history must not manufacture owner PendingActions");
assert.equal(feed.summary.active, 1);

const completed = feed.items.find((item) => item.workItemId === "LJ-JOB-1");
assert.ok(completed, "completed WorkItem must remain visible");
assert.equal(completed.captureId, "LJ-CAP-1");
assert.equal(completed.memoryId, "MEM-1");
assert.deepEqual(completed.resultObjectIds, ["DOC-1"]);
assert.equal(completed.source, "ChatGPT 历史");
assert.equal(completed.stage, "memory");
assert.match(completed.done, /索引同步完成/);
assert.equal(completed.nextActor, "none");

const running = feed.items.find((item) => item.workItemId === "LJ-JOB-2");
assert.ok(running, "active WorkItem must be visible before any memory exists");
assert.equal(running.captureId, "LJ-CAP-2");
assert.equal(running.stage, "parse");
assert.equal(running.nextActor, "system");
assert.match(running.nextStep, /继续当前执行/);

const serialized = JSON.stringify(feed);
for (const forbidden of ["TOP_SECRET_BODY", "/Users/private", "secret.json", "payload"]) {
  assert.equal(serialized.includes(forbidden), false, `owner work projection leaked non-owner field: ${forbidden}`);
}
assert.equal(feed.recentActivity.length, 1, "only terminal WorkItems become recent outcomes");
assert.equal(feed.recentActivity[0].workItemId, "LJ-JOB-1");

const unavailable = buildOwnerWorkFeed({ jobsResponse: null, expectedDocuments: 2 });
assert.equal(unavailable.detailsState, "unavailable");
assert.match(unavailable.detailsMessage, /WorkItem/);
assert.match(unavailable.detailsMessage, /不会用记忆数量/);

const genericSource = buildOwnerWorkFeed({
  jobsResponse: {
    items: [{
      job_id: "LJ-JOB-GENERIC",
      work_item_id: "LJ-JOB-GENERIC",
      status: "running",
      outcome_summary: "正在处理。",
      next_actor: "system",
      next_action: "继续处理。",
      updated_at: "2026-08-16T00:32:00+08:00",
    }],
    pagination: { limit: 24, offset: 0, total: 1, has_more: false },
  },
  expectedDocuments: 0,
});
assert.equal(genericSource.items[0]?.source, "资料", "missing source type must never render blank");

const empty = buildOwnerWorkFeed({
  jobsResponse: { items: [], pagination: { limit: 24, offset: 0, total: 0, has_more: false } },
  expectedDocuments: 7,
});
assert.equal(empty.detailsState, "ready");
assert.equal(empty.items.length, 0, "existing memory count must not be converted into fake work history");

console.log("owner-work-feed-smoke: PASS");
