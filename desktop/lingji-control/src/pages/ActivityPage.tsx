import { useCallback, useMemo } from "react";
import { Empty, Notice, Panel } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { Row } from "../types";
import type { CodexCurrent } from "./codexWorkspaceTypes";

const ACTIVE_STATES = new Set(["queued", "running", "retrying"]);

const statusLabel = (value: unknown): string => {
  const state = String(value ?? "unknown").toLowerCase();
  const labels: Record<string, string> = {
    queued: "等待处理",
    running: "正在处理",
    retrying: "自动重试",
    completed: "已完成",
    failed: "处理失败",
    cancelled: "已取消",
  };
  return labels[state] ?? state;
};

const statusTone = (value: unknown): string => {
  const state = String(value ?? "").toLowerCase();
  if (state === "completed") return "success";
  if (state === "failed") return "error";
  if (state === "running" || state === "retrying") return "warning";
  return "neutral";
};

const dateTime = (value: unknown): string => {
  if (!value) return "时间未知";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};

type ActivitySnapshot = {
  current: CodexCurrent;
  jobs: Row;
};

export default function ActivityPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback(async (signal: AbortSignal): Promise<ActivitySnapshot> => {
    const [current, jobs] = await Promise.all([
      api.get<CodexCurrent>("/api/codex/current", { signal }),
      api.get<Row>("/api/jobs?limit=80", { signal }),
    ]);
    return { current, jobs };
  }, [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 4_000,
    staleAfterMs: 15_000,
    pauseWhenHidden: true,
  });

  const jobs = useMemo(
    () => ((resource.data?.jobs as { jobs?: Row[] } | undefined)?.jobs ?? []),
    [resource.data],
  );
  const activeJobs = jobs.filter((job) => ACTIVE_STATES.has(String(job.status ?? "").toLowerCase()));
  const recentJobs = jobs.filter((job) => !ACTIVE_STATES.has(String(job.status ?? "").toLowerCase())).slice(0, 12);
  const activity = resource.data?.current.activity;
  const project = resource.data?.current.project;
  const session = resource.data?.current.session;

  if (!active) return <Empty text="灵机核心连接后会自动显示活动记录。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取灵机活动…" />;
  if (resource.error && !resource.data) return <Notice kind="error">活动记录暂不可用：{resource.error.message}</Notice>;

  return (
    <div className="stack observation-page">
      <section className="observation-hero">
        <div>
          <span className="desktop-eyebrow">LIVE ACTIVITY</span>
          <h2>{activity?.summary || (activeJobs.length ? "灵机正在处理任务" : "灵机当前空闲")}</h2>
          <p>
            {project?.name ? `项目 ${project.name}` : "未绑定项目"}
            {session?.title ? ` · ${session.title}` : ""}
            {activity?.stage ? ` · 阶段 ${activity.stage}` : ""}
          </p>
        </div>
        <div className="observation-live-state">
          <span className={activeJobs.length || activity ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{activeJobs.length ? `${activeJobs.length} 个任务处理中` : "没有运行中任务"}</strong>
            <small>{resource.refreshing ? "正在同步状态" : "每 4 秒自动更新"}</small>
          </div>
        </div>
      </section>

      {resource.error && resource.data && (
        <Notice kind="warning">状态同步暂时失败，正在保留最近一次结果并自动重试。</Notice>
      )}

      <Panel title="当前任务">
        {activeJobs.length ? (
          <div className="activity-card-list">
            {activeJobs.map((job) => (
              <article className="activity-card" key={String(job.job_id ?? job.updated_at)}>
                <div className="activity-card-heading">
                  <div>
                    <span className={`pill ${statusTone(job.status)}`}>{statusLabel(job.status)}</span>
                    <strong>{String(job.progress_message || job.source_type || "后台任务")}</strong>
                  </div>
                  <small>{dateTime(job.updated_at)}</small>
                </div>
                <div className="activity-card-meta">
                  <span>来源 {String(job.source_type ?? "未知")}</span>
                  <span>尝试 {Number(job.attempts ?? 0)}/{Number(job.max_attempts ?? 0)}</span>
                  <span>任务 {String(job.job_id ?? "未知")}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="observation-empty-state">
            <strong>系统空闲</strong>
            <p>没有排队、运行或自动重试中的任务。灵机会在有新输入时自行继续。</p>
          </div>
        )}
      </Panel>

      <Panel title="最近结果">
        {recentJobs.length ? (
          <div className="activity-timeline">
            {recentJobs.map((job) => (
              <article className="activity-timeline-item" key={String(job.job_id ?? job.updated_at)}>
                <span className={`timeline-marker ${String(job.status ?? "")}`} />
                <div>
                  <div className="activity-card-heading">
                    <strong>{String(job.progress_message || job.source_type || "后台任务")}</strong>
                    <span className={`pill ${statusTone(job.status)}`}>{statusLabel(job.status)}</span>
                  </div>
                  <p>{job.last_error ? String(job.last_error) : `来源 ${String(job.source_type ?? "未知")}`}</p>
                  <small>{dateTime(job.updated_at)}</small>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty text="还没有最近任务记录。" />
        )}
      </Panel>
    </div>
  );
}
