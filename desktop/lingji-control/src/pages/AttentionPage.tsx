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

  if (!active) return <Empty text="连接灵机后显示需要处理事项。" />;
  if (resource.error && !resource.data) return <Notice kind="error">待处理事项读取失败：{resource.error.message}</Notice>;
  if (resource.loading && !resource.data) return <Notice>正在读取待处理事项…</Notice>;

  const actions = resource.data?.pending_actions ?? [];

  return (
    <div className="stack observation-page">
      <Panel title="需要主人处理">
        {resource.stale && <Notice kind="warning">待办数据暂时过期，正在自动重试。</Notice>}
        {resource.error && <Notice kind="error">待办刷新失败：{resource.error.message}</Notice>}
        {actionError && <Notice kind="error">处理失败：{actionError}</Notice>}
        {actions.length ? actions.map((action) => (
            <article key={action.action_id} className="attention-card">
            <div><span className="desktop-eyebrow">主人下一步</span><h3>{action.description || "尚未获得"}</h3><p>工作 {action.work_id || "尚未获得"} · 执行者：{action.actor === "owner" ? "主人" : action.actor === "system" ? "灵机" : action.actor || "尚未获得"}</p></div>
            <button className="button primary" disabled={busy !== null} onClick={async () => { setBusy(action.action_id); setActionError(null); try { await api.post(`/api/work/pending-actions/${encodeURIComponent(action.action_id)}/resolve`); await resource.refresh({ force: true }); } catch (reason) { setActionError(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(null); } }}>{busy === action.action_id ? "处理中…" : "完成处理"}</button>
          </article>
        )) : <Empty text="当前没有需要主人决定的事项。" />}
      </Panel>
    </div>
  );
}
