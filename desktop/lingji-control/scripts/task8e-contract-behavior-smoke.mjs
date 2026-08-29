import assert from "node:assert/strict";
import { ApiError } from "../src/api.ts";
import { formatErrorForUi, vectorSemanticLabel } from "../src/pages/codexWorkspaceContract.ts";
import { normalizeReviewPage } from "../src/pages/memoryReviewApi.ts";
import { mapStatus } from "../src/pages/memoryInspectorContract.ts";

const candidate = (memory_id) => ({ memory_id, title: `候选 ${memory_id}` });

const firstPage = normalizeReviewPage({ items: Array.from({ length: 30 }, (_, index) => candidate(index)), total: 31, limit: 30, offset: 0 });
assert.equal(firstPage.pagination.total, 31);
assert.equal(firstPage.pagination.limit, 30);
assert.equal(firstPage.pagination.offset, 0);
assert.equal(firstPage.pagination.has_more, true, "real review_service DTO must enable a next page");
const lastPage = normalizeReviewPage({ items: [candidate(30)], total: 31, limit: 30, offset: 30 });
assert.equal(lastPage.pagination.has_more, false, "the final review page must disable next");
assert.equal(normalizeReviewPage({ items: [], total: 0, limit: 30, offset: 0 }).pagination.has_more, false, "empty review results must disable next");

const structuredError = formatErrorForUi(new ApiError(404, "MEMORY_CANDIDATE_NOT_FOUND", "[object Object]"));
assert.equal(structuredError.includes("[object Object]"), false);
assert.match(structuredError, /候选记忆/);
assert.equal(formatErrorForUi({ detail: { code: "MEMORY_CANDIDATE_NOT_FOUND" } }).includes("[object Object]"), false);

for (const vectorState of ["disabled", "degraded", "unavailable", "configuration_required"]) {
  const expected = "记忆可用、语义向量待配置/降级";
  assert.equal(vectorSemanticLabel("healthy", null, vectorState), expected, `Vector Center ${vectorState} wording`);
  assert.equal(mapStatus({ memory: { state: "healthy" }, vector: { state: vectorState } }).vectorSemanticLabel, expected, `Inspector ${vectorState} wording`);
}
const unavailableMemory = mapStatus({ memory: { state: "unavailable" }, vector: { state: "disabled" } }).vectorSemanticLabel;
assert.match(unavailableMemory, /记忆不可用/);

console.log("task8e-contract-behavior-smoke: PASS");
