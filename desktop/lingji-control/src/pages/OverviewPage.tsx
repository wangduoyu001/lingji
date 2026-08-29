import { useCallback, useMemo } from "react";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { MemorySourcesApi, ownerSourceName, periodicReconciliationNotice, scanCountValue, sourceStateLabel } from "./memorySourcesApi";
import type { MemorySourcesSnapshot, ScanRun } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId, Row } from "../types";
import type { PendingAction } from "../contracts/workFact";

const display = (value: unknown, fallback = "检查结果尚未获得") => value === null || value === undefined || value === "" ? fallback : String(value);
const stateTone = (value: unknown): "good" | "warn" | "bad" | undefined => {
  const state = String(value ?? "").toLowerCase();
  if (["healthy", "ready", "available", "ok"].includes(state)) return "good";
  if (["degraded", "warning", "busy", "configuration_required", "stale"].includes(state)) return "warn";
  if (["failed", "error", "unavailable", "blocked"].includes(state)) return "bad";
  return undefined;
};
const stateLabel = (value: unknown) => ({ healthy: "灵机运行正常", ready: "灵机已准备好", degraded: "灵机需要检查", failed: "灵机运行失败", unavailable: "灵机暂时不可用", configuration_required: "需要先完成设置", stale: "状态需要刷新" } as Record<string, string>)[String(value ?? "")] ?? display(value, "运行状态尚未获得");

function formatTime(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

function latestCheckSummary(latest: ScanRun | null | undefined): string {
  if (!latest) return "还没有检查记录。";
  const status = String(latest.status ?? "").toLowerCase();
  const stamp = formatTime(latest.updated_at);
  const when = stamp === "时间尚未获得" ? "" : `（${stamp}）`;
  if (status === "failed") return `最近一次检查没有完成${when}。`;
  const parts = [
    scanCountValue(latest, "queued") !== undefined ? `新增 ${scanCountValue(latest, "queued")} 条` : "",
    scanCountValue(latest, "updated") !== undefined ? `更新 ${scanCountValue(latest, "updated")} 条` : "",
    scanCountValue(latest, "skipped") !== undefined ? `跳过 ${scanCountValue(latest, "skipped")} 条` : "",
  ].filter(Boolean);
  const phase = status === "completed" ? "已完成" : status === "running" ? "正在进行" : status === "failed" ? "没有完成" : "已记录";
  const outcome = parts.length ? `：${parts.join("，")}` : "";
  return `最近一次检查${phase}${when}${outcome}。`;
}

export default function OverviewPage({ data, api, active, onNavigate }: { data: Row | null; api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]);
  const loadSources = useCallback(() => sourceApi.snapshot(), [sourceApi]);
  const sourceResource = usePollingResource<MemorySourcesSnapshot>({ fetcher: loadSources, enabled: active, intervalMs: 10_000, staleAfterMs: 30_000 });
  const loadPending = useCallback((signal: AbortSignal) => api.get<{ pending_actions?: PendingAction[] }>("/api/work/pending-actions", { signal }), [api]);
  const pendingResource = usePollingResource({ fetcher: loadPending, enabled: active, intervalMs: 8_000, staleAfterMs: 25_000, pauseWhenHidden: true });
  if (!data) return <Empty text="连接灵机后会显示运行状态。" />;
  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const runtimeState = memoryRuntime.state ?? health.status;
  const sourceSnapshot = sourceResource.data;
  const latest = sourceSnapshot?.summary?.latest;
  const latestSource = latest ? sourceSnapshot?.sources.find((item) => item.source_id === latest.source_id) : undefined;
  const pendingUnavailable = Boolean(pendingResource.error || pendingResource.stale || !pendingResource.data);
  const pendingActions = pendingResource.data?.pending_actions ?? [];
  const currentNames = sourceSnapshot?.sources.filter((item) => item.state === "current").map(ownerSourceName) ?? [];
  const periodicNotice = periodicReconciliationNotice(sourceSnapshot?.runtime);

  return <div className="stack overview-page observation-page">
    <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
      <div className="overview-hero-main"><div className="overview-title-line"><h2>{stateLabel(runtimeState)}</h2></div><p>{pendingUnavailable ? "待办状态暂时无法确认，正在重试" : pendingActions.length ? `现在需要你处理：${display(pendingActions[0]?.description, "一项待确认事项")}` : "你现在不用做任何事"}</p></div>
      <div className="observation-live-state"><span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} /><div><strong>{pendingUnavailable ? "暂时无法确认" : pendingActions.length ? "需要你处理" : "目前不需要你处理"}</strong><small>{pendingUnavailable ? "灵机正在重试" : "灵机状态会自动更新"}</small></div>{pendingActions.length > 0 && !pendingUnavailable && <button className="button secondary" onClick={() => onNavigate("attention")}>去处理</button>}</div>
    </section>
    {pendingUnavailable && <Notice kind="warning">待办状态暂时无法确认，正在重试。</Notice>}
    {sourceResource.stale && <Notice kind="warning">来源状态来自上一次成功读取，正在刷新。</Notice>}
    {sourceResource.error && <Notice kind="warning">来源状态暂时无法读取，请打开“记忆来源”重试。</Notice>}
    {periodicNotice && <Notice kind="info">{periodicNotice}</Notice>}
    <CurrentWorkPanel api={api} active={active} />

    <section className="overview-section source-overview-card"><div className="overview-section-heading"><div><h3>正在记住什么</h3><p className="overview-section-lede">灵机只记住你明确允许的来源。</p></div><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看记忆来源</button></div>
      <p className="overview-readable-line">{sourceSnapshot ? currentNames.length ? `灵机正在记住：${currentNames.join("、")}。` : "目前还没有完成接管的来源。" : "记忆来源尚未获得。"}</p>
    </section>

    <section className="overview-section"><div className="overview-section-heading"><div><h3>最近一次检查</h3><p className="overview-section-lede">这里告诉你灵机上次实际做了什么。</p></div>{latestSource && <small>{sourceStateLabel(latestSource.state)}</small>}</div><p className="overview-readable-line">{latestCheckSummary(latest)}</p><div className="overview-inline-actions"><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看这次检查</button><button className="button secondary" onClick={() => onNavigate("activity")}>查看活动记录</button></div></section>

    <section className="overview-section"><div className="overview-section-heading"><div><h3>长期记忆</h3><p className="overview-section-lede">需要你确认的内容会单独放到“需要我处理”。</p></div><button className="button secondary" onClick={() => onNavigate("memory_review")}>查看记忆审核</button></div><p className="overview-readable-line">记忆正文会保存在 Obsidian 长期记忆区；灵机不会在没有你确认时直接写入永久记忆。</p></section>
    <div className="overview-footer-actions"><button className="button secondary" onClick={() => onNavigate("diagnostics")}>打开高级诊断</button></div>
  </div>;
}
