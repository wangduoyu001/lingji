import type { LingJiApi } from "../api";
import type { CoreIntegrity, CoreMemoryDraft, MemoryCandidate, ObsidianNote, ObsidianScan, ReviewFilters } from "./memoryReviewTypes";
import type { PageResponse } from "./codexWorkspaceTypes";
import { reviewQuery } from "./codexWorkspaceContract";

export class MemoryReviewApi {
  constructor(private readonly api: LingJiApi) {}
  candidates(filters: ReviewFilters, signal?: AbortSignal) { return this.api.get<PageResponse<MemoryCandidate>>(`/api/memory/review/candidates?${reviewQuery(filters)}`, { signal }); }
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
