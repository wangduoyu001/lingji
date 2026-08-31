import { useCallback, useState } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import { pendingActionsFrom, type PendingActionsResponse } from "../contracts/workFact";

export default function AttentionPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<PendingActionsResponse>("/api/work/pending-actions", { signal }), [api]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 8000, staleAfterMs: 25000, pauseWhenHidden: true });
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (!active) return <Empty text="连接灵机后会显示需要你处理的事项。" />;
  if (resource.error && !resource.data) return <Notice kind="warning">暂时无法确认需要你处理的事项，正在重试。</Notice>;
  if (resource.loading && !resource.data) return <Notice>正在读取待处理事项…</Notice>;

  const actions = pendingActionsFrom(resource.data);
  if (resource.error || resource.stale || actions === null) return <Notice kind="warning">暂时无法确认需要你处理的事项，正在重试。</Notice>;

  return (
    <div className="stack observation-page owner-attention-page">
      <section className="workspace-hero attention-hero"><div><span className="section-kicker">只有必要时出现</span><h2>需要我</h2><p>普通内容由灵机自动整理。只有高风险或无法自动判断的事情，才会停在这里。</p></div><span className="auto-refresh-note">自动检查中</span></section>
      <Panel title="需要你决定的事">
        {resource.stale && <Notice kind="warning">待办数据暂时过期，正在自动重试。</Notice>}
        {resource.error && <Notice kind="error">需要你处理的事项暂时无法刷新。</Notice>}
        {actionError && <Notice kind="error">这项处理没有完成，请稍后再试。</Notice>}
        {actions.length ? actions.map((action) => (
            <article key={action.action_id} className="attention-card">
            <div><h3>{action.description || "有一项事项需要你确认"}</h3><p>灵机暂时不会替你做这个决定；处理后会继续自动整理。</p></div>
            <button className="button primary" disabled={busy !== null} onClick={async () => { setBusy(action.action_id); setActionError(null); try { await api.post(`/api/work/pending-actions/${encodeURIComponent(action.action_id)}/resolve`); await resource.refresh({ force: true }); } catch (reason) { setActionError(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(null); } }}>{busy === action.action_id ? "保存中…" : "我已确认，继续处理"}</button>
          </article>
        )) : <Empty text="现在没有需要你处理的事项。灵机会继续自动工作。" />}
      </Panel>
    </div>
  );
}
