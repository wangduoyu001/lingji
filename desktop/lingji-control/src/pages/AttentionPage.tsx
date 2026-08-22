import { useCallback } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PendingActionsFact } from "../contracts/workFact";

export default function AttentionPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<PendingActionsFact>("/api/work/pending-actions", { signal }), [api]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 8000, staleAfterMs: 25000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示需要处理事项。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取主人待办…" />;
  if (resource.error && !resource.data) return <Notice kind="warning">待处理事项暂时不可用，不能按 0 项处理。</Notice>;

  const actions = resource.data?.pending_actions ?? [];

  return (
    <div className="stack observation-page">
      {resource.error && resource.data ? <Notice kind="warning">刷新失败，当前显示上次成功读取的主人待办。</Notice> : null}
      <Panel title="需要主人处理">
        {actions.length ? actions.map((action) => (
          <article key={action.action_id} className="attention-card">
            <h3>{action.description}</h3>
            <p>{action.reason || "该事项需要主人明确决定后才能继续。"}</p>
            <p>Work ID：{action.work_id}</p>
          </article>
        )) : <Empty text="当前没有需要主人决定的事项。" />}
      </Panel>
    </div>
  );
}
