import { useCallback } from "react";
import { Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkFact } from "../contracts/workFact";
import { formatWorkFactResult } from "./workFactPresentation";

export type CurrentWorkFact = WorkFact;

const text = (value: unknown, fallback = "检查结果尚未获得") =>
  value === null || value === undefined || value === "" ? fallback : String(value);
const readableWorkTitle = (value: unknown): string => {
  const title = String(value ?? "");
  return /^扫描\s+obsidian$/i.test(title) ? "Obsidian 长期记忆区" : title;
};
const readableNextAction = (action: WorkFact["next_action"] | undefined): string => {
  if (!action) return "暂时没有下一步";
  if (action.actor === "system") return "灵机会继续自动检查";
  return text(action.description);
};
const statusLabel = (value: unknown): string => ({
  queued: "排队中",
  active: "正在处理",
  running: "正在处理",
  pending: "等待处理",
  accepted: "已接收",
  retrying: "正在重试",
  completed: "已完成",
  success: "已完成",
  failed: "没有完成",
  cancelled: "已取消",
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
  const hasWork = Boolean(work?.title);
  const status = hasWork ? statusLabel(work?.status) : "目前空闲";

  return (
    <section className="panel current-work-panel">
      <div className="current-work-heading">
        <div>
          <h2>正在做什么</h2>
          <p className="current-work-readable">{hasWork ? readableWorkTitle(work?.title) : "目前没有正在处理的事情。"}</p>
        </div>
        <span className="pill">{status}</span>
      </div>
      {resource.stale && <Notice kind="warning">当前工作状态正在刷新。</Notice>}
      {hasWork && <div className="current-work-readable-line"><span>结果：{fact ? formatWorkFactResult(fact) : "还没有结果"}</span><span>下一步：{readableNextAction(fact?.next_action)}</span></div>}

      <details className="current-work-timeline">
        <summary>查看技术详情</summary>
        <div className="current-work-technical"><span>工作标识：{text(work?.work_id)}</span><span>来源标识：{text(work?.source_id)}</span></div>
        {fact?.outcome && <pre className="json-panel">{JSON.stringify({ summary: fact.outcome.summary, evidence: fact.outcome.evidence }, null, 2)}</pre>}
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
