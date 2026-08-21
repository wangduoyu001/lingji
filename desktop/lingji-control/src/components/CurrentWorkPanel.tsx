import { useCallback } from "react";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkItem, ExecutionEvent, Outcome, NextAction } from "../contracts/workFact";

export type CurrentWorkFact = {
  work?: WorkItem;
  events?: ExecutionEvent[];
  outcome?: Outcome;
  next_action?: NextAction;
};

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

      <div className="current-work-summary">
        <div><span>任务</span><strong>{text(work?.id)}</strong></div>
        <div><span>事件</span><strong>{String(fact?.events?.length ?? 0)}</strong></div>
        <div><span>结果</span><strong>{text(fact?.outcome?.summary, "等待结果")}</strong></div>
        <div><span>下一步</span><strong>{text(fact?.next_action?.summary, "无")}</strong></div>
      </div>

      <div className="current-work-timeline">
        {(fact?.events ?? []).slice(0, 5).map((event) => (
          <div key={event.id}>
            <strong>{text(event.event)}</strong>
            <span>{text(event.detail)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
