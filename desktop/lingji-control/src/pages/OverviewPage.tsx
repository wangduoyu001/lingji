import DataTable from "../components/DataTable";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Metric, Notice, Panel, bytes } from "../components/ui";
import type { LingJiApi } from "../api";
import type { Row } from "../types";

const display = (value: unknown, suffix = "") =>
  value === null || value === undefined || value === "" ? "未知" : `${String(value)}${suffix}`;

const stateTone = (value: unknown): "good" | "warn" | "bad" | undefined => {
  const state = String(value ?? "").toLowerCase();
  if (["healthy", "ready", "available", "ok"].includes(state)) return "good";
  if (["degraded", "warning", "busy", "configuration_required", "stale"].includes(state)) return "warn";
  if (["failed", "error", "unavailable", "blocked"].includes(state)) return "bad";
  return undefined;
};

export default function OverviewPage({ data, refresh, api, active }: { data: Row | null; refresh: () => Promise<void>; api: LingJiApi; active: boolean }) {
  if (!data) return <Empty text="连接服务后显示总览。" />;
  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queue = ((d.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const storageRoot = (d.storage ?? {}) as Record<string, unknown>;
  const storage = (storageRoot.totals ?? {}) as Record<string, unknown>;
  const storageAlerts = (storageRoot.alerts ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const memory = (memoryRuntime.memory ?? d.memory_stats ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? d.vector_status ?? {}) as Record<string, unknown>;
  const embedding = (memoryRuntime.embedding ?? d.embedding_status ?? {}) as Record<string, unknown>;
  const hardware = (d.hardware ?? {}) as Record<string, unknown>;
  const computePolicy = (hardware.compute_policy ?? {}) as Record<string, unknown>;
  const checks = (((d.health as Record<string, unknown> | undefined)?.checks ?? []) as Row[]);
  const providers = (d.providers ?? {}) as Record<string, unknown>;
  const scheduler = (d.scheduler ?? []) as Array<Record<string, unknown>>;
  const runtimeState = memoryRuntime.state ?? health.status;
  const stale = Boolean(memoryRuntime.stale);

  return <div className="stack">
    <div className="toolbar">
      <button className="button secondary" onClick={() => void refresh()}>立即刷新</button>
      <span>工作区 {display(memoryRuntime.workspace)}</span>
      <span>数据源 {display(memoryRuntime.source)}</span>
      <span>状态时间 {display(memoryRuntime.as_of)}</span>
    </div>
    {stale && <Notice kind="warning">当前记忆和向量统计来自旧快照，不能当成实时状态。</Notice>}
    <CurrentWorkPanel api={api} active={active} />

    <div className="metric-grid">
      <Metric title="系统状态" value={display(runtimeState)} detail={`${display(health.error_count)} 错误 / ${display(health.warning_count)} 警告`} tone={stateTone(runtimeState)} />
      <Metric title="待处理任务" value={display(queue.pending)} detail={`运行中 ${display(queue.running)} · 重试 ${display(queue.retrying)}`} tone={Number(queue.failed ?? 0) > 0 ? "warn" : undefined} />
      <Metric title="记忆文档" value={display(memory.documents)} detail={`分块 ${display(memory.chunks)} · 修订 ${display(memory.revision)}`} tone={stateTone(memory.state)} />
      <Metric title="向量索引" value={display(vector.vectors)} detail={`${display(vector.state)} · 维度 ${display(vector.dimension)}`} tone={vector.rebuild_required ? "bad" : stateTone(vector.state)} />
    </div>

    <div className="metric-grid">
      <Metric title="Embedding" value={display(embedding.active_model ?? embedding.configured_model)} detail={display(embedding.state)} tone={stateTone(embedding.state)} />
      <Metric title="算力模式" value={display(computePolicy.requested_mode ?? computePolicy.mode)} detail={`设备 ${display(computePolicy.selected_device ?? computePolicy.device)}`} tone={stateTone(computePolicy.state)} />
      <Metric title="灵机占用" value={storage.bytes == null ? "未知" : bytes(Number(storage.bytes))} detail={`${display(storage.files)} 个文件`} />
      <Metric title="磁盘剩余" value={storage.disk_free_bytes == null ? "未知" : bytes(Number(storage.disk_free_bytes))} detail={`${display(storage.disk_free_percent, "%")}`} tone={storageAlerts.below_minimum_free ? "bad" : "good"} />
    </div>

    <div className="two-column">
      <Panel title="健康检查">
        {checks.length ? <div className="list">{checks.map((check) => <div className="list-row" key={String(check.name)}><span className={`pill ${String(check.status ?? "")}`}>{String(check.status ?? "未知")}</span><div><strong>{String(check.name ?? "未知")}</strong><small>{String(check.message ?? "")}</small></div></div>)}</div> : <Empty text="没有健康检查结果。" />}
      </Panel>
      <Panel title="本地 Provider">
        {Object.keys(providers).length ? <div className="list">{Object.entries(providers).map(([name, raw]) => {
          const provider = raw as Row;
          const state = provider.state ?? (provider.available === true ? "available" : provider.available === false ? "unavailable" : "unknown");
          return <div className="list-row" key={name}><span className={`status-dot ${state === "available" || state === "healthy" ? "online" : ""}`} /><div><strong>{name}</strong><small>{display(state)}{provider.capability ? ` · ${String(provider.capability)}` : ""}</small></div></div>;
        })}</div> : <Empty text="Provider 状态不可用。" />}
      </Panel>
    </div>

    <Panel title="定时任务">
      <DataTable headers={["任务", "状态", "下次运行", "错误"]} rows={scheduler.map((job) => [job.name, job.status, job.next_run_at, job.last_error || "-"] as React.ReactNode[])} />
    </Panel>
  </div>;
}
