import { useCallback } from "react";
import { Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkFact } from "../contracts/workFact";

export type CurrentWorkFact = WorkFact;

const text = (value: unknown, fallback = "未知") =>
  value === null || value === undefined || value === "" ? fallback : String(value);

export default function CurrentWorkPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<CurrentWorkFact>("/api/work/current", { signal }), [api]);
  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 5000,
    staleAfterMs: 18000,
    pauseWhenHidden: true,
  });

  if (!active) return <section className="panel current-work-panel"><h2>当前工作</h2><p>连接灵机后显示。</p></section>;
  if (resource.error && !resource.data) return <section className="panel current-work-panel"><h2>当前工作</h2><Notice kind="error">工作事实读取失败：{resource.error.message}</Notice></section>;

  const fact = resource.data;
  const work = fact?.work;

  return (
    <section className="panel current-work-panel">
      <div className="current-work-heading">
        <div>
          <span className="desktop-eyebrow">OWNER WORK FACT</span>
          <h2>{text(work?.title, "当前没有进行中的工作")}</h2>
        </div>
        <span className="pill">{text(work?.status, "idle")}</span>
      </div>
      {resource.stale && <Notice kind="warning">工作事实暂时过期，正在自动重试。</Notice>}

      <div className="current-work-summary">
        <div><span>任务</span><strong>{text(work?.work_id)}</strong></div>
        <div><span>事件</span><strong>{String(fact?.events?.length ?? 0)}</strong></div>
        <div><span>结果</span><strong>{text(fact?.outcome?.summary, "等待结果")}</strong></div>
        <div><span>下一步</span><strong>{text(fact?.next_action?.description, "无")}</strong></div>
      </div>

      <div className="current-work-timeline">
        {(fact?.events ?? []).slice(0, 5).map((event) => (
          <div key={event.event_id}>
            <strong>{text(event.event_type)}</strong>
            <span>{text(event.detail ? JSON.stringify(event.detail) : "")}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
