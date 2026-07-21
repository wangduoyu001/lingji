import DataTable from "../components/DataTable";
import { Empty, Metric, Panel, bytes } from "../components/ui";
import type { Row } from "../types";

export default function OverviewPage({ data, refresh }: { data: Row | null; refresh: () => Promise<void> }) {
  if (!data) return <Empty text="连接服务后显示总览。" />;
  const d = data as any;
  const health: any = d.health ?? {};
  const queue: any = d.queue?.stats ?? {};
  const storage: any = d.storage?.totals ?? {};
  const checks: Row[] = (d.health?.checks ?? []) as Row[];
  const healthy = health.status === "healthy";
  return (
    <div className="stack">
      <div className="toolbar"><button className="button secondary" onClick={() => void refresh()}>立即刷新</button></div>
      <div className="metric-grid">
        <Metric title="系统状态" value={healthy ? "正常" : String(health.status ?? "未知")} detail={`${health.error_count || 0} 错误 / ${health.warning_count || 0} 警告`} tone={healthy ? "good" : "warn"} />
        <Metric title="待处理任务" value={String(queue.pending || 0)} detail={`运行中 ${queue.running || 0}`} />
        <Metric title="灵机占用" value={bytes(storage.bytes)} detail={`${storage.files || 0} 个文件`} />
        <Metric title="磁盘剩余" value={bytes(storage.disk_free_bytes)} detail={`${storage.disk_free_percent || 0}%`} tone={d.storage?.alerts?.below_minimum_free ? "bad" : "good"} />
      </div>
      <div className="two-column">
        <Panel title="健康检查"><div className="list">{checks.map((check) => <div className="list-row" key={check.name as React.Key}><span className={`pill ${String(check.status ?? "")}`}>{String(check.status ?? "")}</span><div><strong>{String(check.name ?? "")}</strong><small>{String(check.message ?? "")}</small></div></div>)}</div></Panel>
        <Panel title="本地 Provider"><div className="list">{Object.entries(d.providers ?? {}).map(([name, value]) => { const provider = value as Row; return <div className="list-row" key={name}><span className={provider.available ? "status-dot online" : "status-dot"} /><div><strong>{name}</strong><small>{provider.available ? `可用 · ${String(provider.capability ?? "")}` : `未安装 · ${String(provider.optional_requirements ?? "")}`}</small></div></div>; })}</div></Panel>
      </div>
      <Panel title="定时任务"><DataTable headers={["任务", "状态", "下次运行", "错误"]} rows={(d.scheduler ?? []).map((job: any) => [job.name, job.status, job.next_run_at, job.last_error || "-"] as React.ReactNode[])} /></Panel>
    </div>
  );
}
