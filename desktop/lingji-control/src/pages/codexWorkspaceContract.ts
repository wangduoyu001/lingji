import type { ReviewFilters } from "./memoryReviewTypes";
import type { WorkspaceFilters } from "./codexWorkspaceTypes";

export const WORKSPACE_LIMIT = 30;
export const REVIEW_LIMIT = 30;
export const ACTIVE_POLL_MS = 1000;
export const IDLE_POLL_MS = 5000;

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
