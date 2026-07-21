import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  acceptsFileMode,
  acceptsMedia,
  basePayload,
  buildJobsQuery,
  canCancel,
  canRetry,
  errorLabel,
  fileModeContract,
  fileNameOnly,
  resultTarget,
  restrictedClass,
  safeName,
  validateText,
  validateUrl,
} from "../src/pages/captureCenterContract";

const root = new URL("../", import.meta.url);
const page = readFileSync(new URL("src/pages/CaptureCenterPage.tsx", root), "utf8");
const api = readFileSync(new URL("src/pages/captureCenterApi.ts", root), "utf8");
const app = readFileSync(new URL("src/App.tsx", root), "utf8");
const navigation = readFileSync(new URL("src/navigation.ts", root), "utf8");
const main = readFileSync(new URL("src-tauri/src/main.rs", root), "utf8");
const capability = readFileSync(new URL("src-tauri/capabilities/default.json", root), "utf8");

assert.ok(navigation.includes('id: "capture_center"'));
assert.ok(app.includes("<CaptureCenterPage"));
for (const endpoint of [
  "/api/capture/text",
  "/api/capture/web",
  "/api/capture/file",
  "/api/capture/media",
  "/api/capture/status",
  "/api/capture/capabilities",
  "/api/capture/jobs",
  "/retry",
  "/cancel",
  "/api/capture/pause",
  "/api/capture/resume",
]) assert.ok(api.includes(endpoint), `missing endpoint ${endpoint}`);

const payload = basePayload({ title: "A", projects: "p1,p2", tags: "t1，t2", privacy: "private", priority: 2 });
assert.equal(payload.process_later, true);
assert.deepEqual(payload.project_ids, ["p1", "p2"]);
assert.deepEqual(payload.tags, ["t1", "t2"]);
assert.equal(validateText(""), "正文不能为空");
assert.equal(validateText("ok"), null);
assert.equal(validateUrl("not-a-url"), "请输入有效网页 URL");
assert.equal(validateUrl("https://example.com"), null);

const query = new URLSearchParams(buildJobsQuery({ status: "failed", sourceType: "web", q: "abc" }, 30));
assert.equal(query.get("limit"), "30");
assert.equal(query.get("offset"), "30");
assert.equal(query.get("status"), "failed");
assert.equal(query.get("source_type"), "web");
assert.equal(query.get("q"), "abc");

assert.equal(acceptsFileMode("capture.html", "web_snapshot"), true);
assert.equal(acceptsFileMode("capture.md", "web_snapshot"), true);
assert.equal(acceptsFileMode("chatgpt.zip", "chatgpt_export"), true);
assert.equal(acceptsFileMode("report.txt", "codex_report"), false);
assert.deepEqual(fileModeContract("web_snapshot"), { source_type: "web", adapter_name: "web_capture" });
assert.deepEqual(fileModeContract("chatgpt_export"), { source_type: "chatgpt_export", adapter_name: "chatgpt_export" });
assert.deepEqual(fileModeContract("codex_report"), { source_type: "codex_report", adapter_name: "codex_work_report" });
assert.equal(acceptsMedia("clip.mp4"), true);
assert.equal(acceptsMedia("voice.flac"), true);
assert.equal(acceptsMedia("image.png"), false);
assert.equal(acceptsMedia("document.pdf"), false);
assert.equal(fileNameOnly("C:\\secret\\clip.mp4"), "clip.mp4");
assert.equal(fileNameOnly("/home/user/clip.mp4"), "clip.mp4");
assert.equal(safeName({ job_id: "J1", status: "queued", file_name: "safe.txt" }), "safe.txt");

assert.equal(canCancel("queued"), true);
assert.equal(canCancel("retrying"), true);
assert.equal(canCancel("running"), false);
assert.equal(canRetry("failed"), true);
assert.equal(canRetry("cancelled"), true);
assert.equal(canRetry("completed"), false);
assert.ok(resultTarget({ job_id: "J1", status: "completed", result_refs: { memory_id: "M1" } }));
assert.equal(restrictedClass("restricted"), " restricted");

assert.equal(errorLabel(401), "需要本地授权或 Token 配置");
assert.equal(errorLabel(409, "CAPTURE_DUPLICATE"), "内容已存在，未重复创建任务");
assert.equal(errorLabel(503), "Capture Service（采集服务）暂不可用");

assert.ok(page.includes("AbortController"));
assert.ok(page.includes("requestIdRef"));
assert.ok(page.includes("directory: false"));
assert.ok(page.includes("multiple: false"));
assert.ok(page.includes("filters"));
assert.ok(!page.includes(">正常</button>"));
assert.ok(!page.includes(">低功耗</button>"));
assert.ok(page.includes("处理中，当前版本不支持强制终止"));
assert.ok(page.includes("onOpenInspector"));
assert.ok(!page.includes("payload"));
assert.ok(!page.includes("lease_token"));
assert.ok(main.includes("tauri_plugin_dialog::init()"));
assert.ok(capability.includes('"dialog:default"'));

console.log("capture-center-smoke: PASS");
