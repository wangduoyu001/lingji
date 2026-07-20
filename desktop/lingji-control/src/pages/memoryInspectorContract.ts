export const INSPECTOR_LIMIT = 30;

const clean = (params) => Object.fromEntries(
  Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined),
);

export const buildSourceQuery = (filters, offset) => clean({
  source_type: filters.sourceType,
  privacy: filters.privacy,
  project: filters.project,
  status: filters.status,
  q: filters.q,
  limit: INSPECTOR_LIMIT,
  offset,
});

export const buildConversationQuery = (filters, sourceId, offset) => clean({
  source_id: sourceId,
  source_type: filters.sourceType,
  privacy: filters.privacy,
  project: filters.project,
  from_time: filters.fromTime,
  to_time: filters.toTime,
  q: filters.q,
  limit: INSPECTOR_LIMIT,
  offset,
});

export const buildMessageQuery = (filters, sourceId, conversationId, offset) => clean({
  conversation_id: conversationId,
  source_id: sourceId,
  role: filters.role,
  from_time: filters.fromTime,
  to_time: filters.toTime,
  q: filters.q,
  limit: INSPECTOR_LIMIT,
  offset,
});

export const toQueryString = (params) => new URLSearchParams(
  Object.entries(params).map(([key, value]) => [key, String(value)]),
).toString();

export const mapStatus = (response) => ({
  sources: response?.sources?.sources ?? null,
  conversations: response?.sources?.conversations ?? null,
  messages: response?.sources?.messages ?? null,
  memories: response?.memory?.documents ?? null,
  chunks: response?.memory?.chunks ?? null,
  vectorCoverage: response?.vector?.coverage ?? null,
  vectorState: response?.vector?.state ?? null,
  rebuildRequired: response?.vector?.rebuild_required ?? null,
  asOf: response?.as_of ?? null,
});

export const mapMessageDetail = (response) => ({
  item: response?.item ?? null,
  memoryLinks: Array.isArray(response?.memory_links) ? response.memory_links : [],
});

export const mapMemoryVector = (response) => response?.vector ?? null;

export const mapMemorySource = (response) => ({
  canonical: response?.canonical ?? null,
  links: Array.isArray(response?.links) ? response.links : [],
});

export const formatList = (value) => {
  if (!Array.isArray(value) || value.length === 0) return "未知";
  return value.map((item) => {
    if (typeof item === "string" || typeof item === "number") return String(item);
    if (item && typeof item === "object") {
      return String(item.name ?? item.title ?? item.id ?? item.value ?? "未知项");
    }
    return "未知项";
  }).join("、");
};

export const isRestricted = (row) => String(row?.privacy ?? "").toLowerCase() === "restricted";
export const rebuildLabel = (value) => value === true ? "需要重建" : value === false ? "无需重建" : "未知";
export const countLabel = (value) => typeof value === "number" ? value.toLocaleString() : "未知";
