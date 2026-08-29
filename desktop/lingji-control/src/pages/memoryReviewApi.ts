import type { LingJiApi } from "../api";
import type { CoreIntegrity, CoreMemoryDraft, MemoryCandidate, ObsidianNote, ObsidianScan, ReviewFilters } from "./memoryReviewTypes";
import type { PageResponse } from "./codexWorkspaceTypes";
import { REVIEW_LIMIT, reviewQuery } from "./codexWorkspaceContract";

type ReviewPageResponse = {
  items: MemoryCandidate[];
  pagination?: { limit?: number; offset?: number; total?: number | null; has_more?: boolean } | null;
  limit?: number;
  offset?: number;
  total?: number | null;
};

export function normalizeReviewPage(response: ReviewPageResponse): PageResponse<MemoryCandidate> {
  const items = Array.isArray(response.items) ? response.items : [];
  const source = response.pagination ?? {};
  const limit = source.limit ?? response.limit ?? REVIEW_LIMIT;
  const offset = source.offset ?? response.offset ?? 0;
  const total = source.total ?? response.total ?? null;
  const hasMore = typeof source.has_more === "boolean"
    ? source.has_more
    : typeof total === "number" && offset + items.length < total;
  return { items, pagination: { limit, offset, total, has_more: hasMore } };
}

export class MemoryReviewApi {
  constructor(private readonly api: LingJiApi) {}
  async candidates(filters: ReviewFilters, signal?: AbortSignal) {
    const response = await this.api.get<ReviewPageResponse>(`/api/memory/review/candidates?${reviewQuery(filters)}`, { signal });
    return normalizeReviewPage(response);
  }
  candidate(id: string, signal?: AbortSignal) { return this.api.get<MemoryCandidate>(`/api/memory/review/candidates/${encodeURIComponent(id)}`, { signal }); }
  approve(id: string, hash: string, signal?: AbortSignal) { return this.api.post<MemoryCandidate>(`/api/memory/review/candidates/${encodeURIComponent(id)}/approve`, { owner_confirmed: true, expected_content_hash: hash }, { signal }); }
  editApprove(id: string, hash: string, content: string, signal?: AbortSignal) { return this.api.post<MemoryCandidate>(`/api/memory/review/candidates/${encodeURIComponent(id)}/edit-approve`, { owner_confirmed: true, expected_content_hash: hash, content }, { signal }); }
  reject(id: string, hash: string, reason: string, signal?: AbortSignal) { return this.api.post<{ status: string }>(`/api/memory/review/candidates/${encodeURIComponent(id)}/reject`, { owner_confirmed: true, expected_content_hash: hash, reason }, { signal }); }
  createCore(body: CoreMemoryDraft, signal?: AbortSignal) { return this.api.post<{ id?: string; memory_id?: string }>("/api/memory/core", { ...body, owner_confirmed: true }, { signal }); }
  archive(id: string, reason = "Owner archived from LingJi UI", signal?: AbortSignal) { return this.api.post<{ status: string }>(`/api/memory/core/${encodeURIComponent(id)}/archive`, { owner_confirmed: true, reason }, { signal }); }
  integrity(id: string, signal?: AbortSignal) { return this.api.get<CoreIntegrity>(`/api/memory/core/${encodeURIComponent(id)}/integrity`, { signal }); }
  readNote(path: string, signal?: AbortSignal) { return this.api.get<ObsidianNote>(`/api/obsidian/notes?relative_path=${encodeURIComponent(path)}`, { signal }); }
  createNote(body: Record<string, unknown>, signal?: AbortSignal) { return this.api.post<ObsidianNote>("/api/obsidian/notes", body, { signal }); }
  scan(signal?: AbortSignal) { return this.api.post<ObsidianScan>("/api/obsidian/scan", {}, { signal }); }
}
