import { useEffect, useState } from "react";
import { Empty, Metric } from "../components/ui";
import DataTable from "../components/DataTable";
import type { LingJiApi } from "../api";
import type { Row } from "../types";

type BsData = {
  memory_count: number | null;
  memory_bytes: number | null;
  vector_count: number | null;
  chat_model: string;
  embed_model: string;
  installed_models: number;
  gpus: Array<{ gpu_id: string; name: string; total_vram_bytes: number; free_vram_bytes: number; utilization_percent?: number }>;
  compute_mode: string;
  cuda_version: string;
  recent_tasks: Array<{ job_id: string; state: string; task: string; created_at: string }>;
  processing_status: string;
  system_status: string;
};

export default function BrainStatusPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [data, setData] = useState<BsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchStatus = async () => {
    if (!active) return;
    setLoading(true);
    try {
      const result = await api.get<BsData>("/api/brain/status");
      setData(result);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void fetchStatus(); }, [active]);
  if (!active) return <Empty text="连接服务后显示脑状态看板。" />;
  if (loading && !data) return <Empty text="加载中..." />;
  if (error && !data) return <div className="notice notice-error">{error}</div>;

  const gpu = data?.gpus?.[0];
  const freeGb = gpu ? (gpu.free_vram_bytes / 1073741824).toFixed(1) : "N/A";
  const totalGb = gpu ? (gpu.total_vram_bytes / 1073741824).toFixed(1) : "N/A";

  return (
    <div className="stack">
      <div className="toolbar">
        <button className="button secondary" onClick={() => void fetchStatus()}>刷新</button>
        <span>状态: {data?.processing_status || "未知"}</span>
        <span>系统: {data?.system_status || "未知"}</span>
      </div>
      <div className="metric-grid">
        <Metric title="记忆数量" value={String(data?.memory_count ?? "-")} detail={`向量 ${data?.vector_count ?? "-"}`} />
        <Metric title="对话模型" value={data?.chat_model || "N/A"} detail={`嵌入 ${data?.embed_model || "N/A"}`} />
        <Metric title="已安装模型" value={String(data?.installed_models ?? "-")} detail={data?.cuda_version ? `CUDA ${data.cuda_version}` : "无 CUDA"} />
        <Metric title="GPU 显存" value={gpu ? `${freeGb} GB 空闲` : "N/A"} detail={gpu ? `${gpu.name} / ${totalGb} GB` : "无 GPU"} />
      </div>
      <div className="two-column">
        <div className="panel">
          <div className="panel-title">GPU 详情</div>
          {gpu ? (<div className="list"><div className="list-row"><div><strong>{gpu.name}</strong><small>利用率 {data?.gpus?.[0]?.utilization_percent ?? 0}%</small></div></div></div>) : <Empty text="无可用 GPU" />}
        </div>
        <div className="panel">
          <div className="panel-title">最近任务</div>
          {data?.recent_tasks?.length ? (
            <DataTable headers={["任务", "状态", "时间"]} rows={data.recent_tasks.map((t: any) => [t.task || t.job_id, t.state, String(t.created_at ?? "").slice(0, 16) || "-"])} />
          ) : <Empty text="无待处理任务" />}
        </div>
      </div>
    </div>
  );
}
