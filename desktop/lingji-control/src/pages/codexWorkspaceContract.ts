import type { ReviewFilters } from "./memoryReviewTypes";
import type { WorkspaceFilters } from "./codexWorkspaceTypes";

export const WORKSPACE_LIMIT = 30;
export const REVIEW_LIMIT = 30;
export const ACTIVE_POLL_MS = 1000;
export const IDLE_POLL_MS = 5000;

export type PagePagination = { limit?: number; offset?: number; total?: number | null; has_more?: boolean } | null | undefined;

export function activeAuthorizedCount(sources: Array<{ status?: string | null }>): number {
  return sources.filter((source) => ["authorized", "scanning", "current"].includes(String(source.status))).length;
}

export function paginationHasNext(pagination: PagePagination): boolean {
  if (!pagination) return false;
  if (typeof pagination.has_more === "boolean") return pagination.has_more;
  if (typeof pagination.total !== "number" || typeof pagination.offset !== "number" || typeof pagination.limit !== "number") return false;
  return pagination.offset + pagination.limit < pagination.total;
}

export function formatErrorForUi(reason: unknown, fallback = "操作失败，请检查本机服务状态后重试。"): string {
  const value = reason && typeof reason === "object" ? reason as Record<string, unknown> : null;
  const detail = value?.detail && typeof value.detail === "object" ? value.detail as Record<string, unknown> : null;
  const code = [value?.code, detail?.code].find((item): item is string => typeof item === "string" && item.trim().length > 0);
  const codeMessages: Record<string, string> = {
    MEMORY_CANDIDATE_NOT_FOUND: "候选记忆不存在，请刷新后重试。",
    MEMORY_REVIEW_CONFLICT: "候选记忆已变化，请刷新后重试。",
    PROJECT_ACCESS_DENIED: "当前项目无权访问，请切换项目后重试。",
  };
  const rawMessage = reason instanceof Error ? reason.message : typeof reason === "string" ? reason : [value?.message, value?.detail, value?.error].find((item): item is string => typeof item === "string" && item.trim().length > 0);
  const message = rawMessage && rawMessage.trim() !== "[object Object]" ? rawMessage : "";
  if (message) {
    const next = typeof value?.next_action === "string" && value.next_action.trim() ? value.next_action : "";
    return next ? `${message} 下一步：${next}` : message;
  }
  if (code) return codeMessages[code] ?? `操作失败（${code}），请检查本机服务状态后重试。`;
  return fallback;
}

export function captureJobLabel(job: { source_type?: string | null; status?: string | null; title?: string | null }): string {
  const source = String(job.source_type ?? "capture");
  const sourceLabel = source === "web" ? "文本" : source === "chatgpt_export" ? "ChatGPT 导出" : source === "codex_report" ? "Codex 报告" : source;
  const statusLabel: Record<string, string> = { completed: "已完成", queued: "排队中", running: "处理中", retrying: "重试中", failed: "失败", cancelled: "已取消" };
  return `${sourceLabel} · ${statusLabel[String(job.status)] ?? "状态未知"}`;
}

export function captureJobSummary(job: { status?: string | null; error_message?: string | null }): string {
  if (String(job.status) === "completed") return "已完成，可在任务详情查看技术信息";
  return job.error_message || "暂无错误摘要";
}

export function vectorSemanticLabel(memoryState?: string | null, embeddingAvailable?: boolean | null, vectorState?: string | null): string {
  const normalizedMemory = String(memoryState ?? "");
  const normalizedVector = String(vectorState ?? "");
  const vectorUnavailable = embeddingAvailable === false || ["disabled", "degraded", "unavailable", "configuration_required"].includes(normalizedVector);
  if (["healthy", "ready"].includes(normalizedMemory) && vectorUnavailable) return "记忆可用、语义向量待配置/降级";
  if (["healthy", "ready"].includes(normalizedMemory)) return "记忆可用";
  if (["unavailable", "failed", "degraded", "configuration_required"].includes(normalizedMemory)) return vectorUnavailable ? "记忆不可用、语义向量待配置/降级" : "记忆不可用";
  if (["disabled", "degraded", "unavailable", "configuration_required"].includes(normalizedVector)) return "语义向量待配置/降级";
  if (vectorState) return `向量状态：${vectorState}`;
  return "记忆状态尚未获得";
}

export function queryString(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)); });
  return params.toString();
}

export function workspaceQuery(filters: WorkspaceFilters): string {
  return queryString({ project_id: filters.projectId, status: filters.status, q: filters.q, limit: filters.limit, offset: filters.offset });
}

export function reviewQuery(filters: ReviewFilters): string {
  return queryString({ project_id: filters.projectId, agent_id: filters.agent, memory_type: filters.type, importance: filters.importance, q: filters.q, limit: filters.limit, offset: filters.offset });
}

export function displayPath(value?: string): string {
  if (!value) return "未知";
  const parts = value.replace(/\\/g, "/").split("/").filter(Boolean);
  return parts.slice(-2).join("/") || "未知";
}

export function progressLabel(current?: number | null, total?: number | null, stage?: string): string {
  return typeof current === "number" && typeof total === "number" && total > 0 ? `${Math.min(100, Math.round((current / total) * 100))}%` : (stage || "处理中");
}

export function canApprove(hash?: string): boolean { return Boolean(hash); }
export function integrityMessage(state: string): string {
  if (state === "external_modified") return "Obsidian 文件已被手动修改。Codex 仍使用最后批准版本，等待你确认。";
  if (state === "missing") return "Obsidian 文件缺失。长期记忆尚未永久删除。";
  return "长期记忆文件健康。";
}

export const OBSIDIAN_ALLOWED_DIRECTORIES = ["01-Inbox/Manual", "03-Knowledge/Notes", "05-Operations/Tasks"] as const;
export function isAllowedObsidianDirectory(value: string): boolean { return OBSIDIAN_ALLOWED_DIRECTORIES.includes(value as typeof OBSIDIAN_ALLOWED_DIRECTORIES[number]); }
