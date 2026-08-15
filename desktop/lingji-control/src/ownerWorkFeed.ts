export type OwnerWorkItem = {
  id: string;
  memoryId: string | null;
  title: string;
  source: string;
  stage: "intake" | "parse" | "confirm" | "index" | "retrieve" | "memory" | "issue" | "stopped" | "unknown";
  stageLabel: string;
  status: string;
  done: string;
  nextStep: string;
  ownerActionRequired: boolean;
  ownerActionLabel: string | null;
  occurredAt: string | null;
};

export type OwnerActivityItem = {
  id: string;
  title: string;
  detail: string;
  tone: "done" | "active" | "issue" | "waiting";
  occurredAt: string | null;
};

export type OwnerWorkFeed = {
  detailsState: "ready" | "unavailable";
  detailsMessage: string;
  items: OwnerWorkItem[];
  recentActivity: OwnerActivityItem[];
  summary: {
    expectedDocuments: number | null;
    visibleItems: number;
    needsOwner: number;
    active: number;
    issues: number;
  };
};

type MemoryRow = Record<string, unknown>;
type QueueJob = Record<string, unknown>;
type EventRow = Record<string, unknown>;

const ACTIVE_STATES = new Set(["queued", "leased", "running", "retrying"]);
const REVIEW_STATES = new Set(["pending", "pending_review", "needs_review", "awaiting_review", "candidate"]);

const SOURCE_LABELS: Record<string, string> = {
  chatgpt_export: "ChatGPT 历史",
  codex_report: "Codex 工作记录",
  media: "媒体资料",
  web: "网页资料",
  text: "文本资料",
  file: "本地文件",
};

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

const asRows = (value: unknown): Record<string, unknown>[] =>
  Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object" && !Array.isArray(item))) : [];

const text = (value: unknown): string => typeof value === "string" ? value.trim() : "";

function safeRelativePath(value: unknown): string | null {
  const raw = text(value).replaceAll("\\", "/");
  if (!raw || raw.startsWith("/") || raw.startsWith("~/") || /^[A-Za-z]:\//.test(raw)) return null;
  const parts = raw.split("/").filter((part) => part && part !== "." && part !== "..");
  return parts.length ? parts.join("/") : null;
}

function safeFilename(value: unknown): string {
  const raw = text(value).replaceAll("\\", "/");
  return raw ? (raw.split("/").at(-1) ?? "").slice(0, 160) : "";
}

function sourceLabel(value: unknown): string {
  const key = text(value).toLowerCase();
  return SOURCE_LABELS[key] ?? (key || "知识库资料");
}

function jobTime(job: QueueJob): string {
  return text(job.completed_at) || text(job.updated_at) || text(job.created_at);
}

function jobTitle(job: QueueJob): string {
  const payload = asRecord(job.payload);
  return text(payload.title).slice(0, 180) || safeFilename(job.input_path) || sourceLabel(job.source_type);
}

function resultLinks(job: QueueJob): Set<string> {
  const result = asRecord(job.result);
  const links = new Set<string>();
  for (const bucket of ["created", "updated", "skipped"] as const) {
    for (const item of asRows(result[bucket])) {
      const relative = safeRelativePath(item.relative_path);
      if (relative) links.add(relative);
    }
  }
  for (const rawPath of Array.isArray(result.paths) ? result.paths : []) {
    const relative = safeRelativePath(rawPath);
    if (relative) links.add(relative);
  }
  return links;
}

function queueAction(job: QueueJob): Pick<OwnerWorkItem, "stage" | "stageLabel" | "done" | "nextStep"> {
  const status = text(job.status).toLowerCase();
  const result = asRecord(job.result);
  if (status === "queued") return { stage: "intake", stageLabel: "等待处理", done: "已进入处理队列", nextStep: "灵机会自动开始解析，你现在不用操作" };
  if (status === "leased" || status === "running") return { stage: "parse", stageLabel: "正在处理", done: "正在解析和整理这份资料", nextStep: "灵机会继续自动处理，你现在不用操作" };
  if (status === "retrying") return { stage: "parse", stageLabel: "自动重试", done: "上一次处理未完成，已经自动重试", nextStep: "灵机会继续重试，你现在不用做技术处理" };
  if (status === "failed") return { stage: "issue", stageLabel: "处理未完成", done: "自动重试已结束，失败原因已保留", nextStep: "这份资料暂未完成，可到任务记录查看原因" };
  if (status === "cancelled") return { stage: "stopped", stageLabel: "已停止", done: "处理任务已取消", nextStep: "不会继续处理，除非你重新提交" };
  if (status === "completed") {
    const created = asRows(result.created).length;
    const updated = asRows(result.updated).length;
    const skipped = asRows(result.skipped).length;
    const parts = [created ? `新增 ${created} 条` : "", updated ? `更新 ${updated} 条` : "", skipped ? `跳过 ${skipped} 条重复内容` : ""].filter(Boolean);
    const suffix = parts.length ? `（${parts.join("，")}）` : "";
    if (result.indexed === true) return { stage: "retrieve", stageLabel: "已完成，可取回", done: `已完成收纳、解析并更新索引${suffix}`, nextStep: "已经可以检索，你现在不用操作" };
    if (result.indexed === false) return { stage: "index", stageLabel: "索引待恢复", done: `已完成收纳和解析，但索引同步未成功${suffix}`, nextStep: "正文已经保留，可在高级工具查看索引状态" };
    return { stage: "memory", stageLabel: "已处理", done: `已完成收纳和解析${suffix}`, nextStep: "资料已进入知识库，你现在不用操作" };
  }
  return { stage: "unknown", stageLabel: "状态待确认", done: "已经记录这份资料，但当前处理状态尚未确认", nextStep: "灵机会继续刷新状态" };
}

function memoryItem(memory: MemoryRow, job: QueueJob | null): OwnerWorkItem {
  const relative = safeRelativePath(memory.relative_path);
  const title = (text(memory.title) || (job ? jobTitle(job) : "") || safeFilename(relative) || text(memory.memory_id) || "资料").slice(0, 180);
  const review = text(memory.review_status).toLowerCase();
  const ownerActionRequired = REVIEW_STATES.has(review);
  const action = job ? queueAction(job) : {
    stage: "memory" as const,
    stageLabel: "已进入知识库",
    done: "这份资料已经进入灵机知识库",
    nextStep: "现在不用你操作，可直接在记忆中查看",
  };
  return {
    id: text(memory.memory_id) || relative || title,
    memoryId: text(memory.memory_id) || null,
    title,
    source: job ? sourceLabel(job.source_type) : "知识库资料",
    stage: ownerActionRequired ? "confirm" : action.stage,
    stageLabel: ownerActionRequired ? "等你确认" : action.stageLabel,
    status: job ? text(job.status) || text(memory.status) || "unknown" : text(memory.status) || "unknown",
    done: ownerActionRequired ? "已经生成候选，正在等待你的确认" : action.done,
    nextStep: ownerActionRequired ? "需要你确认这条候选是否保留" : action.nextStep,
    ownerActionRequired,
    ownerActionLabel: ownerActionRequired ? "确认候选记忆" : null,
    occurredAt: job ? jobTime(job) || null : text(memory.modified_at) || text(memory.updated_at) || null,
  };
}

function jobOnlyItem(job: QueueJob): OwnerWorkItem {
  const action = queueAction(job);
  return {
    id: text(job.job_id) || jobTitle(job),
    memoryId: null,
    title: jobTitle(job),
    source: sourceLabel(job.source_type),
    stage: action.stage,
    stageLabel: action.stageLabel,
    status: text(job.status) || "unknown",
    done: action.done,
    nextStep: action.nextStep,
    ownerActionRequired: false,
    ownerActionLabel: null,
    occurredAt: jobTime(job) || null,
  };
}

function activity(event: EventRow): OwnerActivityItem | null {
  const type = text(event.event_type);
  const payload = asRecord(event.payload);
  const known: Record<string, [string, string, OwnerActivityItem["tone"]]> = {
    capture_submitted: ["已接收新资料", "资料已进入自动处理流程", "active"],
    capture_duplicate: ["发现重复资料并跳过", "没有创建重复任务或重复记忆", "done"],
    capture_job_retried: ["失败任务已自动重试", "原失败记录仍保留", "active"],
    capture_job_cancelled: ["资料处理任务已停止", "历史记录仍保留", "waiting"],
    extraction_document_created: ["已创建一条知识记录", "新资料已写入知识库", "done"],
    extraction_document_updated: ["已更新一条知识记录", "已有资料已按最新内容更新", "done"],
    extraction_document_skipped: ["重复内容已跳过", "没有重复写入知识库", "done"],
    autopilot_repair: ["已自动修复运行问题", "修复后已经重新检查", "done"],
    autopilot_cycle_failed: ["自动巡检暂时失败", "系统会在下一轮继续检查", "issue"],
  };
  const copy = known[type];
  if (!copy) return null;
  const [baseTitle, detail, tone] = copy;
  return {
    id: String(event.event_id ?? `${type}:${text(event.created_at)}`),
    title: type === "capture_submitted" && payload.source_type ? `已接收${sourceLabel(payload.source_type)}` : baseTitle,
    detail,
    tone,
    occurredAt: text(event.created_at) || null,
  };
}

export function buildOwnerWorkFeed({
  memoryResponse,
  queueResponse,
  events,
  expectedDocuments,
  limit = 20,
}: {
  memoryResponse: unknown;
  queueResponse: unknown;
  events: unknown;
  expectedDocuments: number | null;
  limit?: number;
}): OwnerWorkFeed {
  const memoryRoot = asRecord(memoryResponse);
  const memories = asRows(memoryRoot.items);
  const queueRoot = asRecord(queueResponse);
  const jobs = asRows(queueRoot.recent ?? queueRoot.jobs ?? queueResponse).sort((a, b) => jobTime(b).localeCompare(jobTime(a)));
  const byRelative = new Map<string, QueueJob>();
  for (const job of jobs) for (const relative of resultLinks(job)) if (!byRelative.has(relative)) byRelative.set(relative, job);

  const matchedJobs = new Set<string>();
  const items: OwnerWorkItem[] = memories.map((memory) => {
    const relative = safeRelativePath(memory.relative_path);
    const job = relative ? byRelative.get(relative) ?? null : null;
    if (job && job.job_id) matchedJobs.add(String(job.job_id));
    return memoryItem(memory, job);
  });

  for (const job of jobs) {
    const jobId = text(job.job_id);
    if (jobId && matchedJobs.has(jobId)) continue;
    const status = text(job.status).toLowerCase();
    if (ACTIVE_STATES.has(status) || ["failed", "completed", "cancelled"].includes(status)) items.push(jobOnlyItem(job));
  }

  items.sort((a, b) => (b.occurredAt ?? "").localeCompare(a.occurredAt ?? ""));
  const visible = items.slice(0, Math.max(1, Math.min(limit, 50)));
  const detailsUnavailable = typeof expectedDocuments === "number" && expectedDocuments > 0 && memories.length === 0;
  const recentActivity = asRows(events).map(activity).filter((item): item is OwnerActivityItem => Boolean(item)).slice(0, 8);

  return {
    detailsState: detailsUnavailable ? "unavailable" : "ready",
    detailsMessage: detailsUnavailable ? `系统统计到 ${expectedDocuments} 份资料，但当前无法读取具体明细。灵机不会用一个数字代替资料列表。` : "",
    items: visible,
    recentActivity,
    summary: {
      expectedDocuments,
      visibleItems: visible.length,
      needsOwner: visible.filter((item) => item.ownerActionRequired).length,
      active: visible.filter((item) => ACTIVE_STATES.has(item.status.toLowerCase())).length,
      issues: visible.filter((item) => item.stage === "issue").length,
    },
  };
}
