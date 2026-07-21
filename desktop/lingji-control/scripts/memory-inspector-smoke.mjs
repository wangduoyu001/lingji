import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const contract = await import("../src/pages/memoryInspectorContract.ts");

const filters = {
  sourceType: "chatgpt",
  project: "lingji",
  privacy: "private",
  status: "active",
  role: "user",
  q: "memory",
  fromTime: "2026-07-01T00:00:00",
  toTime: "2026-07-21T23:59:59",
};

const sourceQuery = contract.buildSourceQuery(filters, 0);
assert.deepEqual(Object.keys(sourceQuery).sort(), ["limit", "offset", "privacy", "project", "q", "source_type", "status"].sort());
assert.equal(sourceQuery.q, "memory");
assert.ok(!("from_time" in sourceQuery));
assert.ok(!("to_time" in sourceQuery));

const conversationQuery = contract.buildConversationQuery(filters, "SRC-1", 30);
assert.deepEqual(Object.keys(conversationQuery).sort(), ["from_time", "limit", "offset", "privacy", "project", "q", "source_id", "source_type", "to_time"].sort());
assert.ok(!("status" in conversationQuery));
assert.ok(!("role" in conversationQuery));

const messageQuery = contract.buildMessageQuery(filters, "SRC-1", "CONV-1", 60);
assert.deepEqual(Object.keys(messageQuery).sort(), ["conversation_id", "from_time", "limit", "offset", "q", "role", "source_id", "to_time"].sort());
for (const illegal of ["project", "privacy", "status", "source_type"]) assert.ok(!(illegal in messageQuery));

const summary = contract.mapStatus({
  as_of: "2026-07-21T00:00:00Z",
  sources: { sources: 2, conversations: 3, messages: 4 },
  memory: { documents: 5, chunks: 6 },
  vector: { coverage: 0.75, rebuild_required: null, state: "healthy" },
});
assert.deepEqual(summary, {
  sources: 2,
  conversations: 3,
  messages: 4,
  memories: 5,
  chunks: 6,
  vectorCoverage: 0.75,
  vectorState: "healthy",
  rebuildRequired: null,
  asOf: "2026-07-21T00:00:00Z",
});
assert.equal(contract.mapStatus({}).sources, null);
assert.equal(contract.countLabel(undefined), "未知");

const messageDetail = contract.mapMessageDetail({
  item: {
    message_id: "MSG-1",
    occurred_at: "2026-07-21T12:00:00Z",
    content_preview: "preview",
    metadata: { model: "gpt-5.6", is_branch: true },
  },
  memory_links: [{ memory_id: "MEM-1", relation_type: "derived_from", confidence: 0.9 }],
});
assert.equal(messageDetail.item.occurred_at, "2026-07-21T12:00:00Z");
assert.equal(messageDetail.item.metadata.model, "gpt-5.6");
assert.equal(messageDetail.item.metadata.is_branch, true);
assert.equal(messageDetail.memoryLinks[0].memory_id, "MEM-1");

assert.equal(contract.formatList(["a", { name: "b" }, { id: "c" }]), "a、b、c");
assert.equal(contract.isRestricted({ privacy: "restricted" }), true);
assert.equal(contract.isRestricted({ privacy: "private" }), false);

const vector = contract.mapMemoryVector({ memory_id: "MEM-1", vector: { state: "ready", rebuild_required: false, chunks: [{ chunk_id: "C-1" }] } });
assert.equal(vector.state, "ready");
assert.equal(vector.rebuild_required, false);
assert.equal(vector.chunks[0].chunk_id, "C-1");

const source = contract.mapMemorySource({ canonical: { relative_path: "Memory/a.md", citations: [{ chunk_id: "C-1", relative_path: "Memory/a.md", start_line: 1, end_line: 3 }] }, links: [{ message_id: "MSG-1" }] });
assert.equal(source.canonical.relative_path, "Memory/a.md");
assert.equal(source.canonical.citations[0].chunk_id, "C-1");
assert.equal(source.canonical.citations[0].start_line, 1);
assert.equal(source.canonical.citations[0].end_line, 3);
assert.equal(source.links[0].message_id, "MSG-1");

assert.equal(contract.rebuildLabel(true), "需要重建");
assert.equal(contract.rebuildLabel(false), "无需重建");
assert.equal(contract.rebuildLabel(null), "未知");

const page = readFileSync(new URL("../src/pages/MemoryInspectorPage.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");
const navigation = readFileSync(new URL("../src/navigation.ts", import.meta.url), "utf8");
const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
assert.ok(page.includes("AbortController") && page.includes("messageRequestId") && page.includes("memoryRequestId"));
assert.ok(page.includes("row.metadata?.model") && page.includes("row.metadata?.is_branch"));
assert.ok(page.includes("isRestricted(row)"), "restricted state must be evaluated per message row");
assert.ok(api.includes("ApiError") && api.includes("timeoutMs") && api.includes("signal"));
assert.ok(navigation.includes("memory_inspector") && app.includes("<MemoryInspectorPage"));

console.log("memory-inspector-smoke: PASS");
