import type { CaptureJob, CaptureJobsResponse, OwnerNextActor } from "./pages/captureCenterTypes";

export type OwnerWorkItem = {
  id: string;
  workItemId: string;
  captureId: string | null;
  memoryId: string | null;
  resultObjectIds: string[];
  title: string;
  source: string;
  stage: "intake" | "parse" | "index" | "memory" | "issue" | "stopped" | "unknown";
  stageLabel: string;
  status: string;
  done: string;
  nextStep: string;
  nextActor: OwnerNextActor;
  ownerActionRequired: boolean;
  ownerActionLabel: string | null;
  occurredAt: string | null;
};

export type OwnerActivityItem = {
  id: string;
  workItemId: string;
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

const ACTIVE_STATES = new Set(["queued", "leased", "running", "retrying"]);
const SOURCE_LABELS: Record<string, string> = {
  chatgpt_export: "ChatGPT 历史",
  codex_report: "Codex 工作记录",
  media: "媒体资料",
  web: "网页资料",
  text: "文本资料",
  file: "本地文件",
};

const text = (value: unknown): string => typeof value === "string" ? value.trim() : "";

function sourceLabel(value: unknown): string {
  const key = text(value).toLowerCase();
  return SOURCE_LABELS[key] ?? (key || "资料");
}

function stageFor(job: CaptureJob): Pick<OwnerWorkItem, "stage" | "stageLabel"> {
  const status = text(job.status).toLowerCase();
  if (status === "queued") return { stage: "intake", stageLabel: "等待处理" };
  if (status === "leased" || status === "running") return { stage: "parse", stageLabel: "正在处理" };
  if (status === "retrying") return { stage: "parse", stageLabel: "自动重试" };
  if (status === "failed") return { stage: "issue", stageLabel: "处理未完成" };
  if (status === "cancelled") return { stage: "stopped", stageLabel: "已停止" };
  if (status === "completed") {
    return job.result_refs?.memory_id || (job.result_object_ids?.length ?? 0) > 0
      ? { stage: "memory", stageLabel: "已产生结果" }
      : { stage: "index", stageLabel: "已完成" };
  }
  return { stage: "unknown", stageLabel: "状态待确认" };
}

function fallbackOutcome(status: string): string {
  if (status === "queued") return "已进入处理队列，尚未产生执行结果。";
  if (status === "running" || status === "leased") return "正在执行解析和整理。";
  if (status === "retrying") return "上一次执行未完成，正在自动重试。";
  if (status === "failed") return "自动执行和既定重试已结束，失败证据已保留。";
  if (status === "cancelled") return "这项工作已停止。";
  if (status === "completed") return "工作已完成，具体结果以持久化结果对象为准。";
  return "这项工作已被记录，但当前结果未知。";
}

function fallbackNext(status: string): string {
  if (ACTIVE_STATES.has(status)) return "灵机会继续当前已记录的工作。";
  if (status === "failed") return "没有自动生成主人待办；需要排查时可在高级任务记录中手动处理。";
  if (status === "cancelled") return "除非重新提交，否则不会继续执行。";
  if (status === "completed") return "工作已完成；是否形成记忆以真实结果对象为准。";
  return "等待真实状态更新，不推测后续动作。";
}

function jobTime(job: CaptureJob): string | null {
  return text(job.completed_at) || text(job.updated_at) || text(job.created_at) || null;
}

function workItem(job: CaptureJob): OwnerWorkItem {
  const workItemId = text(job.work_item_id) || text(job.job_id);
  const status = text(job.status).toLowerCase() || "unknown";
  const nextActor = text(job.next_actor) || (ACTIVE_STATES.has(status) ? "system" : "none");
  const stage = stageFor(job);
  const memoryId = text(job.result_refs?.memory_id) || null;
  return {
    id: workItemId,
    workItemId,
    captureId: text(job.capture_id) || null,
    memoryId,
    resultObjectIds: (job.result_object_ids ?? []).filter((value): value is string => Boolean(text(value))),
    title: text(job.title) || text(job.file_name) || sourceLabel(job.source_type),
    source: sourceLabel(job.source_type),
    stage: stage.stage,
    stageLabel: stage.stageLabel,
    status,
    done: text(job.outcome_summary) || fallbackOutcome(status),
    nextStep: text(job.next_action) || fallbackNext(status),
    nextActor,
    ownerActionRequired: nextActor === "owner",
    ownerActionLabel: nextActor === "owner" ? "需要主人处理" : null,
    occurredAt: jobTime(job),
  };
}

function activityFor(item: OwnerWorkItem): OwnerActivityItem | null {
  if (ACTIVE_STATES.has(item.status)) return null;
  const tone: OwnerActivityItem["tone"] = item.stage === "issue"
    ? "issue"
    : item.stage === "stopped"
      ? "waiting"
      : "done";
  return {
    id: `work:${item.workItemId}`,
    workItemId: item.workItemId,
    title: item.title,
    detail: item.done,
    tone,
    occurredAt: item.occurredAt,
  };
}

function asJobsResponse(value: unknown): CaptureJobsResponse | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const root = value as Partial<CaptureJobsResponse>;
  if (!Array.isArray(root.items)) return null;
  return root as CaptureJobsResponse;
}

export function buildOwnerWorkFeed({
  jobsResponse,
  expectedDocuments,
  limit = 20,
}: {
  jobsResponse: unknown;
  expectedDocuments: number | null;
  limit?: number;
}): OwnerWorkFeed {
  const jobsRoot = asJobsResponse(jobsResponse);
  const jobs = jobsRoot?.items ?? [];
  const items = jobs
    .map(workItem)
    .filter((item) => Boolean(item.workItemId))
    .sort((a, b) => (b.occurredAt ?? "").localeCompare(a.occurredAt ?? ""));
  const visible = items.slice(0, Math.max(1, Math.min(limit, 50)));
  const recentActivity = visible
    .map(activityFor)
    .filter((item): item is OwnerActivityItem => Boolean(item))
    .slice(0, 8);

  return {
    detailsState: jobsRoot ? "ready" : "unavailable",
    detailsMessage: jobsRoot
      ? ""
      : "真实 WorkItem 列表暂时不可用。灵机不会用记忆数量或静态事件冒充工作履历。",
    items: visible,
    recentActivity,
    summary: {
      expectedDocuments,
      visibleItems: visible.length,
      needsOwner: visible.filter((item) => item.ownerActionRequired).length,
      active: visible.filter((item) => ACTIVE_STATES.has(item.status)).length,
      issues: visible.filter((item) => item.stage === "issue").length,
    },
  };
}
