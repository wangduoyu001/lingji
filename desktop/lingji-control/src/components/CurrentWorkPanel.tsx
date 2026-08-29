import { useCallback } from "react";
import { Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkFact } from "../contracts/workFact";

export type CurrentWorkFact = WorkFact;

const text = (value: unknown, fallback = "检查结果尚未获得") =>
  value === null || value === undefined || value === "" ? fallback : String(value);
const statusLabel = (value: unknown): string => ({
  active: "正在处理",
  running: "正在处理",
  pending: "等待处理",
  completed: "已完成",
  success: "已完成",
  failed: "没有完成",
  idle: "目前没有进行中的工作",
} as Record<string, string>)[String(value ?? "")] ?? "状态尚未获得";

export default function CurrentWorkPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<CurrentWorkFact>("/api/work/current", { signal }), [api]);
  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 5000,
    staleAfterMs: 18000,
    pauseWhenHidden: true,
  });

  if (!active) return <section className="panel current-work-panel"><h2>正在做什么</h2><p>连接灵机后会显示。</p></section>;
  if (resource.error && !resource.data) return <section className="panel current-work-panel"><h2>正在做什么</h2><Notice kind="error">暂时无法读取当前工作，请稍后重试。</Notice></section>;

  const fact = resource.data;
  const work = fact?.work;
  const status = statusLabel(work?.status);
  const hasWork = Boolean(work?.title);

  return (
    <section className="panel current-work-panel">
      <div className="current-work-heading">
        <div>
          <h2>正在做什么</h2>
          <p className="current-work-readable">{hasWork ? text(work?.title) : "目前没有正在处理的事情。"}</p>
        </div>
        <span className="pill">{status}</span>
      </div>
      {resource.stale && <Notice kind="warning">当前工作状态正在刷新。</Notice>}
      {hasWork && <div className="current-work-readable-line"><span>结果：{text(fact?.outcome?.summary, "还没有结果")}</span><span>下一步：{text(fact?.next_action?.description, "暂时没有下一步")}</span></div>}

      <details className="current-work-timeline">
        <summary>查看技术详情</summary>
        <div className="current-work-technical"><span>工作标识：{text(work?.work_id)}</span><span>来源标识：{text(work?.source_id)}</span></div>
        {(fact?.events ?? []).slice(0, 5).map((event) => (
          <div key={event.event_id}>
            <strong>{text(event.event_type)}</strong>
            <span>{text(event.detail?.summary ?? event.detail?.message, "技术事件已记录")}</span>
          </div>
        ))}
      </details>
    </section>
  );
}
