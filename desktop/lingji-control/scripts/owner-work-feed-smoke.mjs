import assert from "node:assert/strict";
import { buildOwnerWorkFeed } from "../src/ownerWorkFeed.ts";

const completedJob = {
  job_id: "LJ-JOB-1",
  source_type: "chatgpt_export",
  status: "completed",
  input_path: "/Users/private/secret/conversations.json",
  payload: { title: "ChatGPT 导入 2026-08", text: "TOP_SECRET_BODY" },
  completed_at: "2026-08-16T00:30:00+08:00",
  result: {
    indexed: true,
    created: [{ relative_path: "02-Sources/chatgpt/对话整理.md", raw_path: "/Users/private/raw/secret.json" }],
    updated: [],
    skipped: [],
    paths: ["/Users/private/vault/02-Sources/chatgpt/对话整理.md"],
  },
};

const runningJob = {
  job_id: "LJ-JOB-2",
  source_type: "media",
  status: "running",
  input_path: "/Users/private/Desktop/产品视频.mp4",
  payload: { title: "产品视频素材" },
  updated_at: "2026-08-16T00:31:00+08:00",
};

const memoryResponse = {
  items: [
    {
      memory_id: "MEM-1",
      title: "ChatGPT 对话整理",
      relative_path: "02-Sources/chatgpt/对话整理.md",
      memory_type: "source",
      status: "active",
      review_status: "",
      updated_at: "2026-08-16T00:30:00+08:00",
    },
    {
      memory_id: "MEM-2",
      title: "待确认的项目决策",
      relative_path: "05-Operations/Decisions/Candidates/decision-1.md",
      memory_type: "decision_candidate",
      status: "active",
      review_status: "pending_review",
      updated_at: "2026-08-16T00:29:00+08:00",
    },
  ],
};

const feed = buildOwnerWorkFeed({
  memoryResponse,
  queueResponse: { recent: [runningJob, completedJob] },
  events: [
    { event_id: 1, event_type: "capture_submitted", created_at: "2026-08-16T00:31:00+08:00", payload: { source_type: "media", text: "DO_NOT_EXPORT" } },
    { event_id: 2, event_type: "unknown_internal_event", payload: { secret: "DO_NOT_EXPORT" } },
  ],
  expectedDocuments: 2,
});

assert.equal(feed.detailsState, "ready");
assert.equal(feed.summary.expectedDocuments, 2);
assert.equal(feed.summary.needsOwner, 1);

const completed = feed.items.find((item) => item.memoryId === "MEM-1");
assert.ok(completed, "completed memory must be visible as a concrete object");
assert.equal(completed.title, "ChatGPT 对话整理");
assert.equal(completed.source, "ChatGPT 历史");
assert.equal(completed.stage, "retrieve");
assert.match(completed.done, /收纳、解析并更新索引/);
assert.match(completed.nextStep, /不用操作/);

const review = feed.items.find((item) => item.memoryId === "MEM-2");
assert.ok(review, "review candidate must be visible");
assert.equal(review.ownerActionRequired, true);
assert.equal(review.stage, "confirm");
assert.match(review.nextStep, /需要你确认/);

const running = feed.items.find((item) => item.id === "LJ-JOB-2");
assert.ok(running, "active queue item must remain visible before a memory row exists");
assert.equal(running.title, "产品视频素材");
assert.equal(running.stage, "parse");
assert.match(running.nextStep, /不用操作/);

const serialized = JSON.stringify(feed);
for (const forbidden of ["TOP_SECRET_BODY", "DO_NOT_EXPORT", "/Users/private", "secret.json"]) {
  assert.equal(serialized.includes(forbidden), false, `owner feed leaked private field: ${forbidden}`);
}
assert.equal(feed.recentActivity.length, 1, "unknown internal events must not become owner-facing activity");
assert.match(feed.recentActivity[0].title, /媒体资料/);

const unavailable = buildOwnerWorkFeed({
  memoryResponse: { items: [] },
  queueResponse: { recent: [] },
  events: [],
  expectedDocuments: 2,
});
assert.equal(unavailable.detailsState, "unavailable");
assert.match(unavailable.detailsMessage, /2 份资料/);
assert.match(unavailable.detailsMessage, /不会用一个数字代替资料列表/);

const genericSource = buildOwnerWorkFeed({
  memoryResponse: { items: [] },
  queueResponse: {
    recent: [{
      job_id: "LJ-JOB-GENERIC",
      status: "running",
      payload: { title: "普通资料" },
      updated_at: "2026-08-16T00:32:00+08:00",
    }],
  },
  events: [],
  expectedDocuments: 0,
});
assert.equal(genericSource.items[0]?.source, "知识库资料", "missing source type must never render as a blank label");

const empty = buildOwnerWorkFeed({
  memoryResponse: { items: [] },
  queueResponse: { recent: [] },
  events: [],
  expectedDocuments: 0,
});
assert.equal(empty.detailsState, "ready");
assert.equal(empty.items.length, 0);

console.log("owner-work-feed-smoke: PASS");
