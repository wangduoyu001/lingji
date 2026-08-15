import { useCallback, useEffect } from "react";
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
  return labels[key] ?? value(stage, "等待新任务");
};

export default function CurrentWorkPanel({
  api,
  active,
  onPendingReviewCount,
}: {
  api: LingJiApi;
  active: boolean;
  onPendingReviewCount?: (count: number) => void;
}) {
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
  const pendingReviewCount = typeof current?.pending_review_count === "number" ? current.pending_review_count : 0;
  const progressCurrent = Number(activity?.progress_current ?? 0);
  const progressTotal = Number(activity?.progress_total ?? 0);
  const hasProgress = progressTotal > 0;
  const progressPercent = hasProgress ? Math.min(100, Math.max(0, Math.round((progressCurrent / progressTotal) * 100))) : 0;

  useEffect(() => {
    onPendingReviewCount?.(pendingReviewCount);
  }, [onPendingReviewCount, pendingReviewCount]);

  if (!active) return null;

  // The daily home should not invent a "current work" card when nothing is happening.
  // Keep polling so owner decisions still surface, but render only real work, review or an actual read failure.
  if (!activity && pendingReviewCount === 0 && !resource.error) return null;

  return (
    <section className="panel current-work-panel current-work-compact">
      <div className="current-work-heading">
        <div>
          <span className="desktop-eyebrow">当前真实任务</span>
          <h2>{activity?.summary || `${pendingReviewCount} 条候选记忆等待确认`}</h2>
          <p className="current-work-description">
            {activity
              ? `${value(project?.name, "未绑定项目")} · ${value(session?.title, "无活动工作记录")}`
              : "没有正在运行的 Codex 任务，只保留需要你确认的候选。"}
          </p>
        </div>
        <div className="observation-live-state">
          <span className={activity ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{activity ? stageLabel(activity.stage) : "等待确认"}</strong>
            <small>{resource.refreshing ? "同步中" : "自动更新"}</small>
          </div>
        </div>
      </div>

      {resource.error && <p className="current-work-warning">最近一次同步失败，已有状态会保留，灵机会自动重试。</p>}

      <div className="current-work-inline-facts">
        {activity && <span><small>当前项目</small><strong>{value(project?.name, "未绑定")}</strong></span>}
        {activity && <span><small>Codex 工作记录</small><strong>{value(session?.title, "无活动记录")}</strong></span>}
        {pendingReviewCount > 0 && <span className="warning"><small>需要你决定</small><strong>{pendingReviewCount} 条候选记忆</strong></span>}
      </div>

      {hasProgress && (
        <div className="current-work-progress" aria-label={`任务进度 ${progressPercent}%`}>
          <div><span>{stageLabel(activity?.stage)}</span><strong>{progressCurrent} / {progressTotal}</strong></div>
          <div className="progress-track"><span style={{ width: `${progressPercent}%` }} /></div>
        </div>
      )}

      {activity && (
        <details className="current-work-details">
          <summary>工作细节</summary>
          <div>
            <span>分支 {value(project?.branch)}</span>
            <span>最近检查点 {value(current?.last_checkpoint_at)}</span>
            <span>记忆索引 {value(current?.memory_index_state)}</span>
          </div>
        </details>
      )}
    </section>
  );
}
