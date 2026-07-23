import { useCallback } from "react";
import type { LingJiApi } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";
import type { CodexCurrent } from "../pages/codexWorkspaceTypes";

const value = (input: unknown, fallback = "未知") => input === null || input === undefined || input === "" ? fallback : String(input);

const stageLabel = (stage: unknown): string => {
  const key = String(stage ?? "").toLowerCase();
  const labels: Record<string, string> = {
    receive: "接收输入",
    queued: "等待处理",
    reading: "读取内容",
    extracting: "提取信息",
    structuring: "结构化",
    writing: "写入记录",
    indexing: "更新索引",
    completed: "处理完成",
    failed: "处理失败",
  };
  return labels[key] ?? value(stage, "未报告阶段");
};

export default function CurrentWorkPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback(
    (signal: AbortSignal) => api.get<CodexCurrent>("/api/codex/current", { signal }),
    [api],
  );
  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 5_000,
    staleAfterMs: 18_000,
    pauseWhenHidden: true,
  });

  const current = resource.data;
  const project = current?.project;
  const session = current?.session;
  const activity = current?.activity;
  const progressCurrent = Number(activity?.progress_current ?? 0);
  const progressTotal = Number(activity?.progress_total ?? 0);
  const hasProgress = progressTotal > 0;
  const progressPercent = hasProgress ? Math.min(100, Math.max(0, Math.round((progressCurrent / progressTotal) * 100))) : 0;

  if (!active) {
    return <section className="panel current-work-panel"><h2>当前工作</h2><p>灵机核心连接后会自动显示。</p></section>;
  }

  return (
    <section className="panel current-work-panel">
      <div className="current-work-heading">
        <div>
          <span className="desktop-eyebrow">CURRENT WORK</span>
          <h2>{activity?.summary || (session?.title ? "正在跟踪当前会话" : "系统当前空闲")}</h2>
        </div>
        <div className="observation-live-state">
          <span className={activity ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{activity ? stageLabel(activity.stage) : "等待新任务"}</strong>
            <small>{resource.refreshing ? "同步中" : "自动更新"}</small>
          </div>
        </div>
      </div>

      {resource.error && <p className="current-work-warning">最近一次同步失败，正在保留已有状态并自动重试。</p>}

      <div className="current-work-summary">
        <div><span>当前项目</span><strong>{value(project?.name, "未绑定")}</strong></div>
        <div><span>当前会话</span><strong>{value(session?.title, "无活动会话")}</strong></div>
        <div><span>阶段</span><strong>{stageLabel(activity?.stage)}</strong></div>
        <div><span>待审核记忆</span><strong>{typeof current?.pending_review_count === "number" ? String(current.pending_review_count) : "未知"}</strong></div>
      </div>

      {hasProgress && (
        <div className="current-work-progress" aria-label={`任务进度 ${progressPercent}%`}>
          <div><span>处理进度</span><strong>{progressCurrent} / {progressTotal}</strong></div>
          <div className="progress-track"><span style={{ width: `${progressPercent}%` }} /></div>
        </div>
      )}

      <div className="current-work-footnote">
        <span>分支 {value(project?.branch)}</span>
        <span>最近检查点 {value(current?.last_checkpoint_at)}</span>
        <span>记忆索引 {value(current?.memory_index_state)}</span>
      </div>
    </section>
  );
}
