import { useCallback } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import { formatWorkDetail, type CurrentWorkFact } from "../contracts/workFact";

const value = (v: unknown, fallback = "未知") =>
  v === null || v === undefined || v === "" ? fallback : String(v);

export default function ActivityPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<CurrentWorkFact>("/api/work/current", { signal }), [api]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 5000, staleAfterMs: 15000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示活动记录。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取真实工作事实…" />;
  if (resource.error && !resource.data) return <Notice kind="error">活动读取失败，当前状态未知。</Notice>;

  const work = resource.data?.work ?? null;
  const events = resource.data?.events ?? [];

  return (
    <div className="stack observation-page">
      {resource.error && resource.data ? <Notice kind="warning">刷新失败，当前显示上次成功读取的数据。</Notice> : null}
      <Panel title="当前工作事实">
        <h2>{value(work?.title, "暂无进行中的工作")}</h2>
        <p>状态：{value(work?.status, "idle")}</p>
        <p>Work ID：{value(work?.work_id, "无")}</p>
      </Panel>
      <Panel title="执行事件">
        {events.length ? events.map((event) => (
          <article key={event.event_id} className="activity-timeline-item">
            <strong>{value(event.event_type)}</strong>
            <p>{formatWorkDetail(event.detail)}</p>
          </article>
        )) : <Empty text={work ? "当前工作暂无执行事件。" : "当前没有进行中的工作，因此没有当前事件。"} />}
      </Panel>
    </div>
  );
}
