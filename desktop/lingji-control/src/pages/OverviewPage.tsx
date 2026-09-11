import { useCallback, useMemo } from "react";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import {
  loadModelHealthPanel,
  MemorySourcesApi,
  ownerSourceName,
  periodicReconciliationNotice,
  runningLabel,
  scanCountValue,
  sourceStateLabel,
} from "./memorySourcesApi";
import type { MemorySourcesSnapshot, ModelHealthPanel, ScanRun } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId, Row } from "../types";
import { pendingActionsFrom, type PendingActionsResponse } from "../contracts/workFact";
import { useObservabilityTasks, useTaskSteps } from "./WorkLedgerPage";
import { StepsFlow } from "./WorkLedgerPage";
import { redactAbsolutePaths } from "./ownerMemoryCardsTypes";
import { fetchHomePanels, projectServiceRows, projectVectorization, type ServiceRow, type VectorizationPanel } from "./servicesHealth";
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
  const modelHealth = usePollingResource<ModelHealthPanel>({ fetcher: useCallback(() => loadModelHealthPanel(api), [api]), enabled: active, intervalMs: 30_000, staleAfterMs: 120_000, pauseWhenHidden: true });
  const services = usePollingResource({ fetcher: useCallback(() => fetchHomePanels(api), [api]), enabled: active, intervalMs: 60_000, staleAfterMs: 180_000, pauseWhenHidden: true });
  const obsTasks = useObservabilityTasks(api, active);
  const latestScanId = obsTasks.data?.items?.[0]?.scan_id ?? null;
  const obsSteps = useTaskSteps(api, latestScanId, active);
  if (!data) return <Empty text="灵机正在连接本机服务…" />;
  const d = data as Record<string, unknown>; const health = (d.health ?? {}) as Record<string, unknown>; const runtime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const runtimeState = health.status ?? runtime.state; const sourceSnapshot = sourceResource.data; const pending = pendingActionsFrom(pendingResource.data); const pendingUnavailable = Boolean(pendingResource.error || pendingResource.stale || pending === null); const cards = cardSummaryResource.data; const internalTopicPattern = /<(environment_context|heartbeat|recommended_plugins|user_instructions|system_message|turn_context|app_context|ide_context|codex_delegation)|^#\s*Files mentioned by the user/i;
  const recentCards = (recentCardsResource.data?.items ?? [])
    .filter((item: OwnerMemoryCard) => String(item.freshness?.state ?? "") === "current")
    .filter((item: OwnerMemoryCard) => !internalTopicPattern.test(String(item.topic ?? "")))
    .slice(0, 6); const currentSources = sourceSnapshot?.sources.filter((item) => item.state === "current").map(ownerSourceName) ?? []; const latest = sourceSnapshot?.summary?.latest; const note = periodicReconciliationNotice(sourceSnapshot?.runtime); const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? String(value) : "—";
  const latestCheckTime = latest?.updated_at ? formatTime(latest.updated_at) : "尚未获得";
  const hasTodos = !pendingUnavailable && Boolean(pending?.length);

  return <div className="stack overview-page owner-observe-page">
    <section className={`overview-hero overview-hero-${stateTone(runtimeState)}`}><div className="overview-hero-main"><div className="overview-title-line"><span className="overview-status-mark" aria-hidden="true" /><h2>{stateLabel(runtimeState)}</h2></div><p>灵机正在自动扫描、整理并更新你的长期记忆，你只需要在这里查看成果。</p></div><div className="overview-live-summary"><strong>{pendingUnavailable ? "正在确认待办" : hasTodos ? "有一件事需要你决定" : "目前不需要你处理"}</strong><small>{pendingUnavailable ? "灵机仍会继续自动工作" : hasTodos ? display(pending?.[0]?.description) : "扫描和整理会自动进行"}</small>{hasTodos && <button className="button primary overview-attention-link" onClick={() => onNavigate("attention")}>处理待办</button>}</div></section>
    {pendingUnavailable && <Notice kind="warning">待办正在自动确认，当前不把未读取当作“没有待办”。</Notice>}{sourceResource.error && <Notice kind="warning">来源状态正在自动刷新，灵机不会因此停止记忆。</Notice>}{note && <Notice kind="info">{note}</Notice>}
    <HomeFactsBoard snapshot={sourceSnapshot} modelHealth={modelHealth.data} loading={!sourceSnapshot} onNavigate={onNavigate} />
    <MonitorBoard tasks={obsTasks.data} steps={obsSteps.data?.steps ?? null} />
    <ServicesBoard services={services.data} />
    <section className="outcome-section recent-memory-section"><div className="section-heading"><div><span className="section-kicker">最近记住的内容</span><h3>灵机最近替你记住了什么</h3></div><span className="section-caption">自动更新</span></div>{recentCards.length ? <div className="recent-memory-list">{recentCards.map((card) => { const conclusion = ownerFacingConclusion(card); return <article className="recent-memory-item" key={card.memory_id}><strong>{display(redactAbsolutePaths(card.topic), "未命名记忆")}</strong><p>{redactAbsolutePaths(conclusion.text)}</p><small>来源：{display(card.source?.label)}</small></article>; })}</div> : <p className="outcome-empty">灵机还没有形成具体记忆，完成一次来源检查后会出现在这里。</p>}</section>
    <section className="outcome-section takeover-summary-section"><div className="section-heading"><div><span className="section-kicker">最近自动接管成果</span><h3>接管了多少记录</h3></div><span className="section-caption">自动统计</span></div><div className="takeover-stats"><div><strong>{number(cards?.conversations)}</strong><span>已接管对话</span></div><div><strong>{number(cards?.messages)}</strong><span>已导入消息</span></div><div><strong>{number(cards?.permanent ?? 0)}</strong><span>已入永久记忆</span></div><div><strong>{latestCheckTime}</strong><span>最近检查时间</span></div></div><p className="proof-note latest-check-note">{latestCheckSummary(latest)}</p><p className="proof-note vector-note">当前记忆和长期记忆只统计仍然有效的内容；已接管对话与消息统计全部导入规模。{cards?.vectors != null ? `其中 ${cards.vectors} 条消息已建立语义检索索引，可按意思搜索。` : "语义检索状态会在后台自动更新。"}</p></section>
    <CurrentWorkPanel api={api} active={active} />
  </div>;
}

function HomeFactsBoard({ snapshot, modelHealth, loading, onNavigate }: { snapshot: MemorySourcesSnapshot | null | undefined; modelHealth: ModelHealthPanel | null; loading: boolean; onNavigate: (page: PageId) => void }) {
  const sources = snapshot?.sources ?? [];
  const apps = snapshot?.apps ?? [];
  const runningApps = apps.filter((row) => row.running === true).map((row) => row.display_name);
  const models = modelHealth?.models ?? null;
  const runningModels = (models ?? []).filter((model) => model.running === true).map((model) => model.display_name);
  const verified = (models ?? []).filter((model) => model.compatibility_status === "verified").length;
  const unverified = (models ?? []).filter((model) => model.compatibility_status != null && model.compatibility_status !== "verified").length;
  const waitingInboxes = (snapshot?.inboxes ?? []).filter((row) => (row.file_count ?? 0) > 0);
  const inboxLine = waitingInboxes.length
    ? waitingInboxes.map((row) => `${row.purpose}有 ${row.file_count} 个文件待处理`).join("；")
    : (snapshot?.inboxes ?? []).length
      ? "官方导出接收文件夹已就绪，暂无待处理文件。"
      : "接收文件夹状态尚未获得。";
  return (
    <section className="outcome-section home-facts-board" aria-label="现在的事实">
      <div className="section-heading"><div><span className="section-kicker">现在的事实</span><h3>打开就能看到的全部准确数据</h3></div><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看全部来源与明细</button></div>
      {loading ? (
        <p className="outcome-empty" aria-busy="true">正在读取本机事实…</p>
      ) : (
        <div className="home-facts-grid">
          <div className="home-fact-group">
            <h4>记忆来源（{sources.length ? `${sources.length} 个` : "尚未获得"}）</h4>
            {sources.length === 0 ? <p className="home-fact-line">暂时没有可连接的记录来源。灵机会自动重试。</p> : sources.map((item) => {
              const rootTail = String(item.root ?? "").replace(/\/+$/, "").split("/").filter(Boolean).slice(-1)[0];
              return (
                <p className="home-fact-line" key={`${item.kind}:${item.root}`}>
                  <span className="pill neutral">{sourceStateLabel(item.state)}</span>
                  <strong>{ownerSourceName(item)}</strong>
                  {rootTail && <small>· {rootTail}</small>}
                  <small>最近检查：{item.latestScan?.updated_at ? new Date(String(item.latestScan.updated_at)).toLocaleString() : "尚未获得"}</small>
                </p>
              );
            })}
          </div>
          <div className="home-fact-group">
            <h4>本机 AI 软件（{apps.length ? `发现 ${apps.length} 个` : "尚未获得"}）</h4>
            <p className="home-fact-line">{apps.length ? <><span className="pill ok">正在运行：{runningApps.length ? runningApps.join("、") : "无"}</span><small>其余 {Math.max(apps.length - runningApps.length, 0)} 个未运行</small></> : "尚未在本机发现 AI 软件。"}</p>
          </div>
          <div className="home-fact-group">
            <h4>模型状态</h4>
            {!models ? <p className="home-fact-line">模型清单尚未获得。灵机会自动重试。</p> : (
              <p className="home-fact-line">
                <span className={`pill ${runningModels.length ? "ok" : "neutral"}`}>{runningModels.length ? `正在运行：${runningModels.join("、")}` : "暂无运行中的模型"}</span>
                <small>兼容已验证 {verified} · 待验证 {unverified}（待验证只影响速度评估，不影响使用）</small>
              </p>
            )}
          </div>
          <div className="home-fact-group">
            <h4>官方导出接收文件夹</h4>
            <p className="home-fact-line"><small>{inboxLine}</small></p>
          </div>
        </div>
      )}
    </section>
  );
}

function ServicesBoard({ services }: { services: { health: Record<string, unknown> | null; overview: Record<string, unknown> | null; importedMessages: number | null } | null }) {
  const rows = projectServiceRows(services?.health ?? null);
  const vectorization: VectorizationPanel | null = services ? projectVectorization(services.overview, services.health) : null;
  const problems = rows.filter((row) => row.status !== "ok");
  return (
    <section className="outcome-section services-board" aria-label="本地服务与向量化">
      <div className="section-heading"><div><span className="section-kicker">灵机的助手们</span><h3>本地服务与向量化状态</h3></div><span className="section-caption">{problems.length ? `${problems.length} 项需要留意` : "全部正常"}</span></div>
      {!services ? (
        <p className="outcome-empty" aria-busy="true">正在读取服务状态…</p>
      ) : (
        <>
          <div className="services-grid">
            {rows.map((row) => (
              <article key={row.key} className={`service-card service-${row.status}`}>
                <header><strong>{row.label}</strong><span className={`pill ${row.status === "ok" ? "ok" : row.status === "warning" ? "warning" : row.status === "error" ? "bad" : "neutral"}`}>{row.statusText}</span></header>
                <p>{row.plain}</p>
                {row.status !== "ok" && row.impact && <small>影响：{row.impact}</small>}
                {row.status !== "ok" && row.fix && <small>怎么做：{row.fix}</small>}
              </article>
            ))}
          </div>
          {vectorization && (
            <div className="vectorization-card">
              <header><strong>按意思搜索（向量化）</strong><span className={`pill ${vectorization.embeddingAvailable ? "ok" : "warning"}`}>{vectorization.embeddingAvailable ? "已启用" : "尚未启用"}</span></header>
              <p>向量化就是“把文字变成机器能理解的意思”，这样你可以用“发布计划”搜到聊过排期的对话，哪怕原文里没有这几个字。</p>
              {!vectorization.embeddingAvailable && vectorization.ollamaService && (
                <small>现在没启用，原因：{vectorization.ollamaService.statusText === "需要留意" || vectorization.ollamaService.statusText === "不可用" ? "本地 AI 服务 Ollama 没有运行。" : "向量化服务尚未配置。"} {vectorization.ollamaService.fix}</small>
              )}
              {vectorization.vectorizedMessages != null && <small>已向量化 {vectorization.vectorizedMessages} 条。</small>}
              <small>放心：向量化在本机完成，对话内容不会上传到任何外部服务。</small>
            </div>
          )}
          <p className="services-note">灵机目前不依赖任何外部云服务：记忆、搜索、向量化全部在本机完成。</p>
        </>
      )}
    </section>
  );
}

function MonitorBoard({ tasks, steps }: { tasks: { items?: Array<{ scan_id: string; status: string; total?: number | null; queued_count?: number | null; reused_count?: number | null; updated_at?: string | null; job_failed?: number | null }> } | null; steps: Parameters<typeof StepsFlow>[0]["steps"] }) {
  const latest = tasks?.items?.[0] ?? null;
  return (
    <section className="outcome-section monitor-board" aria-label="实时监控">
      <div className="section-heading"><div><span className="section-kicker">实时监控</span><h3>流水线与最近任务</h3></div><span className="section-caption">{latest ? `最近任务：${latest.status === "completed" ? "已完成" : latest.status === "running" ? "进行中" : latest.status}` : "暂无任务"}</span></div>
      <StepsFlow steps={steps} />
      {latest && (
        <div className="monitor-latest">
          <div className="monitor-stat"><strong>{latest.total == null ? "尚未获得" : latest.total}</strong><span>检查文件</span></div>
          <div className="monitor-stat"><strong>{latest.queued_count == null ? "尚未获得" : latest.queued_count}</strong><span>新入库</span></div>
          <div className="monitor-stat"><strong>{latest.reused_count == null ? "尚未获得" : latest.reused_count}</strong><span>去重复用</span></div>
          <div className="monitor-stat"><strong>{latest.job_failed == null ? "尚未获得" : latest.job_failed}</strong><span>筛选拒绝</span></div>
        </div>
      )}
    </section>
  );
}
