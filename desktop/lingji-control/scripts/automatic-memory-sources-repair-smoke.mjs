import assert from "node:assert/strict";
import { actionAvailability, authorizationEvidence, decideOnboardingRoute } from "../src/pages/memorySourcesApi.ts";
import { ownsRequest } from "../src/hooks/usePollingResource.ts";

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
console.log("automatic-memory-sources-repair-smoke: PASS");
