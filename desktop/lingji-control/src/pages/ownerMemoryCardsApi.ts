import type { LingJiApi } from "../api";
import type { CanonicalBody, ConversationMessage, DetailLoadState, EvidenceItem, EvidencePage, OwnerMemoryCard, OwnerMemoryCardsResponse, OwnerMemoryDetail } from "./ownerMemoryCardsTypes";

type DetailOptions = { signal?: AbortSignal };
type CanonicalResponse = { as_of?: string | null; item?: { content_hash?: string | null; current_hash?: string | null; chunks?: Array<{ chunk_id?: string | null; text?: string | null; content_hash?: string | null; start_line?: number | null; end_line?: number | null; truncated?: boolean }> } };
type VectorResponse = { as_of?: string | null; vector?: Record<string, unknown> | null };
type SourceResponse = { as_of?: string | null; memory_id?: string; canonical?: Record<string, unknown> | null; links?: Array<Record<string, unknown>> };
type EvidenceResponse = { as_of?: string | null; memory_id?: string; items?: EvidenceItem[]; pagination?: { limit?: number; offset?: number; total?: number | null; has_more?: boolean; next_cursor?: string | null } };
type ConversationMessagesResponse = { items?: ConversationMessage[] };

const loadState = (status: DetailLoadState["status"], error: unknown = null): DetailLoadState => ({ status, error: error instanceof Error ? error.message : error ? String(error) : null });
const unwrapError = (result: PromiseSettledResult<unknown>) => result.status === "rejected" ? result.reason : null;

export class OwnerMemoryCardsApi {
  constructor(private readonly api: LingJiApi) {}
  list(offset = 0, signal?: AbortSignal, limit = 20, state = "current") {
    const boundedLimit = Math.min(Math.max(1, limit), 50);
    const stateQuery = state ? `&state=${encodeURIComponent(state)}` : "";
    return this.api.get<OwnerMemoryCardsResponse>(`/api/memory/inspector/cards?limit=${boundedLimit}&offset=${Math.max(0, offset)}${stateQuery}`, { signal });
  }
  summary(signal?: AbortSignal) {
    return this.api.get<{ cards?: number | null; conversations?: number | null; messages?: number | null; permanent?: number | null; vectorized?: number | null; owner_review?: number | null }>("/api/memory/inspector/cards-summary", { signal });
  }
  detail(id: string, signal?: AbortSignal) {
    return this.api.get<{ as_of?: string | null; item: OwnerMemoryCard }>(`/api/memory/inspector/cards/${encodeURIComponent(id)}`, { signal });
  }
  canonical(id: string, signal?: AbortSignal) {
    return this.api.get<CanonicalResponse>(`/api/memory/inspector/memories/${encodeURIComponent(id)}?chunk_limit=20&max_chars=12000`, { signal });
  }
  getOwnerMemoryVector(id: string, signal?: AbortSignal) {
    return this.api.get<VectorResponse>(`/api/memory/inspector/memories/${encodeURIComponent(id)}/vector`, { signal });
  }
  getOwnerMemorySource(id: string, signal?: AbortSignal) {
    return this.api.get<SourceResponse>(`/api/memory/inspector/memories/${encodeURIComponent(id)}/source`, { signal });
  }
  getOwnerMemoryEvidence(id: string, { limit = 20, offset = 0, signal }: { limit?: number; offset?: number; signal?: AbortSignal } = {}) {
    const boundedLimit = Math.min(Math.max(1, limit), 50);
    const boundedOffset = Math.max(0, offset);
    return this.api.get<EvidenceResponse>(`/api/memory/inspector/memories/${encodeURIComponent(id)}/evidence?limit=${boundedLimit}&offset=${boundedOffset}`, { signal });
  }
  getOwnerMemoryConversationMessages(conversationId: string, signal?: AbortSignal) {
    return this.api.get<ConversationMessagesResponse>(`/api/memory/inspector/messages?conversation_id=${encodeURIComponent(conversationId)}&limit=20&offset=0`, { signal });
  }
  async getOwnerMemoryDetail(memoryId: string, options: DetailOptions = {}): Promise<OwnerMemoryDetail> {
    const selectedResponse = await this.detail(memoryId, options.signal);
    const card = selectedResponse.item;
    const conversationOnly = card.kind === "conversation_evidence" || Boolean(card.source?.conversation_id);
    const resourcePromises = conversationOnly
      ? [this.getOwnerMemorySource(memoryId, options.signal), this.getOwnerMemoryConversationMessages(card.source?.conversation_id ?? "", options.signal)]
      : [this.canonical(memoryId, options.signal), this.getOwnerMemoryVector(memoryId, options.signal), this.getOwnerMemorySource(memoryId, options.signal), this.getOwnerMemoryEvidence(memoryId, { signal: options.signal })];
    const resources = await Promise.allSettled(resourcePromises);
    const asOf = selectedResponse.as_of ?? card.as_of ?? null;
    const canonicalResult = conversationOnly ? null : resources[0];
    const vectorResult = conversationOnly ? null : resources[1];
    const sourceResult = conversationOnly ? resources[0] : resources[2];
    const evidenceResult = conversationOnly ? null : resources[3];
    const canonicalValue = canonicalResult?.status === "fulfilled" ? canonicalResult.value as CanonicalResponse : null;
    const vectorValue = vectorResult?.status === "fulfilled" ? vectorResult.value as VectorResponse : null;
    const sourceValue = sourceResult?.status === "fulfilled" ? sourceResult.value as SourceResponse : null;
    const evidenceValue = evidenceResult?.status === "fulfilled" ? evidenceResult.value as EvidenceResponse : null;
    const conversationMessages = conversationOnly && resources[1]?.status === "fulfilled" ? (resources[1].value as ConversationMessagesResponse).items ?? [] : undefined;
    const pagination = evidenceValue?.pagination ?? {};
    const canonical: CanonicalBody | null = canonicalValue ? {
      asOf: canonicalValue.as_of ?? null,
      contentHash: canonicalValue.item?.content_hash ?? canonicalValue.item?.current_hash ?? null,
      chunks: canonicalValue.item?.chunks ?? [],
      truncated: (canonicalValue.item?.chunks ?? []).some((chunk) => Boolean(chunk.truncated)),
      nextCursor: null,
    } : null;
    const evidence: EvidencePage | null = evidenceValue ? {
      asOf: evidenceValue.as_of ?? null,
      memoryId: evidenceValue.memory_id ?? memoryId,
      items: evidenceValue.items ?? [],
      limit: Number(pagination.limit ?? 20),
      offset: Number(pagination.offset ?? 0),
      total: typeof pagination.total === "number" ? pagination.total : null,
      hasMore: Boolean(pagination.has_more),
      nextCursor: pagination.next_cursor ?? null,
    } : null;
    const errorMessage = (result: PromiseSettledResult<unknown> | null) => result ? unwrapError(result) : null;
    const loads = {
      card: loadState("ready"),
      canonical: conversationOnly ? loadState("unknown", "这是原始会话，尚未形成长期记忆") : canonicalResult?.status === "fulfilled" ? loadState("ready") : loadState("error", errorMessage(canonicalResult)),
      vector: conversationOnly ? loadState("unknown", "这是原始会话，尚未形成长期记忆") : vectorResult?.status === "fulfilled" ? loadState("ready") : loadState("error", errorMessage(vectorResult)),
      source: sourceResult?.status === "fulfilled" ? loadState("ready") : loadState("error", errorMessage(sourceResult)),
      evidence: conversationOnly ? loadState("unknown", "这是原始会话，尚未形成长期记忆") : evidenceResult?.status === "fulfilled" ? loadState("ready") : loadState("error", errorMessage(evidenceResult)),
    };
    return { memoryId, asOf: (canonical?.asOf ?? evidence?.asOf ?? asOf), contentHash: canonical?.contentHash ?? card.content_hash ?? card.current_hash ?? null, card, canonical, vector: vectorValue?.vector ?? null, source: sourceValue ? { canonical: sourceValue.canonical, links: sourceValue.links ?? [] } : null, evidence, conversationMessages, loads };
  }
  message(id: string, signal?: AbortSignal) {
    return this.api.get<{ item: { content?: string | null; preview?: string | null; [key: string]: unknown } }>(`/api/memory/inspector/messages/${encodeURIComponent(id)}`, { signal });
  }
  approve(id: string, hash: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/review/candidates/${encodeURIComponent(id)}/approve`, { owner_confirmed: true, expected_content_hash: hash }, { signal });
  }
  editApprove(id: string, hash: string, content: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/review/candidates/${encodeURIComponent(id)}/edit-approve`, { owner_confirmed: true, expected_content_hash: hash, content }, { signal });
  }
  reject(id: string, hash: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/review/candidates/${encodeURIComponent(id)}/reject`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal });
  }
  correct(id: string, hash: string, content: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/core/${encodeURIComponent(id)}/correct`, { owner_confirmed: true, expected_content_hash: hash, content, reason }, { signal });
  }
  invalidate(id: string, hash: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/core/${encodeURIComponent(id)}/invalidate`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal });
  }
  archive(id: string, hash: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/core/${encodeURIComponent(id)}/archive`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal });
  }
}
