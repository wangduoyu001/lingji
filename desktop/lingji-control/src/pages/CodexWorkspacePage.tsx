import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { ApiError } from "../api";
import type { PageProps } from "../types";
import { ACTIVE_POLL_MS, IDLE_POLL_MS, WORKSPACE_LIMIT, displayPath, progressLabel } from "./codexWorkspaceContract";
import { CodexWorkspaceApi } from "./codexWorkspaceApi";
import type { ActivityEvent, CodexCurrent, CodexProject, CodexSession, ContextPack, WorkspaceFilters } from "./codexWorkspaceTypes";
import "./LocalMemoryLoop.css";

type Props = PageProps & { onOpenInspector: (target: { project_id?: string; source_id?: string; conversation_id?: string; message_id?: string; memory_id?: string }) => void };
const dt = (value?: string | null) => value ? new Date(value).toLocaleString() : "未知";

export default function CodexWorkspacePage({ api, active, onOpenInspector }: Props) {
  const client = useMemo(() => new CodexWorkspaceApi(api), [api]);
  const [current, setCurrent] = useState<CodexCurrent | null>(null);
  const [projects, setProjects] = useState<CodexProject[]>([]);
  const [sessions, setSessions] = useState<CodexSession[]>([]);
  const [selected, setSelected] = useState<CodexSession | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [filters, setFilters] = useState<WorkspaceFilters>({ projectId: "", status: "", q: "", limit: WORKSPACE_LIMIT, offset: 0 });
  const [contextTask, setContextTask] = useState("");
  const [maxChars, setMaxChars] = useState(12000);
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const listAbort = useRef<AbortController | null>(null);
  const listRequestId = useRef(0);
  const activityAbort = useRef<AbortController | null>(null);
  const activityRequestId = useRef(0);
  const lastEventId = useRef(0);

  const load = useCallback(async () => {
    if (!active || document.hidden) return;
    listAbort.current?.abort(); const abort = new AbortController(); const id = ++listRequestId.current; listAbort.current = abort;
    try {
      const [now, projectPage, sessionPage] = await Promise.all([client.current(abort.signal), client.projects(abort.signal), client.sessions(filters, abort.signal)]);
      if (id !== listRequestId.current) return;
      setCurrent(now); setProjects(projectPage.items ?? []); setSessions(sessionPage.items ?? []); setError(null);
    } catch (reason) { if (id === listRequestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason); }
  }, [active, client, filters]);

  const pollActivity = useCallback(async () => {
    if (!active || document.hidden) return;
    activityAbort.current?.abort(); const abort = new AbortController(); const id = ++activityRequestId.current; activityAbort.current = abort;
    try {
      const response = await client.activity(lastEventId.current, abort.signal);
      if (id !== activityRequestId.current) return;
      const incoming = response.items ?? []; if (incoming.length) lastEventId.current = Math.max(...incoming.map((item) => item.event_id));
      setActivity((previous) => [...previous, ...incoming].slice(-100));
    } catch (reason) { if (id === activityRequestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason); }
  }, [active, client]);

  useEffect(() => { void load(); return () => listAbort.current?.abort(); }, [load]);
  useEffect(() => {
    if (!active) return;
    let timer = 0;
    const tick = async () => { await pollActivity(); timer = window.setTimeout(tick, current?.session ? ACTIVE_POLL_MS : IDLE_POLL_MS); };
    void tick();
    const visibility = () => { if (!document.hidden) void pollActivity(); };
    document.addEventListener("visibilitychange", visibility);
    return () => { window.clearTimeout(timer); activityAbort.current?.abort(); document.removeEventListener("visibilitychange", visibility); };
  }, [active, current?.session, pollActivity]);

  const chooseProject = async () => {
    const chosen = await open({ directory: true, multiple: false, title: "选择 Codex 项目目录" });
    if (!chosen || Array.isArray(chosen)) return;
    setBusy("resolve");
    try { const project = await client.resolve({ workspace_path: chosen }); setFilters((f) => ({ ...f, projectId: project.project_id, offset: 0 })); await load(); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const openSession = async (row: CodexSession) => {
    setBusy(`session:${row.session_id}`);
    try { setSelected(await client.session(row.session_id)); } catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const buildContext = async () => {
    const projectId = selected?.project_id || current?.project?.project_id || filters.projectId;
    if (!projectId || !contextTask.trim()) return;
    setBusy("context");
    try { setContextPack(await client.context({ project_id: projectId, query: contextTask.trim(), session_id: selected?.session_id, max_chars: maxChars })); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  if (!active) return <div className="loop-state">连接本机服务后显示项目与对话。</div>;
  return <div className="loop-page">
    <header className="loop-toolbar"><button className="button secondary" onClick={() => void load()}>刷新</button><button className="button" disabled={busy === "resolve"} onClick={() => void chooseProject()}>{busy === "resolve" ? "识别中…" : "选择项目目录"}</button><span>{current?.project ? `当前：${current.project.name ?? current.project.project_id}` : "未绑定项目"}</span></header>
    {error && <div className="loop-state error">{error.status === 401 ? "需要本地授权" : error.status === 503 ? "服务暂不可用" : error.status === 409 ? "项目或会话状态冲突" : "读取失败"}</div>}
    <section className="loop-grid">
      <div className="loop-panel"><h2>项目</h2>{projects.length ? projects.map((p) => <button className="loop-card" key={p.project_id} onClick={() => setFilters((f) => ({ ...f, projectId: p.project_id, offset: 0 }))}><strong>{p.name ?? p.project_id}</strong><span>{p.repository ?? "未知仓库"}</span><span>{p.branch ?? "未知分支"} · {p.worktree_name ?? "未知 Worktree"}</span><small>{displayPath(p.path_display)} · {dt(p.last_seen_at)}</small></button>) : <p>尚未识别项目。</p>}</div>
      <div className="loop-panel"><h2>Session</h2><div className="loop-filters"><select value={filters.projectId} onChange={(e) => setFilters({ ...filters, projectId: e.target.value, offset: 0 })}><option value="">全部项目</option>{projects.map((p) => <option key={p.project_id} value={p.project_id}>{p.name ?? p.project_id}</option>)}</select><select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value, offset: 0 })}><option value="">全部状态</option><option>active</option><option>completed</option><option>failed</option><option>abandoned</option></select><input placeholder="搜索 Session" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value, offset: 0 })} /></div>{sessions.length ? sessions.map((s) => <button className="loop-card" key={s.session_id} onClick={() => void openSession(s)}><strong>{s.title ?? s.session_id}</strong><span>{s.project_name ?? s.project_id ?? "未绑定"} · {s.branch ?? "未知分支"}</span><span>{s.status ?? "未知"} · 检查点 {s.checkpoint_count ?? "未知"}</span><small>{dt(s.started_at)} · {s.summary ?? "无摘要"}</small></button>) : <p>{filters.projectId || filters.status || filters.q ? "筛选后没有 Session。" : "没有 Session。"}</p>}<div className="loop-pager"><button disabled={filters.offset === 0} onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - WORKSPACE_LIMIT) })}>上一页</button><button onClick={() => setFilters({ ...filters, offset: filters.offset + WORKSPACE_LIMIT })}>下一页</button></div></div>
    </section>
    {selected && <section className="loop-panel"><h2>Session 详情</h2><p><strong>{selected.title ?? selected.session_id}</strong></p><p>目标：{selected.goal ?? "未知"}</p><p>完成：{selected.completed?.join("；") || "未知"}</p><p>决策：{selected.decisions?.join("；") || "未知"}</p><p>测试：{selected.tests?.join("；") || "未知"}</p><p>阻塞：{selected.blockers?.join("；") || "无"}</p><p>下一步：{selected.next_steps?.join("；") || "未知"}</p><button className="button secondary" onClick={() => onOpenInspector({ project_id: selected.project_id, source_id: selected.source_ids?.[0], conversation_id: selected.conversation_ids?.[0] })}>查看 Memory Inspector</button></section>}
    <section className="loop-grid"><div className="loop-panel"><h2>实时 Activity</h2>{activity.length ? activity.map((event) => <div className="activity-row" key={event.event_id}><strong>{event.stage ?? "未知阶段"}</strong><span>{event.summary ?? "无摘要"}</span><small>{dt(event.occurred_at)} · {progressLabel(event.progress_current, event.progress_total, event.status)} {event.error_code ? `· ${event.error_code}` : ""}</small>{(event.memory_id || event.message_id || event.conversation_id) && <button onClick={() => onOpenInspector({ project_id: event.project_id, conversation_id: event.conversation_id, message_id: event.message_id, memory_id: event.memory_id })}>跳转</button>}</div>) : <p>当前没有 Activity。</p>}</div><div className="loop-panel"><h2>构建 Codex 项目上下文</h2><textarea value={contextTask} onChange={(e) => setContextTask(e.target.value)} placeholder="当前任务" /><input type="number" min={1000} max={100000} value={maxChars} onChange={(e) => setMaxChars(Number(e.target.value))} /><button className="button" disabled={busy === "context" || !contextTask.trim()} onClick={() => void buildContext()}>{busy === "context" ? "构建中…" : "构建 Context Pack"}</button>{contextPack && <><p>{contextPack.used_chars ?? "未知"} / {contextPack.max_chars ?? maxChars} chars</p><pre>{contextPack.markdown}</pre><button onClick={() => void navigator.clipboard.writeText(contextPack.markdown)}>复制 Context Pack</button></>}</div></section>
  </div>;
}
