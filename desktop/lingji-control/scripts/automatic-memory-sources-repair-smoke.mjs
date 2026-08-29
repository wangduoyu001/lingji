import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { actionAvailability, authorizationEvidence, decideOnboardingRoute, periodicReconciliationNotice } from "../src/pages/memorySourcesApi.ts";
import { canPublishRequest, ownsRequest } from "../src/hooks/usePollingResource.ts";
import { activeAuthorizedCount, captureJobLabel, captureJobSummary, formatErrorForUi, paginationHasNext, vectorSemanticLabel } from "../src/pages/codexWorkspaceContract.ts";

const sourceText = async (path) => {
  try { return await readFile(new URL(path, import.meta.url), "utf8"); }
  catch { return ""; }
};
assert.match(periodicReconciliationNotice({ automation_mode: "periodic_reconciliation", next_reconciliation_seconds: 60 }), /之后每1分钟自动检查一次/);
assert.match(periodicReconciliationNotice({ automation_mode: "periodic_reconciliation", next_reconciliation_seconds: 900 }), /之后每15分钟自动检查一次/);
assert.match(periodicReconciliationNotice({ automation_mode: "periodic_reconciliation", next_reconciliation_seconds: 1800 }), /之后每30分钟自动检查一次/);
assert.match(periodicReconciliationNotice({ automation_mode: "periodic_reconciliation" }), /检查时间尚未获得/);
for (const invalid of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, null]) {
  const notice = periodicReconciliationNotice({ automation_mode: "periodic_reconciliation", next_reconciliation_seconds: invalid });
  assert.match(notice, /尚未获得/);
  assert.doesNotMatch(notice, /最迟 .* 分钟发现变化/);
}
assert.equal(periodicReconciliationNotice({ automation_mode: "event_watcher", next_reconciliation_seconds: 900 }), "");
const [contract, sourcesPage, overviewPage, workPage, codexPage, reviewPage, autoReviewPage, capturePage, obsidianPage, vectorPage, inspectorPage] = await Promise.all([
  sourceText("../src/pages/codexWorkspaceContract.ts"), sourceText("../src/pages/MemorySourcesPage.tsx"),
  sourceText("../src/pages/OverviewPage.tsx"), sourceText("../src/components/CurrentWorkPanel.tsx"),
  sourceText("../src/pages/CodexWorkspacePage.tsx"), sourceText("../src/pages/MemoryReviewPage.tsx"),
  sourceText("../src/pages/AutoReviewPage.tsx"), sourceText("../src/pages/CaptureCenterPage.tsx"),
  sourceText("../src/pages/ObsidianPage.tsx"), sourceText("../src/pages/VectorCenterPage.tsx"),
  sourceText("../src/pages/MemoryInspectorPage.tsx"),
]);

// Task8E safe polling fallback: source status must describe the actual
// periodic contract instead of implying a live event takeover.
assert.doesNotMatch(sourcesPage, /30 秒实时|30秒实时|实时接管/);
assert.match(sourcesPage, /periodicReconciliationNotice/);

const available = [{ status: "available", kind: "generic_ai_history" }];
const empty = [];
assert.equal(decideOnboardingRoute({ page: "overview", checked: false, readsSucceeded: false, authorized: empty, discovered: available }), null, "a failed first read must remain retryable, not route");
assert.equal(decideOnboardingRoute({ page: "activity", checked: false, readsSucceeded: true, authorized: empty, discovered: available }), null, "a user navigation must cancel a stale redirect");
assert.equal(decideOnboardingRoute({ page: "overview", checked: false, readsSucceeded: true, authorized: empty, discovered: available }), "memory_sources");
assert.equal(authorizationEvidence({ kind: "generic_ai_history", root: "/tmp/two" }, [{ source_id: "old", kind: "generic_ai_history", root: "/tmp/one", status: "authorized" }]), false, "old same-kind root cannot confirm a new authorization");
assert.equal(authorizationEvidence({ kind: "generic_ai_history", root: "/tmp/two" }, [{ source_id: "new", kind: "generic_ai_history", root: "/tmp/two", status: "current" }]), true);
assert.equal(actionAvailability("revoked", { source_id: "src-revoked", root: "/tmp/revoked", kind: "generic_ai_history" }).includes("authorize"), true);
assert.equal(actionAvailability("unsupported", { kind: "claude_desktop", root: "" }).includes("authorize"), false);
const oldRequest = {};
const freshRequest = {};
assert.equal(ownsRequest(freshRequest, oldRequest), false, "aborted pre-action poll cannot clear the newer request");
assert.equal(ownsRequest(freshRequest, freshRequest), true);
assert.equal(canPublishRequest(freshRequest, oldRequest, true), false, "aborted ordinary errors cannot overwrite a newer request");
assert.equal(canPublishRequest(freshRequest, freshRequest, true), false, "aborted current errors cannot publish");
assert.equal(canPublishRequest(freshRequest, freshRequest, false), true);
assert.equal(activeAuthorizedCount([{ status: "authorized" }, { status: "current" }, { status: "revoked" }]), 2);
assert.equal(paginationHasNext({ total: 0, offset: 0, limit: 30, has_more: false }), false);
assert.equal(paginationHasNext({ total: 31, offset: 0, limit: 30, has_more: true }), true);
assert.equal(formatErrorForUi({ message: "候选 ID 不存在", next_action: "请刷新候选列表" }), "候选 ID 不存在 下一步：请刷新候选列表");
assert.equal(formatErrorForUi({ code: "NOT_FOUND" }).includes("[object Object]"), false);
assert.equal(captureJobLabel({ source_type: "web", status: "completed" }), "文本 · 已完成");
assert.equal(captureJobSummary({ status: "completed", error_message: null }), "已完成，可在任务详情查看技术信息");
assert.equal(vectorSemanticLabel("healthy", false), "记忆可用、语义向量待配置/降级");

const failures = [];
const behavior = (name, check) => { try { check(); } catch (error) { failures.push(`${name}: ${error.message}`); } };
behavior("source count excludes revoked", () => {
  assert.match(sourcesPage, /ownerSourceName/);
  assert.match(sourcesPage, /sourceSummary/);
  assert.match(overviewPage, /正在记住什么/);
});
behavior("configuration required and ordinary work noise", () => {
  assert.match(overviewPage, /configuration_required/);
  assert.match(overviewPage, /需要先完成设置/);
  assert.doesNotMatch(workPage, /JSON\.stringify\(event\.detail\)/);
});
behavior("pagination follows backend has_more", () => {
  assert.match(contract, /paginationHasNext/);
  assert.match(codexPage, /paginationHasNext\(sessionPagination/);
  assert.match(reviewPage, /paginationHasNext\(pagination/);
});
behavior("structured shadow errors have a stable user message", () => {
  assert.match(contract, /formatErrorForUi/);
  assert.match(autoReviewPage, /formatErrorForUi\(reason/);
  assert.doesNotMatch(autoReviewPage, /String\(reason\)/);
});
behavior("text capture rows use user semantics", () => {
  assert.match(contract, /captureJobLabel/);
  assert.match(capturePage, /captureJobLabel\(job\)/);
  assert.doesNotMatch(capturePage, /job\.source_type \?\? "未知".*job\.adapter_name/);
});
behavior("obsidian load ends in a truthful terminal state", () => {
  assert.match(obsidianPage, /loadState/);
  assert.match(obsidianPage, /配置读取失败/);
  assert.match(obsidianPage, /尚未加载 Obsidian 配置/);
});
behavior("memory and vector degraded states stay consistent", () => {
  assert.match(contract, /vectorSemanticLabel/);
  assert.match(vectorPage, /vectorSemanticLabel\(/);
  assert.match(inspectorPage, /vectorSemanticLabel/);
  assert.match(vectorPage, /semanticState/);
});
if (failures.length) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else {
  console.log("automatic-memory-sources-repair-smoke: PASS (Task8E behaviors included)");
}
