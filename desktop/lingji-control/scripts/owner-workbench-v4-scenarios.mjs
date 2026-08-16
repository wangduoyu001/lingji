import assert from "node:assert/strict";
import {
  buildOwnerAttentionItems,
  hasReviewConsistencyIssue,
  ownerAttentionSummary,
  ownerSourcesUnknown,
} from "../src/ownerWorkbenchModel.ts";

const empty = buildOwnerAttentionItems({ reviewItems: [], importSources: [], vectorRebuildRequired: false });
assert.deepEqual(empty, []);
assert.deepEqual(ownerAttentionSummary({ items: empty, sourceUnknown: false, activeWorkCount: 0 }), {
  title: "现在不用你做任何事",
  detail: "没有权限、冲突或不可逆事项等你处理。灵机会继续观察已授权来源。",
  state: "auto",
});

const memoryItems = buildOwnerAttentionItems({
  reviewItems: [{
    memory_id: "MEM-DECISION-001",
    title: "Mac 优先云端生图",
    proposal_reason: "同一要求在多个项目记录中重复出现。",
    confidence: 0.92,
  }],
  importSources: [],
  vectorRebuildRequired: false,
});
assert.equal(memoryItems.length, 1);
assert.equal(memoryItems[0].kind, "memory");
assert.equal(memoryItems[0].objectId, "MEM-DECISION-001");
assert.equal(memoryItems[0].target, "memory_review");
assert.equal(memoryItems[0].memoryId, "MEM-DECISION-001");
assert.match(memoryItems[0].detail, /重复出现/);

const importItems = buildOwnerAttentionItems({
  reviewItems: [],
  importSources: [{
    id: "codex",
    label: "Codex",
    candidates: [{ candidate_id: "CANDIDATE-42", display_name: "work-report.json", size_bytes: 2048 }],
  }],
  vectorRebuildRequired: false,
});
assert.equal(importItems.length, 1);
assert.equal(importItems[0].kind, "import");
assert.equal(importItems[0].objectId, "CANDIDATE-42");
assert.equal(importItems[0].candidateId, "CANDIDATE-42");
assert.match(importItems[0].detail, /读取正文会跨过隐私边界/);
assert.match(importItems[0].detail, /2 KB/);

const vectorItems = buildOwnerAttentionItems({ reviewItems: [], importSources: [], vectorRebuildRequired: true });
assert.equal(vectorItems.length, 1);
assert.equal(vectorItems[0].kind, "vector");
assert.equal(vectorItems[0].objectId, "vector-rebuild");
assert.match(vectorItems[0].detail, /不可逆维护/);

assert.equal(hasReviewConsistencyIssue({ pendingReviewCount: 2, reviewsLoaded: true, reviewItems: [] }), true);
assert.equal(hasReviewConsistencyIssue({ pendingReviewCount: 2, reviewsLoaded: false, reviewItems: [] }), false);
assert.equal(hasReviewConsistencyIssue({ pendingReviewCount: 2, reviewsLoaded: true, reviewItems: [{ memory_id: "MEM-1" }] }), false);

assert.equal(ownerSourcesUnknown({ reviewsLoaded: true, assistantsLoaded: true }), false);
assert.equal(ownerSourcesUnknown({ reviewsLoaded: false, assistantsLoaded: true }), true);
assert.equal(ownerSourcesUnknown({ reviewsLoaded: true, assistantsLoaded: false }), true);

const activeSummary = ownerAttentionSummary({ items: [], sourceUnknown: false, activeWorkCount: 3 });
assert.equal(activeSummary.state, "auto");
assert.match(activeSummary.detail, /自动处理 3 项工作/);

const unknownSummary = ownerAttentionSummary({ items: [], sourceUnknown: true, activeWorkCount: 3 });
assert.equal(unknownSummary.state, "unknown");
assert.match(unknownSummary.detail, /未知不会被显示成“没有待办”/);

const ownerSummary = ownerAttentionSummary({ items: memoryItems, sourceUnknown: false, activeWorkCount: 0 });
assert.equal(ownerSummary.state, "owner");
assert.match(ownerSummary.title, /1 件事真的需要你/);

console.log("owner-workbench-v4-scenarios: PASS");
