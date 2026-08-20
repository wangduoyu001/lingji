import type { CaptureCommon, CaptureJob, CaptureJobFilters, CaptureResultRefs } from "./captureCenterTypes";

export const CAPTURE_PAGE_SIZE = 30;
export const ACTIVE_POLL_MS = 2_000;
export const IDLE_POLL_MS = 10_000;

export const splitList = (value: string): string[] => value.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean);
export const basePayload = (input: { title: string; projects: string; tags: string; privacy: "private" | "restricted"; priority: number }): CaptureCommon => ({
  title: input.title.trim(),
  project_ids: splitList(input.projects),
  tags: splitList(input.tags),
  privacy: input.privacy,
  priority: input.priority,
  process_later: true,
  metadata: {},
});

export const buildJobsQuery = (filters: CaptureJobFilters, offset: number): string => {
  const query = new URLSearchParams({ limit: String(CAPTURE_PAGE_SIZE), offset: String(offset) });
  if (filters.status) query.set("status", filters.status);
  if (filters.sourceType) query.set("source_type", filters.sourceType);
  if (filters.q.trim()) query.set("q", filters.q.trim());
  return query.toString();
};

export const canCancel = (status: string): boolean => status === "queued" || status === "retrying";
export const canRetry = (status: string): boolean => status === "failed" || status === "cancelled";
export const hasActiveJobs = (jobs: CaptureJob[]): boolean => jobs.some((job) => ["queued", "running", "retrying"].includes(job.status));
export const restrictedClass = (privacy?: string | null): string => privacy === "restricted" ? " restricted" : "";
export const progressLabel = (job: CaptureJob): string => {
  if (typeof job.progress_current === "number" && typeof job.progress_total === "number" && job.progress_total > 0) return `${job.progress_current}/${job.progress_total}`;
  return job.outcome_summary || "未知";
};
export const safeName = (job: CaptureJob): string => job.file_name || job.filename || job.title || job.job_id;
export const resultTarget = (job: CaptureJob): CaptureResultRefs | null => job.result_refs && Object.values(job.result_refs).some(Boolean) ? job.result_refs : null;

const extension = (path: string): string => path.split(/[\\/]/).pop()?.toLowerCase().split(".").pop() || "";
export const acceptsFileMode = (path: string, mode: string): boolean => {
  const ext = extension(path);
  if (mode === "chatgpt_export") return ["zip", "json"].includes(ext);
  if (mode === "codex_report") return ext === "json";
  return ["html", "htm", "json", "txt", "md"].includes(ext);
};
export const acceptsMedia = (path: string): boolean => [
  "mp4", "mov", "mkv", "avi", "webm", "m4v", "flv", "ts", "mts", "m2ts",
  "mp3", "wav", "m4a", "aac", "flac", "ogg", "opus", "wma",
].includes(extension(path));
export const fileNameOnly = (path: string): string => path.split(/[\\/]/).pop() || "未选择文件";

export const fileModeContract = (mode: string): { source_type: string; adapter_name: string } => {
  if (mode === "chatgpt_export") return { source_type: "chatgpt_export", adapter_name: "chatgpt_export" };
  if (mode === "codex_report") return { source_type: "codex_report", adapter_name: "codex_work_report" };
  return { source_type: "web", adapter_name: "web_capture" };
};

export const validateUrl = (value: string): string | null => {
  try { const url = new URL(value); return ["http:", "https:"].includes(url.protocol) ? null : "仅支持 HTTP 或 HTTPS URL"; }
  catch { return "请输入有效网页 URL"; }
};
export const validateText = (value: string): string | null => value.trim() ? null : "正文不能为空";

export const errorLabel = (status: number, code?: string): string => {
  if (status === 401) return "需要本地授权或 Token 配置";
  if (status === 409) return code === "CAPTURE_DUPLICATE" ? "内容已存在，未重复创建任务" : "任务状态已变化，请刷新后重试";
  if (status === 503) return "Capture Service（采集服务）暂不可用";
  return "操作失败，请检查本机服务状态";
};