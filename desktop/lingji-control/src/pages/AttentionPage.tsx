import { useCallback } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PendingAction } from "../contracts/workFact";

export default function AttentionPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<{ pending_actions?: PendingAction[] }>("/api/work/pending-actions", { signal }), [api]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 8000, staleAfterMs: 25000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示需要处理事项。" />;
  if (resource.error && !resource.data) return <Notice kind="error">待处理事项读取失败：{resource.error.message}</Notice>;
  if (resource.stale) return <Notice kind="warning">待办数据暂时过期，正在自动重试。</Notice>;

  const actions = resource.data?.pending_actions ?? [];

  return (
    <div className="stack observation-page">
      <Panel title="需要主人处理">
        {actions.length ? actions.map((action) => (
            <article key={action.action_id} className="attention-card">
            <h3>{action.description}</h3>
            <p>工作 {action.work_id} · 执行者：{action.actor}</p>
          </article>
        )) : <Empty text="当前没有需要主人决定的事项。" />}
      </Panel>
    </div>
  );
}
