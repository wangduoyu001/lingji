import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { ApiError } from "../api";
import { Empty } from "../components/ui";
import type { PageProps } from "../types";
import { ACTIVE_POLL_MS, IDLE_POLL_MS, WORKSPACE_LIMIT, displayPath, progressLabel } from "./codexWorkspaceContract";
import { CodexWorkspaceApi } from "./codexWorkspaceApi";
import type { ActivityEvent, CodexCurrent, CodexProject, CodexSession, ContextPack, WorkspaceFilters } from "./codexWorkspaceTypes";
import "./LocalMemoryLoop.css";
import "../AssistantAutopilot.css";

type Props = PageProps & { onOpenInspector: (target: { project_id?: string; source_id?: string; conversation_id?: string; message_id?: string; memory_id?: string }) => void };
const dt = (value?: string | null) => value ? new Date(value).toLocaleString() : "未知";
const stateClass = (value?: string | null) => value === "active" ? "ok" : value === "failed" || value === "abandoned" ? "error" : value === "completed" ? "success" : "neutral";
const stateLabel = (value?: string | null) => ({
  active: "进行中",
  completed: "已完成",
  failed: "失败",
  abandoned: "已结束",
}[String(value ?? "")] ?? (value || "未知"));

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
    listAbort.current?.abort();
    const abort = new AbortController();
    const id = ++listRequestId.current;
    listAbort.current = abort;
    try {
      const [now, projectPage, sessionPage] = await Promise.all([
        client.current(abort.signal),
        client.projects(abort.signal),
        client.sessions(filters, abort.signal),
      ]);
      if (id !== listRequestId.current) return;
      setCurrent(now);
      setProjects(projectPage.items ?? []);
      setSessions(sessionPage.items ?? []);
      setError(null);
    } catch (reason) {
      if (id === listRequestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason);
    }
  }, [active, client, filters]);

  const pollActivity = useCallback(async () => {
    if (!active || document.hidden) return;
    activityAbort.current?.abort();
    const abort = new AbortController();
    const id = ++activityRequestId.current;
    activityAbort.current = abort;
    try {
      const response = await client.activity(lastEventId.current, abort.signal);
      if (id !== activityRequestId.current) return;
      const incoming = response.items ?? [];
      if (incoming.length) lastEventId.current = Math.max(...incoming.map((item) => item.event_id));
      setActivity((previous) => [...previous, ...incoming].slice(-100));
    } catch (reason) {
      if (id === activityRequestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason);
    }
  }, [active, client]);

  useEffect(() => { void load(); return () => listAbort.current?.abort(); }, [load]);
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      if (!document.hidden) void load();
    }, 15_000);
    return () => window.clearInterval(timer);
  }, [active, load]);

  useEffect(() => {
    if (!active) return;
    let timer = 0;
    const tick = async () => {
      await pollActivity();
      timer = window.setTimeout(tick, current?.session ? ACTIVE_POLL_MS : IDLE_POLL_MS);
    };
    void tick();
    const visibility = () => {
      if (!document.hidden) {
        void pollActivity();
        void load();
      }
    };
    document.addEventListener("visibilitychange", visibility);
    return () => {
      window.clearTimeout(timer);
      activityAbort.current?.abort();
      document.removeEventListener("visibilitychange", visibility);
    };
  }, [active, current?.session, load, pollActivity]);

  const chooseProject = async () => {
    const chosen = await open({ directory: true, multiple: false, title: "选择 Codex 项目目录" });
    if (!chosen || Array.isArray(chosen)) return;
    setBusy("resolve");
    try {
      const project = await client.resolve({ workspace_path: chosen });
      setFilters((value) => ({ ...value, projectId: project.project_id, offset: 0 }));
      await load();
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const openSession = async (row: CodexSession) => {
    setBusy(`session:${row.session_id}`);
    try {
      setSelected(await client.session(row.session_id));
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const buildContext = async () => {
    const projectId = selected?.project_id || current?.project?.project_id || filters.projectId;
    if (!projectId || !contextTask.trim()) return;
    setBusy("context");
    try {
      setContextPack(await client.context({
        project_id: projectId,
        query: contextTask.trim(),
        session_id: selected?.session_id,
        max_chars: maxChars,
      }));
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  if (!active) return <div className="loop-state">连接本机服务后会自动识别 Codex 项目和工作记录。</div>;

  const activeProject = current?.project;

  return <div className="loop-page codex-workspace-page">
    <section className="workspace-hero codex-workspace-hero">
      <div>
        <span className="desktop-eyebrow">CODEX 工作上下文</span>
        <h2>{activeProject?.name ?? activeProject?.project_id ?? "正在识别本机 Codex 项目"}</h2>
        <p>
          {activeProject
            ? `${activeProject.repository ?? "未知仓库"} · ${activeProject.branch ?? "未知分支"} · ${displayPath(activeProject.path_display)}`
            : "灵机会自动关联已经出现过的项目和工作记录；手动选择项目只作为识别失败时的兜底。"}
        </p>
      </div>
      <div className="workspace-hero-actions">
        <div className="workspace-counter"><strong>{sessions.length}</strong><span>已识别工作记录</span></div>
        <button className="button secondary" disabled={busy === "resolve"} onClick={() => void chooseProject()}>
          {busy === "resolve" ? "识别中…" : "识别不到时选择项目"}
        </button>
      </div>
    </section>

    {error && <div className="loop-state error">
      {error.status === 401 ? "需要本地授权" : error.status === 503 ? "服务暂不可用，灵机会继续重试" : error.status === 409 ? "项目或工作记录状态冲突" : "读取失败"}
    </div>}

    <section className="workspace-browser-grid">
      <aside className="loop-panel project-rail-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">PROJECTS</span><h2>已识别项目</h2></div><span className="pill neutral">{projects.length}</span></header>
        <div className="project-rail-list">
          {projects.length ? projects.map((project) => (
            <button
              className={`project-rail-card ${filters.projectId === project.project_id ? "active" : ""}`}
              key={project.project_id}
              onClick={() => setFilters((value) => ({ ...value, projectId: project.project_id, offset: 0 }))}
            >
              <strong>{project.name ?? project.project_id}</strong>
              <span>{project.repository ?? "未知仓库"}</span>
              <small>{project.branch ?? "未知分支"} · {project.worktree_name ?? "默认工作目录"}</small>
              <small>{dt(project.last_seen_at)}</small>
            </button>
          )) : <Empty text="暂未识别项目，灵机会继续扫描。" />}
        </div>
      </aside>

      <section className="loop-panel session-browser-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">CODEX RECORDS</span><h2>Codex 工作记录</h2></div><span className="pill neutral">{sessions.length}</span></header>
        <p className="codex-session-explainer">
          这里的数字表示灵机已经识别到的 Codex Session 工作记录，不是灵机新建了聊天窗口。
          灵机会用这些记录恢复项目上下文、整理进度和生成记忆候选。
        </p>
        <div className="workspace-filter-bar">
          <label>项目<select value={filters.projectId} onChange={(event) => setFilters({ ...filters, projectId: event.target.value, offset: 0 })}><option value="">全部项目</option>{projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.name ?? project.project_id}</option>)}</select></label>
          <label>状态<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value, offset: 0 })}><option value="">全部状态</option><option value="active">进行中</option><option value="completed">已完成</option><option value="failed">失败</option><option value="abandoned">已结束</option></select></label>
          <label className="workspace-search-field">搜索<input placeholder="标题、摘要或工作记录 ID" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value, offset: 0 })} /></label>
        </div>
        <div className="session-card-list">
          {sessions.length ? sessions.map((session) => (
            <button className={`session-card ${selected?.session_id === session.session_id ? "active" : ""}`} key={session.session_id} onClick={() => void openSession(session)}>
              <div className="session-card-heading"><strong>{session.title ?? "未命名 Codex 工作记录"}</strong><span className={`pill ${stateClass(session.status)}`}>{stateLabel(session.status)}</span></div>
              <p>{session.summary ?? "尚未生成摘要"}</p>
              <div className="session-card-meta"><span>{session.project_name ?? session.project_id ?? "未绑定项目"}</span><span>{session.branch ?? "未知分支"}</span><span>检查点 {session.checkpoint_count ?? "未知"}</span></div>
              <small>{dt(session.started_at)}</small>
            </button>
          )) : <Empty text={filters.projectId || filters.status || filters.q ? "筛选后没有匹配的工作记录。" : "暂未识别 Codex 工作记录，灵机会继续扫描。"} />}
        </div>
        <div className="loop-pager"><button disabled={filters.offset === 0} onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - WORKSPACE_LIMIT) })}>上一页</button><span>第 {Math.floor(filters.offset / WORKSPACE_LIMIT) + 1} 页</span><button onClick={() => setFilters({ ...filters, offset: filters.offset + WORKSPACE_LIMIT })}>下一页</button></div>
      </section>

      <aside className="loop-panel session-detail-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">WORK RECORD</span><h2>工作记录详情</h2></div></header>
        {selected ? <div className="session-detail-content">
          <div className="session-detail-title"><div><strong>{selected.title ?? "未命名 Codex 工作记录"}</strong><small>{selected.session_id}</small></div><span className={`pill ${stateClass(selected.status)}`}>{stateLabel(selected.status)}</span></div>
          <SessionFact title="目标" values={selected.goal ? [selected.goal] : []} empty="未知" />
          <SessionFact title="已完成" values={selected.completed} />
          <SessionFact title="关键决策" values={selected.decisions} />
          <SessionFact title="测试" values={selected.tests} />
          <SessionFact title="阻塞" values={selected.blockers} empty="无" tone="warning" />
          <SessionFact title="下一步" values={selected.next_steps} />
          <button className="button secondary" onClick={() => onOpenInspector({ project_id: selected.project_id, source_id: selected.source_ids?.[0], conversation_id: selected.conversation_ids?.[0] })}>查看这条记录如何进入记忆</button>
        </div> : <div className="workspace-empty-detail"><span className="desktop-eyebrow">WORK RECORD</span><h2>选择一条工作记录</h2><p>这里会整理目标、完成项、决策、测试、阻塞和下一步，而不是把整段原始对话直接倒出来。</p></div>}
      </aside>
    </section>

    <section className="loop-grid workspace-activity-grid">
      <div className="loop-panel activity-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">LIVE ACTIVITY</span><h2>实时处理记录</h2></div><span className="pill neutral">{activity.length}</span></header>
        <div className="activity-timeline">
          {activity.length ? activity.slice().reverse().map((event) => (
            <div className="activity-row" key={event.event_id}>
              <span className={`activity-dot ${event.status === "failed" ? "failed" : event.status === "completed" ? "done" : ""}`} />
              <div>
                <div className="activity-row-heading"><strong>{event.stage ?? "未知阶段"}</strong><small>{dt(event.occurred_at)}</small></div>
                <p>{event.summary ?? "无摘要"}</p>
                <small>{progressLabel(event.progress_current, event.progress_total, event.status)} {event.error_code ? `· ${event.error_code}` : ""}</small>
                {(event.memory_id || event.message_id || event.conversation_id) && <button className="text-button" onClick={() => onOpenInspector({ project_id: event.project_id, conversation_id: event.conversation_id, message_id: event.message_id, memory_id: event.memory_id })}>查看来源</button>}
              </div>
            </div>
          )) : <Empty text="当前没有新的处理活动。" />}
        </div>
      </div>

      <div className="loop-panel context-builder-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">CONTEXT BUILDER</span><h2>构建 Codex 项目上下文</h2></div></header>
        <p className="panel-description">按当前项目和可选工作记录生成受字符预算约束的 Context Pack，不读取完整原始对话。</p>
        <label>当前任务<textarea value={contextTask} onChange={(event) => setContextTask(event.target.value)} placeholder="描述 Codex 接下来要完成的具体任务" /></label>
        <label>字符预算<input type="number" min={1000} max={100000} value={maxChars} onChange={(event) => setMaxChars(Number(event.target.value))} /></label>
        <button className="button primary" disabled={busy === "context" || !contextTask.trim()} onClick={() => void buildContext()}>{busy === "context" ? "构建中…" : "构建 Context Pack"}</button>
        {contextPack && <div className="context-pack-result">
          <div className="context-pack-header"><div><strong>Context Pack</strong><small>{contextPack.used_chars ?? "未知"} / {contextPack.max_chars ?? maxChars} chars</small></div><button className="button secondary" onClick={() => void navigator.clipboard.writeText(contextPack.markdown)}>复制 Context Pack</button></div>
          <pre>{contextPack.markdown}</pre>
        </div>}
      </div>
    </section>
  </div>;
}

function SessionFact({ title, values, empty = "未知", tone = "" }: { title: string; values?: string[] | null; empty?: string; tone?: string }) {
  return <section className={`session-fact ${tone}`}><span>{title}</span>{values?.length ? <ul>{values.map((value, index) => <li key={`${title}-${index}`}>{value}</li>)}</ul> : <p>{empty}</p>}</section>;
}
