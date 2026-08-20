import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [app, pages, overview, attention, review, projector] = await Promise.all([
  readFile(new URL("../src/App.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/AppPages.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/AttentionPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/pages/MemoryReviewPage.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/ownerWorkbenchModel.ts", import.meta.url), "utf8"),
]);

assert.match(overview, /\/api\/memory\/review\/candidates\?limit=8&offset=0/);
assert.match(overview, /\/api\/assistant-hub\/status/);
assert.match(overview, /buildOwnerAttentionItems/);
assert.match(overview, /hasReviewConsistencyIssue/);
assert.match(overview, /ownerSourcesUnknown/);
assert.match(overview, /ownerAttentionSummary/);
assert.match(overview, /onOpenReview\(decision\.memoryId\)/);
assert.match(overview, /reviewMismatch/);
assert.match(overview, /系统汇总报告有待确认记忆，但当前没有读到对应候选对象/);
assert.equal(overview.includes("Math.max(pendingReviewCount, feed.summary.needsOwner)"), false, "Home must not create owner actions from summary counts");
assert.equal(overview.includes("reviewItems.map"), false, "Home must not maintain a second memory PendingAction projector");
assert.equal(overview.includes("assistantSources.flatMap"), false, "Home must not maintain a second import PendingAction projector");

assert.match(attention, /buildOwnerAttentionItems/);
assert.match(attention, /resource\.data\?\.reviews\?\.items/);
assert.match(attention, /ownerAttentionSummary/);
assert.match(attention, /ownerSourcesUnknown/);
assert.match(attention, /每个按钮背后都有一个真实对象/);
assert.match(attention, /onOpenReview\(item\.memoryId\)/);
assert.match(attention, /authorizeImport\(item\)/);
assert.match(attention, /item\.candidateId/);
assert.match(attention, /AUTHORIZE_ASSISTANT_IMPORT_/);
assert.equal(attention.includes("type OwnerItem ="), false, "Attention must not define a second PendingAction model");
assert.equal(attention.includes("const result: OwnerItem[]"), false, "Attention must not rebuild PendingActions locally");
assert.equal(attention.includes("pending_review_count"), false, "Owner inbox count must come from actual candidate objects, not a summary count");

assert.match(projector, /memory:\$\{candidate\.memory_id\}/);
assert.match(projector, /objectId: candidate\.memory_id/);
assert.match(projector, /memoryId: candidate\.memory_id/);
assert.match(projector, /import:\$\{candidate\.candidate_id\}/);
assert.match(projector, /objectId: candidate\.candidate_id/);
assert.match(projector, /candidateId: candidate\.candidate_id/);
assert.match(projector, /pendingReviewCount > 0 && reviewsLoaded && reviewItems\.length === 0/);
assert.match(projector, /items\.length > 0/);
assert.match(projector, /现在不用你做任何事/);

assert.match(app, /reviewTargetId/);
assert.match(app, /openReview/);
assert.match(app, /setReviewTargetId\(memoryId\)/);
assert.match(pages, /targetMemoryId={reviewTargetId}/);
assert.match(review, /targetMemoryId/);
assert.match(review, /client\.candidate\(targetMemoryId\)/);
assert.match(review, /已直接定位到你刚才选择的候选记忆/);

console.log("owner-home-action-consistency-smoke: PASS");
