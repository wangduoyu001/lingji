import { useCallback, useMemo } from "react";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Metric, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { MemorySourcesApi, sourceStateLabel, scanStatusLabel, countLabel } from "./memorySourcesApi";
import type { MemorySourcesSnapshot } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId, Row } from "../types";
import { activeAuthorizedCount } from "./codexWorkspaceContract";

const display = (value: unknown, fallback = "尚未获得") => value === null || value === undefined || value === "" ? fallback : String(value);
const stateTone = (value: unknown): "good" | "warn" | "bad" | undefined => {
  const state = String(value ?? "").toLowerCase();
  if (["healthy", "ready", "available", "ok"].includes(state)) return "good";
  if (["degraded", "warning", "busy", "configuration_required", "stale"].includes(state)) return "warn";
  if (["failed", "error", "unavailable", "blocked"].includes(state)) return "bad";
  return undefined;
};
const stateLabel = (value: unknown) => ({ healthy: "运行正常", ready: "已就绪", degraded: "需要检查", failed: "运行失败", unavailable: "当前不可用", configuration_required: "需要配置", stale: "数据过期" } as Record<string, string>)[String(value ?? "")] ?? display(value);

export default function OverviewPage({ data, api, active, onNavigate }: { data: Row | null; api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]);
  const loadSources = useCallback(() => sourceApi.snapshot(), [sourceApi]);
  const sourceResource = usePollingResource<MemorySourcesSnapshot>({ fetcher: loadSources, enabled: active, intervalMs: 10_000, staleAfterMs: 30_000 });
  if (!data) return <Empty text="灵机核心连接后会自动显示运行状态。" />;
  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queue = ((d.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const memory = (memoryRuntime.memory ?? d.memory_stats ?? {}) as Record<string, unknown>;
  const runtimeState = memoryRuntime.state ?? health.status;
  const sourceSnapshot = sourceResource.data;
  const latest = sourceSnapshot?.summary?.latest;
  const latestSource = latest ? sourceSnapshot?.sources.find((item) => item.source_id === latest.source_id) : undefined;
  const pending = (d.pending_memory_count ?? d.pending_review_count) as unknown;
  const activeMemory = memory.active ?? memory.core_memories ?? memory.documents;
  const latestStatus = latestSource?.state ?? latest?.status;
  const run = latest as Record<string, unknown> | null;

  return <div className="stack overview-page observation-page">
    <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
      <div className="overview-hero-main"><span className="desktop-eyebrow">SYSTEM POSTURE</span><div className="overview-title-line"><h2>{stateLabel(runtimeState)}</h2><span className={`pill ${stateTone(runtimeState) === "good" ? "ok" : stateTone(runtimeState) === "bad" ? "error" : "warning"}`}>{display(runtimeState)}</span></div><p>灵机会自动检查来源、处理队列并保留可追溯的扫描结果。</p></div>
      <div className="observation-live-state"><span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} /><div><strong>{queue.running != null ? `${display(queue.running)} 个任务运行中` : "尚未获得"}</strong><small>状态每 10 秒自动更新</small></div></div>
    </section>
    {sourceResource.stale && <Notice kind="warning">来源状态来自上一次成功读取，正在刷新；请不要把过期状态当成当前状态。</Notice>}
    {sourceResource.error && <Notice kind="warning">来源状态暂时不可用：{sourceResource.error.message}。请打开“记忆来源”重试。</Notice>}
    <CurrentWorkPanel api={api} active={active} />
    <section className="attention-summary"><div><span className="desktop-eyebrow">OWNER ATTENTION</span><h3>需要你决定的事项以真实待办为准</h3><p>只有持久化工作事实要求主人确认时，灵机才会把事情交给你。</p></div><button className="button secondary" onClick={() => onNavigate("attention")}>查看待办</button></section>

    <section className="overview-section source-overview-card"><div className="overview-section-heading"><div><span className="desktop-eyebrow">MEMORY SOURCES</span><h3>灵机发现并接管了什么</h3></div><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看记忆来源</button></div>
      <div className="source-overview-copy"><div><strong>已发现</strong><span>{sourceSnapshot ? sourceSnapshot.discovered.map((item) => item.display_name).join("、") || "尚未发现" : "尚未获得"}</span></div><div><strong>已授权 / 当前</strong><span>{sourceSnapshot ? `${activeAuthorizedCount(sourceSnapshot.authorized)} 个已授权，${sourceSnapshot.sources.filter((item) => item.state === "current").length} 个已接管` : "尚未获得"}</span></div><div><strong>下一步</strong><span>{latestSource?.nextAction ?? "打开记忆来源查看授权和扫描下一步。"}</span></div></div>
    </section>

    <section className="overview-section"><div className="overview-section-heading"><div><span className="desktop-eyebrow">CURRENT ACTIVITY</span><h3>现在正在做什么</h3></div><small>{latestStatus ? (latestSource ? sourceStateLabel(latestStatus) : scanStatusLabel(String(latestStatus))) : "尚未获得"}</small></div><div className="metric-grid observation-metric-grid"><Metric title="当前活动" value={latestSource?.display_name ?? "尚未获得"} detail={latestSource ? `${latestSource.detail} · 进度 ${latestSource.latestScan?.progress ?? "尚未获得"}/${latestSource.latestScan?.total ?? "尚未获得"}` : "打开记忆来源查看"} tone={stateTone(latestStatus)} /><Metric title="本次新增" value={countLabel(run?.queued)} detail="后端未提供时显示尚未获得" /><Metric title="本次更新" value={countLabel(run?.updated)} detail="后端未提供时显示尚未获得" /><Metric title="本次跳过" value={countLabel(run?.skipped)} detail="后端未提供时显示尚未获得" /><Metric title="本次复用" value={countLabel(run?.reused)} detail="已有证据不会重复导入" /><Metric title="本次失败" value={countLabel(run?.failed)} detail={latest?.last_error ? String(latest.last_error) : "没有可确认的失败数量"} tone={latest?.last_error ? "bad" : undefined} /></div></section>

    <section className="overview-section"><div className="overview-section-heading"><div><span className="desktop-eyebrow">MEMORY POSTURE</span><h3>记忆现在是什么状态</h3></div><button className="button secondary" onClick={() => onNavigate("memory_review")}>查看记忆审核</button></div><div className="metric-grid observation-metric-grid"><Metric title="可用记忆" value={countLabel(activeMemory)} detail="来自现有记忆状态接口" /><Metric title="待主人确认" value={countLabel(pending)} detail="只有真实待办才需要你决定" tone={typeof pending === "number" && pending > 0 ? "warn" : undefined} /><Metric title="工作队列" value={queue.pending != null ? `${display(queue.pending)} 等待` : "尚未获得"} detail={queue.failed != null ? `失败 ${display(queue.failed)}` : "失败数量尚未获得"} tone={stateTone(queue.failed != null && Number(queue.failed) > 0 ? "failed" : undefined)} /><Metric title="数据新鲜度" value={memoryRuntime.stale ? "需要刷新" : memoryRuntime.as_of ? "最新状态" : "尚未获得"} detail={display(memoryRuntime.as_of)} tone={memoryRuntime.stale ? "warn" : undefined} /></div></section>
    <div className="overview-footer-actions"><button className="button secondary" onClick={() => onNavigate("activity")}>查看活动记录</button><button className="button secondary" onClick={() => onNavigate("diagnostics")}>打开高级诊断</button></div>
  </div>;
}
