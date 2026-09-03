import { useCallback, useMemo } from "react";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { MemorySourcesApi, ownerSourceName, periodicReconciliationNotice, scanCountValue } from "./memorySourcesApi";
import type { MemorySourcesSnapshot, ScanRun } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId, Row } from "../types";
import { pendingActionsFrom, type PendingActionsResponse } from "../contracts/workFact";
import { OwnerMemoryCardsApi } from "./ownerMemoryCardsApi";
import { ownerFacingConclusion, type OwnerMemoryCard } from "./ownerMemoryCardsTypes";

const display = (value: unknown, fallback = "尚未获得") => value === null || value === undefined || value === "" ? fallback : String(value);
const formatTime = (value: unknown): string => { if (!value) return "时间尚未获得"; const date = new Date(String(value)); return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString(); };
const stateTone = (value: unknown): "good" | "warn" | "bad" | "neutral" => { const state = String(value ?? "").toLowerCase(); if (["healthy", "ready", "available", "ok"].includes(state)) return "good"; if (["degraded", "warning", "busy", "configuration_required", "stale"].includes(state)) return "warn"; if (["failed", "error", "unavailable", "blocked"].includes(state)) return "bad"; return "neutral"; };
const stateLabel = (value: unknown) => ({ healthy: "灵机运行正常", ready: "灵机已准备好", degraded: "基础记忆可用，部分功能待处理", failed: "灵机暂时没有完成工作", unavailable: "灵机正在自动恢复", configuration_required: "等待首次设置", stale: "灵机正在刷新状态" } as Record<string, string>)[String(value ?? "")] ?? "灵机正在自动工作";

function latestCheckSummary(latest: ScanRun | null | undefined): string {
  if (!latest) return "还没有完成过自动检查。";
  const status = String(latest.status ?? "").toLowerCase();
  const stamp = formatTime(latest.updated_at);
  const added = scanCountValue(latest, "queued"); const updated = scanCountValue(latest, "updated"); const skipped = scanCountValue(latest, "skipped");
  if (status === "failed") return `最近一次自动检查未完成（${stamp}），原有记忆未受影响。`;
  if (status === "running") return "灵机正在检查新记录，完成后会自动更新记忆。";
  const parts = [added != null && added > 0 ? `新增 ${added} 条` : "", updated != null && updated > 0 ? `更新 ${updated} 条` : "", skipped != null && skipped > 0 ? `跳过 ${skipped} 条` : ""].filter(Boolean);
  return parts.length ? `最近一次自动检查完成：${parts.join("，")}（${stamp}）。` : `最近一次自动检查完成，暂未发现变化（${stamp}）。`;
}

export default function OverviewPage({ data, api, active, onNavigate }: { data: Row | null; api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]); const cardsApi = useMemo(() => new OwnerMemoryCardsApi(api), [api]);
  const sourceResource = usePollingResource<MemorySourcesSnapshot>({ fetcher: useCallback(() => sourceApi.snapshot(), [sourceApi]), enabled: active, intervalMs: 10_000, staleAfterMs: 30_000, pauseWhenHidden: true });
  const pendingResource = usePollingResource({ fetcher: useCallback((signal: AbortSignal) => api.get<PendingActionsResponse>("/api/work/pending-actions", { signal }), [api]), enabled: active, intervalMs: 8_000, staleAfterMs: 25_000, pauseWhenHidden: true });
  const cardSummaryResource = usePollingResource({ fetcher: useCallback((signal: AbortSignal) => cardsApi.summary(signal), [cardsApi]), enabled: active, intervalMs: 20_000, staleAfterMs: 45_000, pauseWhenHidden: true });
  const recentCardsResource = usePollingResource({ fetcher: useCallback((signal: AbortSignal) => cardsApi.list(0, signal, 6, "current"), [cardsApi]), enabled: active, intervalMs: 20_000, staleAfterMs: 45_000, pauseWhenHidden: true });
  if (!data) return <Empty text="灵机正在连接本机服务…" />;
  const d = data as Record<string, unknown>; const health = (d.health ?? {}) as Record<string, unknown>; const runtime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const runtimeState = health.status ?? runtime.state; const sourceSnapshot = sourceResource.data; const pending = pendingActionsFrom(pendingResource.data); const pendingUnavailable = Boolean(pendingResource.error || pendingResource.stale || pending === null); const cards = cardSummaryResource.data; const recentCards = (recentCardsResource.data?.items ?? []).filter((item: OwnerMemoryCard) => String(item.freshness?.state ?? "") === "current").slice(0, 6); const currentSources = sourceSnapshot?.sources.filter((item) => item.state === "current").map(ownerSourceName) ?? []; const latest = sourceSnapshot?.summary?.latest; const note = periodicReconciliationNotice(sourceSnapshot?.runtime); const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? String(value) : "—";
  const latestCheckTime = latest?.updated_at ? formatTime(latest.updated_at) : "尚未获得";
  const hasTodos = !pendingUnavailable && Boolean(pending?.length);

  return <div className="stack overview-page owner-observe-page">
    <section className={`overview-hero overview-hero-${stateTone(runtimeState)}`}><div className="overview-hero-main"><div className="overview-title-line"><span className="overview-status-mark" aria-hidden="true" /><h2>{stateLabel(runtimeState)}</h2></div><p>灵机正在自动扫描、整理并更新你的长期记忆，你只需要在这里查看成果。</p></div><div className="overview-live-summary"><strong>{pendingUnavailable ? "正在确认待办" : hasTodos ? "有一件事需要你决定" : "目前不需要你处理"}</strong><small>{pendingUnavailable ? "灵机仍会继续自动工作" : hasTodos ? display(pending?.[0]?.description) : "扫描和整理会自动进行"}</small>{hasTodos && <button className="button primary overview-attention-link" onClick={() => onNavigate("attention")}>处理待办</button>}</div></section>
    {pendingUnavailable && <Notice kind="warning">待办正在自动确认，当前不把未读取当作“没有待办”。</Notice>}{sourceResource.error && <Notice kind="warning">来源状态正在自动刷新，灵机不会因此停止记忆。</Notice>}{note && <Notice kind="info">{note}</Notice>}
    <section className="outcome-section recent-memory-section"><div className="section-heading"><div><span className="section-kicker">最近记住的内容</span><h3>灵机最近替你记住了什么</h3></div><span className="section-caption">自动更新</span></div>{recentCards.length ? <div className="recent-memory-list">{recentCards.map((card) => { const conclusion = ownerFacingConclusion(card); return <article className="recent-memory-item" key={card.memory_id}><strong>{display(card.topic, "未命名记忆")}</strong><p>{conclusion.text}</p><small>来源：{display(card.source?.label)}</small></article>; })}</div> : <p className="outcome-empty">灵机还没有形成具体记忆，完成一次来源检查后会出现在这里。</p>}</section>
    <section className="outcome-section takeover-summary-section"><div className="section-heading"><div><span className="section-kicker">最近自动接管成果</span><h3>接管了多少记录</h3></div><span className="section-caption">自动统计</span></div><div className="takeover-stats"><div><strong>{currentSources.length ? currentSources.join("、") : "尚未获得"}</strong><span>已接管来源</span></div><div><strong>{number(cards?.conversations)}</strong><span>已接管对话</span></div><div><strong>{number(cards?.messages)}</strong><span>已导入消息</span></div><div><strong>{latestCheckTime}</strong><span>最近检查时间</span></div></div><p className="proof-note latest-check-note">{latestCheckSummary(latest)}</p><p className="proof-note vector-note">当前记忆和长期记忆只统计仍然有效的内容；已接管对话与消息统计全部导入规模。{cards?.vectorized != null ? `其中 ${cards.vectorized} 件已准备语义检索。` : "语义检索状态会在后台自动更新。"}</p></section>
    <CurrentWorkPanel api={api} active={active} />
  </div>;
}
