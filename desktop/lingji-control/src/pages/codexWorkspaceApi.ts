import type { LingJiApi } from "../api";
import type { ActivityEvent, CodexCurrent, CodexProject, CodexSession, ContextPack, PageResponse, WorkspaceFilters } from "./codexWorkspaceTypes";
import { workspaceQuery } from "./codexWorkspaceContract";

export class CodexWorkspaceApi {
  constructor(private readonly api: LingJiApi) {}
  current(signal?: AbortSignal) { return this.api.get<CodexCurrent>("/api/codex/current", { signal }); }
  projects(signal?: AbortSignal) { return this.api.get<PageResponse<CodexProject> | { items: CodexProject[] }>("/api/codex/projects", { signal }); }
  resolve(body: { path: string }, signal?: AbortSignal) { return this.api.post<CodexProject>("/api/codex/projects/resolve", { ...body }, { signal }); }
  sessions(filters: WorkspaceFilters, signal?: AbortSignal) { return this.api.get<PageResponse<CodexSession>>(`/api/codex/sessions?${workspaceQuery(filters)}`, { signal }); }
  session(id: string, signal?: AbortSignal) { return this.api.get<CodexSession>(`/api/codex/sessions/${encodeURIComponent(id)}`, { signal }); }
  activity(afterId: number, signal?: AbortSignal) { return this.api.get<{ items: ActivityEvent[] }>(`/api/activity?after_id=${afterId}`, { signal }); }
  context(body: { project_id: string; task: string; max_chars: number }, signal?: AbortSignal) { return this.api.post<ContextPack>("/api/context/project", { ...body }, { signal }); }
}
