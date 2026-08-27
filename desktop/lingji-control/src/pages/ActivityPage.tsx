import { useCallback, useState } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkHistoryItem, WorkHistoryResponse } from "../contracts/workFact";

const shown = (value: unknown): string => value === null || value === undefined || value === "" ? "尚未获得" : String(value);
const time = (value: unknown): string => value ? new Date(String(value)).toLocaleString() : "尚未获得";

function WorkCard({ item }: { item: WorkHistoryItem }) {
  const summary = item.summary ?? {};
  const status = item.outcome?.status || item.work?.status;
  const result = summary.result || (status === "failed" ? "失败" : status === "completed" || status === "success" ? "成功" : null);
  return <article className="activity-card">
    <div className="activity-card-heading"><div><span className={`timeline-marker ${status === "failed" ? "failed" : status === "completed" || status === "success" ? "completed" : ""}`} /><strong>{shown(item.work?.title || summary.source)}</strong></div><span className={`pill ${status === "failed" ? "failed" : status === "completed" || status === "success" ? "success" : "neutral"}`}>{shown(summary.phase)}</span></div>
    <p className="activity-card-result">结果：{shown(result || item.outcome?.summary)}</p>
    <div className="activity-card-meta"><span>时间：{time(summary.time || item.work?.updated_at || item.work?.created_at)}</span><span>来源：{shown(summary.source)}</span><span>下一步：{shown(summary.next_actor)}</span></div>
    <details className="activity-diagnostics"><summary>查看技术详情（执行事件）</summary><small>工作 ID：{shown(item.work?.work_id)} · 状态码：{shown(status)} · 来源 ID：{shown(summary.source_id || item.work?.source_id)}</small>{(item.events ?? []).length > 0 && <pre>{JSON.stringify(item.events ?? [], null, 2)}</pre>}</details>
  </article>;
}

export default function ActivityPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const load = useCallback((signal: AbortSignal) => api.get<WorkHistoryResponse>(`/api/work/history?limit=20&offset=${offset}`, { signal }), [api, offset]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 5000, staleAfterMs: 15000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示活动记录。" />;
  if (resource.loading && !resource.data) return <Notice>正在读取活动记录…</Notice>;
  if (resource.error && !resource.data) return <Notice kind="error">活动读取失败：{resource.error.message}</Notice>;
  const items = resource.data?.items ?? [];
  return (
    <div className="stack observation-page activity-page">
      <Panel title="最近工作">
        <div className="activity-toolbar"><p>这里展示灵机最近实际完成、失败或仍在处理的工作（当前工作事实）。</p><button className="button secondary" disabled={resource.refreshing} onClick={() => void resource.refresh({ force: true })}>{resource.refreshing ? "读取中…" : "刷新"}</button></div>
        {resource.stale && <Notice kind="warning">活动数据暂时过期，正在自动重试。</Notice>}
        {resource.error && <Notice kind="error">活动刷新失败：{resource.error.message}</Notice>}
        {items.length ? <div className="activity-card-list">{items.map((item) => <WorkCard key={item.work?.work_id ?? `${offset}-${item.summary?.time}`} item={item} />)}</div> : <Empty text="还没有可显示的活动记录。" />}
        <div className="loop-pager activity-pager"><button disabled={offset === 0 || resource.loading} onClick={() => setOffset(Math.max(0, offset - 20))}>上一页</button><span>第 {Math.floor(offset / 20) + 1} 页{resource.data?.total == null ? " · 总数尚未获得" : ` · 共 ${resource.data.total} 条`}</span><button disabled={!resource.data?.has_more || resource.loading} onClick={() => setOffset(offset + 20)}>下一页</button></div>
      </Panel>
    </div>
  );
}
