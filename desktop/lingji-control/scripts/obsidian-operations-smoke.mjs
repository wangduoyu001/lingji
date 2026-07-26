import assert from "node:assert/strict";
import fs from "node:fs";

const component = fs.readFileSync(new URL("../src/components/ObsidianOperations.tsx", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../src/pages/memoryReviewApi.ts", import.meta.url), "utf8");
const contract = fs.readFileSync(new URL("../src/pages/codexWorkspaceContract.ts", import.meta.url), "utf8");
const inspector = fs.readFileSync(new URL("../src/pages/MemoryInspectorLoopPage.tsx", import.meta.url), "utf8");

assert.match(api, /\/api\/obsidian\/notes\?relative_path=/); assert.match(api, /post<ObsidianNote>\("\/api\/obsidian\/notes"/); assert.match(api, /\/api\/obsidian\/scan/);
for (const path of ["01-Inbox/Manual", "03-Knowledge/Notes", "05-Operations/Tasks"]) assert.ok(contract.includes(path), path);
assert.doesNotMatch(contract, /Core-Memory|08-Private|00-System/);
assert.match(component, /08-Private 默认不可读取/); assert.match(component, /路径不允许/); assert.match(component, /文件不存在/);
assert.match(component, /AbortController/); assert.match(component, /requestId/);
assert.match(component, /扫描 Obsidian 变化/); assert.match(component, /external_modified_core/);
for (const label of ["当前项目", "仅 Codex", "当前 Session", "仅有关联 Memory", "仅 Core Memory", "清除快捷筛选"]) assert.ok(inspector.includes(label), label);
assert.match(inspector, /project_id/); assert.match(inspector, /conversation_id/); assert.match(inspector, /memory_id/);
assert.doesNotMatch(inspector, /content|正文/); assert.match(inspector, /AbortController/); assert.match(inspector, /requestId/);
console.log("obsidian-operations-smoke: PASS");
