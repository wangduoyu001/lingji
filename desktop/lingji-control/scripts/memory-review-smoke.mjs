import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("../src/pages/MemoryReviewPage.tsx", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../src/pages/memoryReviewApi.ts", import.meta.url), "utf8");
const contract = fs.readFileSync(new URL("../src/pages/codexWorkspaceContract.ts", import.meta.url), "utf8");
const nav = fs.readFileSync(new URL("../src/navigation.ts", import.meta.url), "utf8");

assert.match(nav, /memory_review/);
for (const path of ["/api/memory/review/candidates", "/approve", "/edit-approve", "/reject", "/api/memory/core", "/archive", "/integrity"]) assert.ok(api.includes(path), path);
assert.match(page, /selected\.current_hash/);
assert.match(api, /expected_content_hash/);
assert.match(api, /owner_confirmed: true/);
assert.match(page, /候选内容已变化，请刷新后重新审核/); assert.match(page, /批准/); assert.match(page, /编辑后批准/); assert.match(page, /拒绝理由/);
assert.match(page, /确认加入长期记忆/); assert.match(page, /归档后不再默认注入 Codex，但不会物理删除文件/);
assert.match(page, /来源：/); assert.match(page, /对话：/); assert.match(page, /原文片段：/); assert.match(page, /当前状态：/); assert.match(page, /历史状态：/); assert.match(page, /为什么：/);
assert.match(page, /打开来源检查/); assert.match(page, /打开原文检查/);
assert.doesNotMatch(page, /永久删除/); assert.doesNotMatch(page, /HMAC|Tombstone|复杂 Merge/);
assert.match(contract, /external_modified/); assert.match(contract, /missing/);
assert.match(page, /AbortController/); assert.match(page, /requestId/);
assert.match(page, /error\.status === 409/); assert.match(page, /error\.status === 401/); assert.match(page, /error\.status === 503/);
console.log("memory-review-smoke: PASS");
