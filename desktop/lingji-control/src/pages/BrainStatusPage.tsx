import { useCallback } from "react";
import { Empty, Metric } from "../components/ui";
import DataTable from "../components/DataTable";
import type { LingJiApi } from "../api";
import { normalizeBrainStatus, type BrainStatusSummary } from "../contracts/brainStatus";
import { usePollingResource } from "../hooks/usePollingResource";

const gibibytes = (value: number | null | undefined): string | null =>
  typeof value === "number" ? (value / 1073741824).toFixed(1) : null;

export default function BrainStatusPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const fetchStatus = useCallback(
    async (signal: AbortSignal): Promise<BrainStatusSummary> =>
      normalizeBrainStatus(await api.get<unknown>("/api/brain/status", { signal })),
    [api],
  );
  const resource = usePollingResource({
    fetcher: fetchStatus,
    enabled: active,
    intervalMs: 5_000,
    staleAfterMs: 15_000,
    pauseWhenHidden: true,
  });

  if (!active) return <Empty text="连接服务后显示脑状态看板。" />;
  if (resource.loading && !resource.data) return <Empty text="加载中..." />;
  if (resource.error && !resource.data) return <div className="notice notice-error">{resource.error.message}</div>;

  const data = resource.data;
  const gpu = data?.gpus?.[0];
  const freeGb = gibibytes(gpu?.free_vram_bytes);
  const totalGb = gibibytes(gpu?.total_vram_bytes);
  const utilization = gpu?.utilization_percent;
  const gpuStatus = gpu?.status || (gpu ? "unknown" : null);

  return (
    <div className="stack">
      <div className="toolbar">
        <button className="button secondary" disabled={resource.refreshing} onClick={() => void resource.refresh()}>
          {resource.refreshing ? "刷新中..." : "刷新"}
        </button>
        <span>状态: {data?.processing_status || "未知"}</span>
        <span>系统: {data?.system_status || "未知"}</span>
        {resource.stale && <span className="notice">数据已过期</span>}
        {resource.error && data && <span className="notice notice-error">刷新失败：{resource.error.message}</span>}
      </div>
      <div className="metric-grid">
        <Metric title="记忆数量" value={data?.memory_count === null || data?.memory_count === undefined ? "未知" : String(data.memory_count)} detail={`向量 ${data?.vector_count === null || data?.vector_count === undefined ? "未知" : data.vector_count}`} />
        <Metric title="对话模型" value={data?.chat_model || "未知"} detail={`嵌入 ${data?.embed_model || "未知"}`} />
        <Metric title="已安装模型" value={data?.installed_models === null || data?.installed_models === undefined ? "未知" : String(data.installed_models)} detail={data?.cuda_version ? `CUDA ${data.cuda_version}` : "CUDA 未知"} />
        <Metric title="GPU 显存" value={freeGb === null ? "未知" : `${freeGb} GB 空闲`} detail={gpu ? `${gpu.name || "未知 GPU"} / ${totalGb ?? "未知"} GB` : "未发现 GPU 状态"} />
      </div>
      <div className="two-column">
        <div className="panel">
          <div className="panel-title">GPU 详情</div>
          {gpu ? (
            <div className="list">
              <div className="list-row">
                <div>
                  <strong>{gpu.name || "未知 GPU"}</strong>
                  <small>利用率 {utilization === null || utilization === undefined ? "未知" : `${utilization}%`} · 状态 {gpuStatus}</small>
                </div>
              </div>
            </div>
          ) : <Empty text="GPU 状态不可用" />}
        </div>
        <div className="panel">
          <div className="panel-title">最近任务</div>
          {data?.recent_tasks?.length ? (
            <DataTable
              headers={["任务", "状态", "时间"]}
              rows={data.recent_tasks.map((task) => [
                task.task_id || task.job_id || "未知任务",
                task.status || "未知",
                String(task.created_at ?? "").slice(0, 16) || "-",
              ])}
            />
          ) : <Empty text="无待处理任务" />}
        </div>
      </div>
    </div>
  );
}
