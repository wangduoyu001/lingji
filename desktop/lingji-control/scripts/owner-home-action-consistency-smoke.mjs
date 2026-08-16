import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [app, pages, overview, attention, review] = await Promise.all([
  readFile(new URL("../src/App.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/AppPages.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/AttentionPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/MemoryReviewPage.tsx", import.meta.url), "utf8"),
]);

assert.match(overview, /\/api\/memory\/review\/candidates\?limit=8&offset=0/);
assert.match(overview, /\/api\/assistant-hub\/status/);
assert.match(overview, /reviewItems\.slice\(0, 3\)/);
assert.match(overview, /candidate\.memory_id/);
assert.match(overview, /candidate\.candidate_id/);
assert.match(overview, /memoryId: candidate\.memory_id/);
assert.match(overview, /onOpenReview\(decision\.memoryId\)/);
assert.match(overview, /reviewMismatch/);
assert.match(overview, /pendingReviewCount > 0 && resource\.data\?\.reviews !== null && reviewItems\.length === 0/);
assert.match(overview, /不会给你一个会打开空页面的“去处理”按钮/);
assert.equal(overview.includes("Math.max(pendingReviewCount, feed.summary.needsOwner)"), false, "V4 home must not create owner actions from summary counts");

assert.match(attention, /resource\.data\?\.reviews\?\.items/);
assert.match(attention, /candidate\.memory_id/);
assert.match(attention, /source\.candidates/);
assert.match(attention, /candidate\.candidate_id/);
assert.match(attention, /每个按钮背后都有一个真实对象/);
assert.match(attention, /onOpenReview\(item\.candidate\.memory_id\)/);
assert.match(attention, /authorizeImport/);
assert.match(attention, /AUTHORIZE_ASSISTANT_IMPORT_/);
assert.equal(attention.includes("pending_review_count"), false, "Owner inbox count must come from actual candidate objects, not a summary count");

assert.match(app, /reviewTargetId/);
assert.match(app, /openReview/);
assert.match(app, /setReviewTargetId\(memoryId\)/);
assert.match(pages, /targetMemoryId={reviewTargetId}/);
assert.match(review, /targetMemoryId/);
assert.match(review, /client\.candidate\(targetMemoryId\)/);
assert.match(review, /已直接定位到你刚才选择的候选记忆/);

console.log("owner-home-action-consistency-smoke: PASS");
