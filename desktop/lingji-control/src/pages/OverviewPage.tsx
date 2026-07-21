import DataTable from "../components/DataTable";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Metric, Panel, bytes } from "../components/ui";
import type { LingJiApi } from "../api";
import type { Row } from "../types";

export default function OverviewPage({ data, refresh, api, active }: { data: Row | null; refresh: () => Promise<void>; api: LingJiApi; active: boolean }) {
  if (!data) return <Empty text="连接服务后显示总览。" />;
  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queue = ((d.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const storage = ((d.storage as Record<string, unknown> | undefined)?.totals ?? {}) as Record<string, unknown>;
  const checks = (((d.health as Record<string, unknown> | undefined)?.checks ?? []) as Row[]);
  const healthy = health.status === "healthy";
  const providers = (d.providers ?? {}) as Record<string, unknown>;
  const scheduler = (d.scheduler ?? []) as Array<Record<string, unknown>>;
  return <div className="stack">
    <div className="toolbar"><button className="button secondary" onClick={() => void refresh()}>立即刷新</button></div>
    <CurrentWorkPanel api={api} active={active} />
    <div className="metric-grid">
      <Metric title="系统状态" value={healthy ? "正常" : String(health.status ?? "未知")} detail={`${health.error_count ?? "未知"} 错误 / ${health.warning_count ?? "未知"} 警告`} tone={healthy ? "good" : "warn"} />
      <Metric title="待处理任务" value={queue.pending == null ? "未知" : String(queue.pending)} detail={`运行中 ${queue.running ?? "未知"}`} />
      <Metric title="灵机占用" value={bytes(storage.bytes)} detail={`${storage.files ?? "未知"} 个文件`} />
      <Metric title="磁盘剩余" value={bytes(storage.disk_free_bytes)} detail={`${storage.disk_free_percent ?? "未知"}%`} tone={(d.storage as Record<string, unknown> | undefined)?.alerts && ((d.storage as Record<string, unknown>).alerts as Record<string, unknown>).below_minimum_free ? "bad" : "good"} />
    </div>
    <div className="two-column">
      <Panel title="健康检查"><div className="list">{checks.map((check) => <div className="list-row" key={String(check.name)}><span className={`pill ${String(check.status ?? "")}`}>{String(check.status ?? "未知")}</span><div><strong>{String(check.name ?? "未知")}</strong><small>{String(check.message ?? "")}</small></div></div>)}</div></Panel>
      <Panel title="本地 Provider"><div className="list">{Object.entries(providers).map(([name, raw]) => { const provider = raw as Row; return <div className="list-row" key={name}><span className={provider.available ? "status-dot online" : "status-dot"} /><div><strong>{name}</strong><small>{provider.available ? `可用 · ${String(provider.capability ?? "")}` : `未安装 · ${String(provider.optional_requirements ?? "")}`}</small></div></div>; })}</div></Panel>
    </div>
    <Panel title="定时任务"><DataTable headers={["任务", "状态", "下次运行", "错误"]} rows={scheduler.map((job) => [job.name, job.status, job.next_run_at, job.last_error || "-"] as React.ReactNode[])} /></Panel>
  </div>;
}
