import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { buildOwnerWorkFeed } from "../src/ownerWorkFeed.ts";
import {
  buildOwnerAttentionItems,
  ownerAttentionSummary,
} from "../src/ownerWorkbenchModel.ts";

const [overview, activity, attentionPage, memoryPage, commandBar] = await Promise.all([
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/ActivityPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/AttentionPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/MemoryHomePage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/components/GlobalOwnerCommand.tsx", import.meta.url), "utf8"),
]);

const workFeed = buildOwnerWorkFeed({
  jobsResponse: {
    items: [
      {
        job_id: "LJ-JOB-RUNNING",
        work_item_id: "LJ-JOB-RUNNING",
        capture_id: "LJ-CAP-RUNNING",
        title: "正在整理的新资料",
        source_type: "text",
        status: "running",
        outcome_summary: "正在执行解析和整理。",
        next_actor: "system",
        next_action: "继续当前执行直到产生真实结果。",
        updated_at: "2026-08-20T12:00:00Z",
      },
      {
        job_id: "LJ-JOB-DONE",
        work_item_id: "LJ-JOB-DONE",
        capture_id: "LJ-CAP-DONE",
        title: "已完成的资料",
        source_type: "chatgpt_export",
        status: "completed",
        outcome_summary: "新增 1 条，索引同步完成。",
        next_actor: "none",
        next_action: "工作已完成；可从结果对象或记忆页面继续查看。",
        result_refs: { memory_id: "MEM-DONE" },
        result_object_ids: ["DOC-DONE"],
        completed_at: "2026-08-20T11:59:00Z",
      },
    ],
    pagination: { limit: 24, offset: 0, total: 2, has_more: false },
  },
  expectedDocuments: 9,
  limit: 24,
});

assert.equal(workFeed.summary.active, 1, "10-second Home must expose a real running WorkItem");
assert.equal(workFeed.recentActivity.length, 1, "10-second Home must expose a real terminal outcome");
assert.equal(workFeed.items.find((item) => item.workItemId === "LJ-JOB-DONE")?.memoryId, "MEM-DONE");
assert.equal(workFeed.summary.needsOwner, 0, "WorkItem projection must not manufacture owner actions");

const ownerActions = buildOwnerAttentionItems({
  reviewItems: [{ memory_id: "MEM-PENDING", title: "待确认记忆", proposal_reason: "需要主人决定是否保留" }],
  importSources: [],
  vectorRebuildRequired: false,
});
const ownerSummary = ownerAttentionSummary({ items: ownerActions, sourceUnknown: false, activeWorkCount: workFeed.summary.active });
assert.equal(ownerActions.length, 1, "10-second inbox count must come from a concrete object");
assert.equal(ownerSummary.state, "owner");
assert.match(ownerSummary.title, /1 件事真的需要你/);

assert.match(overview, /\/api\/capture\/jobs\?limit=24&offset=0/);
assert.match(overview, /buildOwnerWorkFeed/);
assert.match(overview, /buildOwnerAttentionItems/);
assert.match(overview, /有 WorkItem 才显示结果/);
assert.match(overview, /下一执行者/);
assert.equal(overview.includes("/api/jobs"), false, "Home must not read raw queue history");
assert.equal(overview.includes("generic event"), false, "Home must not project owner work from generic events");

assert.match(activity, /\/api\/capture\/jobs\?limit=80&offset=0/);
assert.match(activity, /buildOwnerWorkFeed/);
assert.match(activity, /每一项都必须有真实 WorkItem/);
assert.match(activity, /下一执行者/);
assert.equal(activity.includes("/api/jobs"), false, "Work page must use the same owner-safe WorkItem endpoint");

assert.match(attentionPage, /buildOwnerAttentionItems/);
assert.match(attentionPage, /每个按钮背后都有一个真实对象/);
assert.equal(attentionPage.includes("pending_review_count"), false, "Attention count must not come from a summary number");

assert.match(memoryPage, /\/api\/memory\/inspector\/memories\/\$\{id\}\/source/);
assert.match(memoryPage, /\/api\/memory\/inspector\/memories\/\$\{id\}\/vector/);
assert.match(memoryPage, /记住了什么/);
assert.match(memoryPage, /为什么能相信它/);
assert.match(memoryPage, /来源证据/);

assert.match(commandBar, /source_type: "text"/);
assert.match(commandBar, /不会把它显示成“已经记住”/);
assert.match(commandBar, /capture_id|captureId/);
assert.match(commandBar, /job_id|jobId/);

console.log("owner-10-second-smoke: PASS");
