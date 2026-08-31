import { useCallback, useMemo } from "react";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { MemorySourcesApi, ownerSourceName, periodicReconciliationNotice, scanCountValue } from "./memorySourcesApi";
import type { MemorySourcesSnapshot, ScanRun } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId, Row } from "../types";
import { pendingActionsFrom, type PendingActionsResponse, type WorkHistoryResponse } from "../contracts/workFact";
import { OwnerMemoryCardsApi } from "./ownerMemoryCardsApi";
import { formatWorkFactResult, formatWorkFactTitle } from "../components/workFactPresentation";

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

export default function OverviewPage({ data, api, active, onNavigate: _onNavigate }: { data: Row | null; api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]); const cardsApi = useMemo(() => new OwnerMemoryCardsApi(api), [api]);
  const sourceResource = usePollingResource<MemorySourcesSnapshot>({ fetcher: useCallback(() => sourceApi.snapshot(), [sourceApi]), enabled: active, intervalMs: 10_000, staleAfterMs: 30_000, pauseWhenHidden: true });
  const pendingResource = usePollingResource({ fetcher: useCallback((signal: AbortSignal) => api.get<PendingActionsResponse>("/api/work/pending-actions", { signal }), [api]), enabled: active, intervalMs: 8_000, staleAfterMs: 25_000, pauseWhenHidden: true });
  const cardSummaryResource = usePollingResource({ fetcher: useCallback((signal: AbortSignal) => cardsApi.summary(signal), [cardsApi]), enabled: active, intervalMs: 20_000, staleAfterMs: 45_000, pauseWhenHidden: true });
  const workHistoryResource = usePollingResource<WorkHistoryResponse>({ fetcher: useCallback((signal: AbortSignal) => api.get<WorkHistoryResponse>("/api/work/history?limit=4&offset=0", { signal }), [api]), enabled: active, intervalMs: 15_000, staleAfterMs: 30_000, pauseWhenHidden: true });
  if (!data) return <Empty text="灵机正在连接本机服务…" />;
  const d = data as Record<string, unknown>; const health = (d.health ?? {}) as Record<string, unknown>; const runtime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const runtimeState = health.status ?? runtime.state; const sourceSnapshot = sourceResource.data; const pending = pendingActionsFrom(pendingResource.data); const pendingUnavailable = Boolean(pendingResource.error || pendingResource.stale || pending === null); const cards = cardSummaryResource.data; const workItems = workHistoryResource.data?.items ?? []; const currentSources = sourceSnapshot?.sources.filter((item) => item.state === "current").map(ownerSourceName) ?? []; const latest = sourceSnapshot?.summary?.latest; const note = periodicReconciliationNotice(sourceSnapshot?.runtime); const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? String(value) : "—";

  return <div className="stack overview-page owner-observe-page">
    <section className={`overview-hero overview-hero-${stateTone(runtimeState)}`}><div className="overview-hero-main"><div className="overview-title-line"><span className="overview-status-mark" aria-hidden="true" /><h2>{stateLabel(runtimeState)}</h2></div><p>灵机正在自动扫描、整理并更新你的长期记忆，你只需要在这里查看成果。</p></div><div className="overview-live-summary"><strong>{pendingUnavailable ? "正在确认待办" : pending?.length ? "有一件事需要你决定" : "目前不需要你处理"}</strong><small>{pendingUnavailable ? "灵机仍会继续自动工作" : pending?.length ? display(pending[0]?.description) : "扫描和整理会自动进行"}</small></div></section>
    {pendingUnavailable && <Notice kind="warning">待办正在自动确认，当前不把未读取当作“没有待办”。</Notice>}{sourceResource.error && <Notice kind="warning">来源状态正在自动刷新，灵机不会因此停止记忆。</Notice>}{note && <Notice kind="info">{note}</Notice>}
    <section className="outcome-section"><div className="section-heading"><div><span className="section-kicker">最近自动成果</span><h3>灵机刚刚替你做了什么</h3></div><span className="section-caption">自动更新</span></div>{workHistoryResource.error && !workItems.length ? <p className="outcome-empty">正在读取最近成果…</p> : workItems.length ? <div className="outcome-list">{workItems.slice(0, 4).map((item, index) => <article className="outcome-item" key={item.work?.work_id ?? index}><span className="outcome-dot" /><div><strong>{formatWorkFactTitle(item.work?.title) || "灵机完成了一项记忆整理"}</strong><p>{item.outcome ? formatWorkFactResult(item) : display(item.summary?.result, "已完成自动处理")}</p><small>{formatTime(item.summary?.time ?? item.work?.updated_at)}</small></div></article>)}</div> : <p className="outcome-empty">灵机还没有形成可展示的成果，首次扫描完成后会出现在这里。</p>}</section>
    <section className="outcome-section memory-proof-section"><div className="section-heading"><div><span className="section-kicker">当前记忆</span><h3>灵机现在替你记住了什么</h3></div><span className="section-caption">只统计仍然有效的内容</span></div><div className="proof-grid"><div><strong>{number(cards?.cards)}</strong><span>件当前记忆</span></div><div><strong>{number(cards?.conversations)}</strong><span>段已接管对话</span></div><div><strong>{number(cards?.messages)}</strong><span>条原始消息</span></div><div><strong>{number(cards?.permanent)}</strong><span>件长期记忆</span></div></div><p className="proof-note">当前记忆卡片和长期记忆只统计仍然有效的内容；已接管对话与原始消息统计全部导入规模。{currentSources.length ? ` 来源：${currentSources.join("、")}。` : " 灵机还没有完成来源接管。"} {cards?.vectorized != null ? `其中 ${cards.vectorized} 件已准备语义检索。` : "语义检索状态会在后台自动更新。"}</p></section>
    <CurrentWorkPanel api={api} active={active} />
    <section className="outcome-section"><div className="section-heading"><div><span className="section-kicker">最近检查</span><h3>自动接管进度</h3></div></div><p className="outcome-highlight">{latestCheckSummary(latest)}</p><p className="outcome-muted">{latest ? `来源：${latest.source_id ? (sourceSnapshot?.sources.find((item) => item.source_id === latest.source_id)?.display_name ?? "已授权来源") : "已授权来源"}。` : "灵机会自动发现支持的记录来源。"}</p></section>
  </div>;
}
