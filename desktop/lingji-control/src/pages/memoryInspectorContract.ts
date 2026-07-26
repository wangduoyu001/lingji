import type { InspectorFilters, InspectorStatusResponse, MemorySourceResponse, MemoryVectorResponse, MessageDetailResponse } from "./memoryInspectorTypes";

export const INSPECTOR_LIMIT = 30;

const clean = (params: Record<string, string | undefined>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined),
  ) as Record<string, string>;

export const buildSourceQuery = (filters: InspectorFilters, offset: number): Record<string, string> => clean({
  source_type: filters.sourceType,
  privacy: filters.privacy,
  project: filters.project,
  status: filters.status,
  q: filters.q,
  limit: String(INSPECTOR_LIMIT),
  offset: String(offset),
});

export const buildConversationQuery = (filters: InspectorFilters, sourceId: string, offset: number): Record<string, string> => clean({
  source_id: sourceId,
  source_type: filters.sourceType,
  privacy: filters.privacy,
  project: filters.project,
  from_time: filters.fromTime,
  to_time: filters.toTime,
  q: filters.q,
  limit: String(INSPECTOR_LIMIT),
  offset: String(offset),
});

export const buildMessageQuery = (filters: InspectorFilters, sourceId: string, conversationId: string, offset: number): Record<string, string> => clean({
  conversation_id: conversationId,
  source_id: sourceId,
  role: filters.role,
  from_time: filters.fromTime,
  to_time: filters.toTime,
  q: filters.q,
  limit: String(INSPECTOR_LIMIT),
  offset: String(offset),
});

export const toQueryString = (params: Record<string, string>): string => new URLSearchParams(
  Object.entries(params).map(([key, value]: [string, string]) => [key, String(value)]),
).toString();

export const mapStatus = (response: InspectorStatusResponse | Record<string, unknown>) => ({
  sources: (response as InspectorStatusResponse)?.sources?.sources ?? null,
  conversations: (response as InspectorStatusResponse)?.sources?.conversations ?? null,
  messages: (response as InspectorStatusResponse)?.sources?.messages ?? null,
  memories: (response as InspectorStatusResponse)?.memory?.documents ?? null,
  chunks: (response as InspectorStatusResponse)?.memory?.chunks ?? null,
  vectorCoverage: (response as Record<string, Record<string, unknown>>)?.vector?.coverage ?? null,
  vectorState: (response as Record<string, Record<string, unknown>>)?.vector?.state ?? null,
  rebuildRequired: (response as Record<string, Record<string, unknown>>)?.vector?.rebuild_required ?? null,
  asOf: (response as Record<string, string>)?.as_of ?? null,
});

export const mapMessageDetail = (response: MessageDetailResponse | Record<string, unknown>) => ({
  item: (response as MessageDetailResponse)?.item ?? null,
  memoryLinks: Array.isArray((response as MessageDetailResponse)?.memory_links) ? (response as MessageDetailResponse).memory_links : [],
});

export const mapMemoryVector = (response: MemoryVectorResponse | Record<string, unknown>) => (response as MemoryVectorResponse)?.vector ?? null;

export const mapMemorySource = (response: MemorySourceResponse | Record<string, unknown>) => ({
  canonical: (response as MemorySourceResponse)?.canonical ?? null,
  links: Array.isArray((response as MemorySourceResponse)?.links) ? (response as MemorySourceResponse).links! : [],
});

export const formatList = (value: unknown): string => {
  if (!Array.isArray(value) || value.length === 0) return "未知";
  return value.map((item: unknown) => {
    if (typeof item === "string" || typeof item === "number") return String(item);
    if (item && typeof item === "object") return String((item as Record<string, unknown>).name ?? (item as Record<string, unknown>).title ?? (item as Record<string, unknown>).id ?? (item as Record<string, unknown>).value ?? "未知项");
    return "未知项";
  }).join("、");
};

export const isRestricted = (row: Record<string, unknown>): boolean => String(row?.privacy ?? "").toLowerCase() === "restricted";

export const rebuildLabel = (value: unknown): string => value === true ? "需要重建" : value === false ? "无需重建" : "未知";

export const countLabel = (value: unknown): string => typeof value === "number" ? value.toLocaleString() : "未知";
