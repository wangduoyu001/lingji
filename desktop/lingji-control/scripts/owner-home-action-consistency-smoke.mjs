import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const overview = await readFile(new URL("../src/pages/OverviewPage.tsx", import.meta.url), "utf8");

assert.match(
  overview,
  /const reviewDecisionCount = Math\.max\(pendingReviewCount, feed\.summary\.needsOwner\)/,
  "top owner action count must include concrete pending-review rows from Owner Work Feed",
);
assert.match(
  overview,
  /if \(item\.ownerActionRequired\) return "memory_review"/,
  "a row that says owner confirmation is required must open the memory review page directly",
);
assert.match(overview, /现在不用你做任何事/);
assert.match(overview, /需要你处理/);

console.log("owner-home-action-consistency-smoke: PASS");
