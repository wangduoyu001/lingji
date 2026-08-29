import type { LingJiApi } from "../api";
import type { OwnerMemoryCard, OwnerMemoryCardsResponse } from "./ownerMemoryCardsTypes";

export class OwnerMemoryCardsApi {
  constructor(private readonly api: LingJiApi) {}
  list(offset = 0, signal?: AbortSignal, limit = 20) {
    const boundedLimit = Math.min(Math.max(1, limit), 50);
    return this.api.get<OwnerMemoryCardsResponse>(`/api/memory/inspector/cards?limit=${boundedLimit}&offset=${Math.max(0, offset)}`, { signal });
  }
  detail(id: string, signal?: AbortSignal) {
    return this.api.get<{ item: OwnerMemoryCard }>(`/api/memory/inspector/cards/${encodeURIComponent(id)}?expand=true`, { signal });
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
