import type { LingJiApi } from "../api";
import type { CanonicalBody, ConversationMessage, DetailLoadState, EvidenceItem, EvidencePage, OwnerMemoryCard, OwnerMemoryCardsResponse, OwnerMemoryDetail } from "./ownerMemoryCardsTypes";

type DetailOptions = { signal?: AbortSignal };
type CanonicalResponse = { as_of?: string | null; item?: { content_hash?: string | null; current_hash?: string | null; next_cursor?: string | null; chunks?: Array<{ chunk_id?: string | null; text?: string | null; content_hash?: string | null; start_line?: number | null; end_line?: number | null; truncated?: boolean }> } };
type VectorResponse = { as_of?: string | null; vector?: Record<string, unknown> | null };
type SourceResponse = { as_of?: string | null; memory_id?: string; canonical?: Record<string, unknown> | null; links?: Array<Record<string, unknown>> };
type EvidenceResponse = { as_of?: string | null; memory_id?: string; items?: EvidenceItem[]; pagination?: { limit?: number; offset?: number; total?: number | null; has_more?: boolean; next_cursor?: string | null } };
type ConversationMessagesResponse = { items?: ConversationMessage[] };

const loadState = (status: DetailLoadState["status"], error: unknown = null): DetailLoadState => ({ status, error: error instanceof Error ? error.message : error ? String(error) : null });

export class OwnerMemoryCardsApi {
  private mutationSignal?: AbortSignal;
  constructor(private readonly api: LingJiApi) {}
  setMutationSignal(signal: AbortSignal) { this.mutationSignal = signal; }
  clearMutationSignal(signal: AbortSignal) { if (this.mutationSignal === signal) this.mutationSignal = undefined; }
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
  canonical(id: string, signal?: AbortSignal, cursor?: string | null) {
    const cursorQuery = cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
    return this.api.get<CanonicalResponse>(`/api/memory/inspector/memories/${encodeURIComponent(id)}?chunk_limit=20&max_chars=12000${cursorQuery}`, { signal });
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
    const conversationOnly = card.kind === "conversation_evidence";
    // The page composes these resources independently. This method intentionally
    // returns a card-first skeleton so one pending resource cannot hold back the
    // owner's readable content from the other resources.
    const asOf = selectedResponse.as_of ?? card.as_of ?? null;
    const loads = {
      card: loadState("ready"),
      canonical: conversationOnly ? loadState("unknown", "这是原始会话，尚未形成长期记忆") : loadState("loading"),
      vector: conversationOnly ? loadState("unknown", "这是原始会话，尚未形成长期记忆") : loadState("loading"),
      source: loadState("loading"),
      evidence: conversationOnly ? loadState("unknown", "这是原始会话，尚未形成长期记忆") : loadState("loading"),
    };
    return { memoryId, asOf, contentHash: card.content_hash ?? card.current_hash ?? null, card, canonical: null, vector: null, source: null, evidence: null, loads };
  }
  message(id: string, signal?: AbortSignal) {
    return this.api.get<{ item: { content?: string | null; preview?: string | null; [key: string]: unknown } }>(`/api/memory/inspector/messages/${encodeURIComponent(id)}`, { signal });
  }
  approve(id: string, hash: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/review/candidates/${encodeURIComponent(id)}/approve`, { owner_confirmed: true, expected_content_hash: hash }, { signal: signal ?? this.mutationSignal });
  }
  editApprove(id: string, hash: string, content: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/review/candidates/${encodeURIComponent(id)}/edit-approve`, { owner_confirmed: true, expected_content_hash: hash, content }, { signal: signal ?? this.mutationSignal });
  }
  reject(id: string, hash: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/review/candidates/${encodeURIComponent(id)}/reject`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal: signal ?? this.mutationSignal });
  }
  correct(id: string, hash: string, content: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/core/${encodeURIComponent(id)}/correct`, { owner_confirmed: true, expected_content_hash: hash, content, reason }, { signal: signal ?? this.mutationSignal });
  }
  invalidate(id: string, hash: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/core/${encodeURIComponent(id)}/invalidate`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal: signal ?? this.mutationSignal });
  }
  archive(id: string, hash: string, reason: string, signal?: AbortSignal) {
    return this.api.post(`/api/memory/core/${encodeURIComponent(id)}/archive`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal: signal ?? this.mutationSignal });
  }
}
