import { useCallback, useMemo } from "react";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { MemorySourcesApi, ownerSourceName, periodicReconciliationNotice, scanCountValue, sourceStateLabel } from "./memorySourcesApi";
import type { MemorySourcesSnapshot, ScanRun } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId, Row } from "../types";
import type { PendingAction } from "../contracts/workFact";
import { OwnerMemoryCardsApi } from "./ownerMemoryCardsApi";
import type { OwnerMemoryCardsResponse } from "./ownerMemoryCardsTypes";

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
  const queued = scanCountValue(latest, "queued");
  const updated = scanCountValue(latest, "updated");
  const skipped = scanCountValue(latest, "skipped");
  if (status === "failed") return `最近一次检查没有完成${when}。`;
  const parts = [
    queued !== undefined && queued > 0 ? `新增 ${queued} 条` : "",
    updated !== undefined ? `更新 ${updated} 条` : "",
    skipped !== undefined ? `跳过 ${skipped} 条` : "",
  ].filter(Boolean);
  const phase = status === "completed" ? "已完成" : status === "running" ? "正在进行" : status === "failed" ? "没有完成" : "已记录";
  if (status === "completed" && queued === 0 && parts.length === 0) return `最近一次检查${phase}${when}，未发现新内容。`;
  const outcome = parts.length ? `：${parts.join("，")}` : "";
  return `最近一次检查${phase}${when}${outcome}。`;
}

export default function OverviewPage({ data, api, active, onNavigate }: { data: Row | null; api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]);
  const cardsApi = useMemo(() => new OwnerMemoryCardsApi(api), [api]);
  const loadSources = useCallback(() => sourceApi.snapshot(), [sourceApi]);
  const sourceResource = usePollingResource<MemorySourcesSnapshot>({ fetcher: loadSources, enabled: active, intervalMs: 10_000, staleAfterMs: 30_000 });
  const loadPending = useCallback((signal: AbortSignal) => api.get<{ pending_actions?: PendingAction[] }>("/api/work/pending-actions", { signal }), [api]);
  const pendingResource = usePollingResource({ fetcher: loadPending, enabled: active, intervalMs: 8_000, staleAfterMs: 25_000, pauseWhenHidden: true });
  const cardsResource = usePollingResource<OwnerMemoryCardsResponse>({ fetcher: useCallback(() => cardsApi.list(0, undefined, 50), [cardsApi]), enabled: active, intervalMs: 20_000, staleAfterMs: 45_000, pauseWhenHidden: true });
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
  const cards = cardsResource.data?.items ?? [];
  const cardTotal = cardsResource.data?.pagination?.total;
  const permanentCount = cards.filter((card) => ["complete", "available"].includes(String(card.layers?.permanent?.state ?? ""))).length;
  const vectorCount = cards.filter((card) => ["complete", "available"].includes(String(card.layers?.vector?.state ?? ""))).length;
  const reviewCount = cards.filter((card) => ["confirm", "review"].includes(String(card.action?.type ?? ""))).length;
  const metric = (value: number | null | undefined) => typeof value === "number" ? String(value) : "尚未获得";

  return <div className="stack overview-page observation-page">
    <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
      <div className="overview-hero-main"><div className="overview-title-line"><h2>{stateLabel(runtimeState)}</h2></div><p>{pendingUnavailable ? "待办状态暂时无法确认，正在重试" : pendingActions.length ? `现在需要你处理：${display(pendingActions[0]?.description, "一项待确认事项")}` : "你现在不用做任何事"}</p></div>
      <div className="observation-live-state"><span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} /><div><strong>{pendingUnavailable ? "暂时无法确认" : pendingActions.length ? "需要你处理" : "目前不需要你处理"}</strong><small>{pendingUnavailable ? "灵机正在重试" : "灵机状态会自动更新"}</small></div>{pendingActions.length > 0 && !pendingUnavailable && <button className="button secondary" onClick={() => onNavigate("attention")}>去处理</button>}</div>
    </section>
    {pendingUnavailable && <Notice kind="warning">待办状态暂时无法确认，正在重试。</Notice>}
    {sourceResource.stale && <Notice kind="warning">来源状态来自上一次成功读取，正在刷新。</Notice>}
    {sourceResource.error && <Notice kind="warning">来源状态暂时无法读取，请打开“记忆来源”重试。</Notice>}
    {periodicNotice && <Notice kind="info">{periodicNotice}</Notice>}
    <section className="overview-section owner-memory-summary"><div className="overview-section-heading"><div><h3>记忆摘要</h3><p className="overview-section-lede">这些数字和“记忆内容”使用同一份卡片记录。</p></div><button className="button primary" onClick={() => onNavigate("memory_cards")}>打开记忆内容</button></div><div className="metric-grid"><div className="metric"><span>发现候选</span><strong>{metric(sourceSnapshot?.discovered.length)}</strong></div><div className="metric"><span>记忆卡片</span><strong>{metric(cardTotal)}</strong></div><div className="metric"><span>已进入长期记忆</span><strong>{cardsResource.data ? permanentCount : "尚未获得"}</strong></div><div className="metric"><span>语义向量</span><strong>{cardsResource.data ? vectorCount : "尚未获得"}</strong></div><div className="metric"><span>需要我确认</span><strong>{cardsResource.data ? reviewCount : "尚未获得"}</strong></div></div></section>
    <CurrentWorkPanel api={api} active={active} />

    <section className="overview-section source-overview-card"><div className="overview-section-heading"><div><h3>正在记住什么</h3><p className="overview-section-lede">灵机只记住你明确允许的来源。</p></div><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看记忆来源</button></div>
      <p className="overview-readable-line">{sourceSnapshot ? currentNames.length ? `灵机正在记住：${currentNames.join("、")}。` : "目前还没有完成接管的来源。" : "记忆来源尚未获得。"}</p>
    </section>

    <section className="overview-section"><div className="overview-section-heading"><div><h3>最近一次检查</h3><p className="overview-section-lede">这里告诉你灵机上次实际做了什么。</p></div>{latestSource && <small>{sourceStateLabel(latestSource.state)}</small>}</div><p className="overview-readable-line">{latestCheckSummary(latest)}</p><div className="overview-inline-actions"><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看这次检查</button><button className="button secondary" onClick={() => onNavigate("activity")}>查看活动记录</button></div></section>

    <section className="overview-section"><div className="overview-section-heading"><div><h3>最近工作</h3><p className="overview-section-lede">这里是工作记录，不是记忆内容。</p></div><button className="button secondary" onClick={() => onNavigate("activity")}>活动记录</button></div><p className="overview-readable-line">最近工作记录已更新，可查看完整活动记录。</p></section>
    <div className="overview-footer-actions"><button className="button secondary" onClick={() => onNavigate("diagnostics")}>打开高级诊断</button></div>
  </div>;
}
