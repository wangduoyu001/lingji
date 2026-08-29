import { useCallback, useState } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PendingAction } from "../contracts/workFact";

export default function AttentionPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<{ pending_actions?: PendingAction[] }>("/api/work/pending-actions", { signal }), [api]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 8000, staleAfterMs: 25000, pauseWhenHidden: true });
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (!active) return <Empty text="连接灵机后会显示需要你处理的事项。" />;
  if (resource.error && !resource.data) return <Notice kind="error">暂时无法读取需要你处理的事项，请稍后重试。</Notice>;
  if (resource.loading && !resource.data) return <Notice>正在读取待处理事项…</Notice>;

  const actions = resource.data?.pending_actions ?? [];

  return (
    <div className="stack observation-page">
      <Panel title="需要我处理">
        {resource.stale && <Notice kind="warning">待办数据暂时过期，正在自动重试。</Notice>}
        {resource.error && <Notice kind="error">需要你处理的事项暂时无法刷新。</Notice>}
        {actionError && <Notice kind="error">这项处理没有完成，请稍后再试。</Notice>}
        {actions.length ? actions.map((action) => (
            <article key={action.action_id} className="attention-card">
            <div><h3>{action.description || "有一项事项需要你确认"}</h3><p>灵机已暂停这一步，等你处理后会继续。</p></div>
            <button className="button primary" disabled={busy !== null} onClick={async () => { setBusy(action.action_id); setActionError(null); try { await api.post(`/api/work/pending-actions/${encodeURIComponent(action.action_id)}/resolve`); await resource.refresh({ force: true }); } catch (reason) { setActionError(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(null); } }}>{busy === action.action_id ? "处理中…" : "完成处理"}</button>
          </article>
        )) : <Empty text="现在没有需要你处理的事项。灵机会继续自动工作。" />}
      </Panel>
    </div>
  );
}
