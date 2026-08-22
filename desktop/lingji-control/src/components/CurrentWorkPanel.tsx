import { useCallback } from "react";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import { formatWorkDetail, type CurrentWorkFact } from "../contracts/workFact";

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
  if (resource.loading && !resource.data) return <section className="panel current-work-panel"><h2>当前工作</h2><p>正在读取真实工作状态…</p></section>;
  if (resource.error && !resource.data) return <section className="panel current-work-panel"><h2>当前工作</h2><p>当前工作读取失败，不能把接口不可用当成“没有工作”。</p></section>;

  const fact = resource.data;
  const work = fact?.work ?? null;

  return (
    <section className="panel current-work-panel">
      <div className="current-work-heading">
        <div>
          <span className="desktop-eyebrow">OWNER WORK FACT</span>
          <h2>{text(work?.title, "当前没有进行中的工作")}</h2>
        </div>
        <span className="pill">{text(work?.status, "idle")}</span>
      </div>

      {resource.error && resource.data ? <p>数据刷新失败，当前显示上次成功读取的工作事实。</p> : null}

      <div className="current-work-summary">
        <div><span>任务</span><strong>{text(work?.work_id, "无")}</strong></div>
        <div><span>事件</span><strong>{String(fact?.events.length ?? 0)}</strong></div>
        <div><span>结果</span><strong>{text(fact?.outcome?.summary, work ? "等待结果" : "无")}</strong></div>
        <div><span>下一步</span><strong>{text(fact?.next_action?.description, "无")}</strong></div>
      </div>

      <div className="current-work-timeline">
        {(fact?.events ?? []).slice(-5).map((event) => (
          <div key={event.event_id}>
            <strong>{text(event.event_type)}</strong>
            <span>{formatWorkDetail(event.detail)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
