import DataTable from "../components/DataTable";
import { Empty, Metric, Panel, bytes } from "../components/ui";
import type { Row } from "../types";

export default function OverviewPage({ data, refresh }: { data: Row | null; refresh: () => Promise<void> }) {
  if (!data) return <Empty text="连接服务后显示总览。" />;
  const health = data.health ?? {};
  const queue = data.queue?.stats ?? {};
  const storage = data.storage?.totals ?? {};
  const checks: Row[] = health.checks ?? [];
  const healthy = health.status === "healthy";
  return (
    <div className="stack">
      <div className="toolbar"><button className="button secondary" onClick={() => void refresh()}>立即刷新</button></div>
      <div className="metric-grid">
        <Metric title="系统状态" value={healthy ? "正常" : health.status || "未知"} detail={`${health.error_count || 0} 错误 / ${health.warning_count || 0} 警告`} tone={healthy ? "good" : "warn"} />
        <Metric title="待处理任务" value={String(queue.pending || 0)} detail={`运行中 ${queue.running || 0}`} />
        <Metric title="灵机占用" value={bytes(storage.bytes)} detail={`${storage.files || 0} 个文件`} />
        <Metric title="磁盘剩余" value={bytes(storage.disk_free_bytes)} detail={`${storage.disk_free_percent || 0}%`} tone={data.storage?.alerts?.below_minimum_free ? "bad" : "good"} />
      </div>
      <div className="two-column">
        <Panel title="健康检查"><div className="list">{checks.map((check) => <div className="list-row" key={check.name}><span className={`pill ${check.status}`}>{check.status}</span><div><strong>{check.name}</strong><small>{check.message}</small></div></div>)}</div></Panel>
        <Panel title="本地 Provider"><div className="list">{Object.entries(data.providers ?? {}).map(([name, value]) => { const provider = value as Row; return <div className="list-row" key={name}><span className={provider.available ? "status-dot online" : "status-dot"} /><div><strong>{name}</strong><small>{provider.available ? `可用 · ${provider.capability}` : `未安装 · ${provider.optional_requirements}`}</small></div></div>; })}</div></Panel>
      </div>
      <Panel title="定时任务"><DataTable headers={["任务", "状态", "下次运行", "错误"]} rows={(data.scheduler ?? []).map((job: Row) => [job.name, job.status, job.next_run_at, job.last_error || "-"])} /></Panel>
    </div>
  );
}
