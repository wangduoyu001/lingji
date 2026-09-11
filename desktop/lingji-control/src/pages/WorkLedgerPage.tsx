import { useCallback, useState } from "react";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";

export type ObsTask = {
  scan_id: string;
  status: string;
  progress?: number | null;
  total?: number | null;
  queued_count?: number | null;
  reused_count?: number | null;
  updated_at?: string | null;
  job_completed?: number | null;
  job_failed?: number | null;
  job_queued?: number | null;
};

export type ObsStep = { step: string; label: string; plain: string; count: number | null; total: number | null; percent: number | null };
export type ObsItem = { name: string; status: string; label: string; updated_at?: string | null; failure?: { what: string; next: string } };
export type ObsChange = { time?: string | null; action: string; object: string; reason?: string | null };

const TASK_STATUS: Record<string, { label: string; tone: string }> = {
  running: { label: "进行中", tone: "warning" },
  completed: { label: "已完成", tone: "ok" },
  failed: { label: "未完成", tone: "bad" },
  cancelled: { label: "已取消", tone: "neutral" },
  paused: { label: "已暂停", tone: "neutral" },
};

export function taskStatusLabel(status: string | null | undefined): string {
  return TASK_STATUS[String(status ?? "")]?.label ?? "尚未获得";
}

export function timeText(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

export function useObservabilityTasks(api: LingJiApi, active: boolean) {
  return usePollingResource<{ items: ObsTask[]; pagination: { total: number; has_more: boolean } }>({
    fetcher: useCallback((signal: AbortSignal) => api.get("/api/observability/tasks?limit=50&offset=0", { signal }), [api]),
    enabled: active,
    intervalMs: 10_000,
    staleAfterMs: 30_000,
  });
}

export function useTaskSteps(api: LingJiApi, scanId: string | null, active: boolean) {
  return usePollingResource<{ steps: ObsStep[] }>({
    fetcher: useCallback((signal: AbortSignal) => api.get(`/api/observability/tasks/${encodeURIComponent(String(scanId))}/steps`, { signal }), [api, scanId]),
    enabled: active && Boolean(scanId),
    intervalMs: 8_000,
    staleAfterMs: 30_000,
  });
}

export function useTaskItems(api: LingJiApi, scanId: string | null, active: boolean) {
  return usePollingResource<{ items: ObsItem[]; pagination: { total: number; has_more: boolean } }>({
    fetcher: useCallback((signal: AbortSignal) => api.get(`/api/observability/tasks/${encodeURIComponent(String(scanId))}/items?limit=50&offset=0`, { signal }), [api, scanId]),
    enabled: active && Boolean(scanId),
    intervalMs: 10_000,
    staleAfterMs: 30_000,
  });
}

export function useChanges(api: LingJiApi, active: boolean) {
  return usePollingResource<{ items: ObsChange[] }>({
    fetcher: useCallback((signal: AbortSignal) => api.get("/api/observability/changes?limit=80&offset=0", { signal }), [api]),
    enabled: active,
    intervalMs: 15_000,
    staleAfterMs: 45_000,
  });
}

export function useInfoFeed(api: LingJiApi, active: boolean) {
  return usePollingResource<{ items: ObsItem[]; pagination: { has_more: boolean } }>({
    fetcher: useCallback((signal: AbortSignal) => api.get("/api/observability/feed?limit=80&offset=0", { signal }), [api]),
    enabled: active,
    intervalMs: 15_000,
    staleAfterMs: 45_000,
  });
}

export function StepsFlow({ steps }: { steps: ObsStep[] | null }) {
  if (!steps || steps.length === 0) return <p className="outcome-empty">这一步的工作明细尚未获得，灵机会自动重试。</p>;
  return (
    <div className="steps-flow">
      {steps.map((step, index) => (
        <div key={step.step} className="step-row" title={step.plain}>
          <span className="step-index">{index + 1}</span>
          <div className="step-main">
            <strong>{step.label}</strong>
            <small>{step.plain}</small>
          </div>
          <div className="step-count">
            <strong>{step.count == null ? "尚未获得" : `${step.count}${step.total ? ` / ${step.total}` : ""}`}</strong>
            {step.percent != null && <div className="step-bar"><div className="step-bar-fill" style={{ width: `${step.percent}%` }} /></div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function WorkLedgerPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const tasks = useObservabilityTasks(api, active);
  const [selected, setSelected] = useState<string | null>(null);
  const currentId = selected ?? tasks.data?.items?.[0]?.scan_id ?? null;
  const steps = useTaskSteps(api, currentId, active);
  const items = useTaskItems(api, currentId, active);

  return (
    <div className="stack work-ledger-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">检查记录</span>
          <h2>检查记录</h2>
          <p>灵机做过的每一次检查都在这里：做了什么、每一步处理了多少、结果如何。</p>
        </div>
        <span className="auto-refresh-note">{tasks.refreshing ? "正在更新" : "自动更新"}</span>
      </section>
      {tasks.error && !tasks.data && <Notice kind="warning">暂时无法读取工作记录，灵机会自动重试。</Notice>}
      {tasks.loading && !tasks.data ? (
        <div className="empty-state" aria-busy="true">正在读取工作记录…</div>
      ) : (tasks.data?.items?.length ?? 0) === 0 ? (
        <Empty text="还没有工作记录。灵机完成第一次自动检查后会出现在这里。" />
      ) : (
        <div className="work-ledger-layout">
          <div className="work-task-list">
            {tasks.data?.items.map((task) => (
              <button key={task.scan_id} className={`work-task-row${currentId === task.scan_id ? " active" : ""}`} onClick={() => setSelected(task.scan_id)}>
                <div>
                  <strong>自动检查 · {taskStatusLabel(task.status)}</strong>
                  <small>{timeText(task.updated_at)}</small>
                </div>
                <div className="work-task-counts">
                  <span>检查 {task.total == null ? "尚未获得" : task.total} 个文件</span>
                  <span>新内容 {task.queued_count == null ? "尚未获得" : task.queued_count} · 复用 {task.reused_count == null ? "尚未获得" : task.reused_count}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="work-task-detail">
            <h3>这次检查的流水线</h3>
            <StepsFlow steps={steps.data?.steps ?? null} />
            <h3>处理的每一条</h3>
            {(items.data?.items?.length ?? 0) === 0 ? (
              <p className="outcome-empty">这条检查的逐条明细尚未获得。</p>
            ) : (
              <div className="work-item-list">
                {items.data?.items.map((item) => (
                  <div key={item.name} className="work-item-row">
                    <div className="work-item-head">
                      <span className={`pill ${item.status === "failed" ? "bad" : item.status === "merged" ? "neutral" : item.status === "kept" ? "ok" : "warning"}`}>{item.label}</span>
                      <strong>{item.name}</strong>
                    </div>
                    {item.failure ? (
                      <div className="work-item-detail">
                        <p>原因：{item.failure.what}</p>
                        <p>接下来：{item.failure.next}</p>
                      </div>
                    ) : (
                      <div className="work-item-detail"><p>更新时间：{timeText(item.updated_at)}</p></div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function ChangesLedgerPage({ api, active, timelineMode }: { api: LingJiApi; active: boolean; timelineMode?: boolean }) {
  const changes = useChanges(api, active);
  return (
    <div className="stack changes-ledger-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">{timelineMode ? "时间线" : "变更账本"}</span>
          <h2>{timelineMode ? "时间线" : "变更账本"}</h2>
          <p>{timelineMode ? "按时间看记忆的变化：自动检查、内容入库、更新。" : "第二大脑的每一笔变化都记在这里：什么时候、对什么、做了什么。"}</p>
        </div>
        <span className="auto-refresh-note">{changes.refreshing ? "正在更新" : "自动更新"}</span>
      </section>
      {timelineMode && <KnowledgeTimelinePanel api={api} active={active} />}
      {changes.loading && !changes.data ? (
        <div className="empty-state" aria-busy="true">正在读取变更账本…</div>
      ) : (changes.data?.items?.length ?? 0) === 0 ? (
        <Empty text="还没有账目。灵机完成工作后会自动记账。" />
      ) : (
        <div className="changes-list">
          {changes.data?.items.map((change, index) => (
            <div key={`${change.time}-${index}`} className="change-row">
              <small className="change-time">{timeText(change.time)}</small>
              <span className="pill neutral">{change.action}</span>
              <small>对象：{change.object}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type KnowledgeTimelineEntry = {
  conversation_id: string;
  title: string;
  summary: string;
  key_points: string[];
  category: string;
  revision: number;
  occurred_at?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
};

function KnowledgeTimelinePanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const knowledge = usePollingResource<{ items: KnowledgeTimelineEntry[]; stats: { ready: number; total: number; pending: number } }>({
    fetcher: useCallback((signal: AbortSignal) => api.get("/api/observability/knowledge?limit=15&order=updated", { signal }), [api]),
    enabled: active,
    intervalMs: 15_000,
    staleAfterMs: 45_000,
  });
  const entries = knowledge.data?.items ?? [];
  return (
    <section className="outcome-section">
      <div className="section-heading">
        <div><span className="section-kicker">记忆提炼动态</span><h3>灵机最近提炼（或更新）了哪些知识要点</h3></div>
        <span className="section-caption">
          {knowledge.data?.stats
            ? `已提炼 ${knowledge.data.stats.ready} / ${knowledge.data.stats.total}${knowledge.data.stats.pending > 0 ? ` · 待提炼 ${knowledge.data.stats.pending}` : ""}`
            : "自动更新"}
        </span>
      </div>
      {entries.length === 0 ? (
        <p className="outcome-empty">还没有提炼记录。本机模型正在自动推进，完成后会出现在这里。</p>
      ) : (
        <div className="knowledge-list">
          {entries.map((entry) => (
            <article key={entry.conversation_id} className="knowledge-item">
              <div className="knowledge-item-head">
                <span className="pill neutral">{entry.category}</span>
                <span className={`pill ${entry.revision > 1 ? "warning" : "ok"}`}>{entry.revision > 1 ? `更新 · 第 ${entry.revision} 版` : "新提炼"}</span>
                <small>{timeText(entry.updated_at ?? entry.created_at)}</small>
              </div>
              <strong>{entry.title}</strong>
              <p>{entry.summary}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
