import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const root = new URL("../", import.meta.url);
const quick = readFileSync(new URL("src/components/QuickCapture.tsx", root), "utf8");
const app = readFileSync(new URL("src/App.tsx", root), "utf8");
const api = readFileSync(new URL("src/pages/captureCenterApi.ts", root), "utf8");
const types = readFileSync(new URL("src/pages/captureCenterTypes.ts", root), "utf8");

assert.ok(app.includes("<QuickCapture"));
assert.ok(app.includes("<RuntimeBoundary"));
assert.ok(app.includes("NAVIGATION"));
assert.ok(quick.includes("event.metaKey || event.ctrlKey"));
assert.ok(quick.includes('event.key.toLowerCase() !== "k"'));
assert.ok(quick.includes("client.submitText"));
assert.ok(api.includes('this.api.post("/api/capture/text"'));
assert.ok(types.includes("work_id?: string | null"));
assert.ok(quick.includes("result.work_id"));
assert.ok(quick.includes('onNavigate("activity")'));
assert.ok(quick.includes("提交失败，内容已保留"));
assert.ok(quick.includes("不能宣称已接手"));
assert.ok(!quick.includes("/api/memory"));
assert.ok(!quick.includes("localStorage"));

console.log("quick-capture-smoke: PASS");
