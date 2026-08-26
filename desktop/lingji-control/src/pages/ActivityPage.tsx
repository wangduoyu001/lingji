import { useCallback } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkFact } from "../contracts/workFact";

const value = (v: unknown, fallback = "未知") => v ? String(v) : fallback;

export default function ActivityPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<WorkFact>("/api/work/current", { signal }), [api]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 5000, staleAfterMs: 15000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示活动记录。" />;
  if (resource.error && !resource.data) return <Notice kind="error">活动读取失败：{resource.error.message}</Notice>;
  if (resource.stale) return <Notice kind="warning">活动数据暂时过期，正在自动重试。</Notice>;

  return (
    <div className="stack observation-page">
      <Panel title="当前工作事实">
        <h2>{value(resource.data?.work?.title, "暂无工作")}</h2>
        <p>状态：{value(resource.data?.work?.status)} · 结果：{value(resource.data?.outcome?.summary, "尚未产生")}</p>
      </Panel>
      <Panel title="执行事件">
        {(resource.data?.events ?? []).length ? (resource.data?.events ?? []).map((event) => (
          <article key={event.event_id} className="activity-timeline-item">
            <strong>{value(event.event_type)}</strong>
            <p>{event.detail ? JSON.stringify(event.detail) : "无附加详情"}</p>
          </article>
        )) : <Empty text="暂无执行事件。" />}
      </Panel>
    </div>
  );
}
