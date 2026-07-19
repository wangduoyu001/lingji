import { useCallback, useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import { Empty, Metric, Notice, Panel, bytes } from "../components/ui";
import type { PageProps, Row } from "../types";

const MODE_LABELS: Record<string, string> = {
  auto: "自动选择",
  gpu_preferred: "GPU 优先",
  cpu_only: "仅使用 CPU",
};

export default function SystemComputePage({ api, active }: PageProps) {
  const [capabilities, setCapabilities] = useState<Row | null>(null);
  const [telemetry, setTelemetry] = useState<Row | null>(null);
  const [policy, setPolicy] = useState<Row | null>(null);
  const [mode, setMode] = useState("auto");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!active) return;
    try {
      const [nextCapabilities, nextTelemetry, nextPolicy] = await Promise.all([
        api.get<Row>("/api/hardware/capabilities"),
        api.get<Row>("/api/hardware/telemetry"),
        api.get<Row>("/api/compute/policy"),
      ]);
      setCapabilities(nextCapabilities);
      setTelemetry(nextTelemetry);
      setPolicy(nextPolicy);
      setMode(String(nextPolicy.requested_mode || "auto"));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);

  async function refresh() {
    if (!active) return;
    try {
      await api.post<Row>("/api/hardware/refresh", {});
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  async function saveMode() {
    setSaving(true);
    try {
      const next = await api.patch<Row>("/api/compute/policy", { mode });
      setPolicy(next);
      setMode(String(next.requested_mode));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  }

  if (!capabilities) return <Empty text="连接本机服务后显示硬件和算力状态。" />;

  const system = capabilities.system ?? {};
  const cpu = capabilities.cpu ?? {};
  const memory = capabilities.memory ?? {};
  const gpus: Row[] = capabilities.gpus ?? [];
  const disks: Row[] = capabilities.disks ?? [];
  const physicalDisks: Row[] = capabilities.physical_disks ?? [];
  const tools = capabilities.toolchains ?? {};

  return (
    <div className="stack">
      <Notice>
        本页显示真实检测结果。显卡存在只代表它可以成为候选加速器，不代表某个模型一定能运行；模型仍需依赖检测、加载测试和短基准。
      </Notice>
      {error && <Notice kind="error">{error}</Notice>}
      <div className="toolbar">
        <button className="button secondary" onClick={() => void refresh()} disabled={!active}>重新检测硬件</button>
        <span>最后检测：{String(capabilities.collected_at || "-")}</span>
      </div>

      <div className="metric-grid">
        <Metric title="操作系统" value={String(system.os_name || "未知")} detail={`${system.os_release || ""} · ${system.architecture || ""}`} />
        <Metric title="CPU" value={String(cpu.model || "未知")} detail={`${cpu.physical_cores ?? "?"} 核 / ${cpu.logical_threads ?? "?"} 线程`} />
        <Metric title="可用内存" value={memory.available_bytes == null ? "无法检测" : bytes(memory.available_bytes)} detail={`总计 ${memory.total_bytes == null ? "未知" : bytes(memory.total_bytes)}`} tone={memory.status === "available" ? "good" : "warn"} />
        <Metric title="GPU" value={gpus.length ? `${gpus.length} 块可用` : "未检测到"} detail={gpus[0]?.name || "基础功能继续使用 CPU"} tone={gpus.length ? "good" : "neutral"} />
      </div>

      <div className="two-column">
        <Panel title="全局算力模式">
          <div className="form-grid">
            <label>主人选择
              <select value={mode} onChange={(event) => setMode(event.target.value)}>
                {Object.entries(MODE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <button className="button primary" disabled={saving || mode === policy?.requested_mode} onClick={() => void saveMode()}>{saving ? "保存中…" : "保存算力模式"}</button>
          </div>
          {policy && <div className="list">
            <div className="list-row"><strong>当前候选设备</strong><small>{policy.candidate_device === "gpu" ? `${policy.gpu_name} · GPU ${policy.gpu_id}` : "CPU"}</small></div>
            <div className="list-row"><strong>降级原因</strong><small>{policy.fallback_reason || "无需降级"}</small></div>
            <div className="list-row"><strong>基础检索</strong><small>{policy.basic_retrieval_available ? "始终可用" : "异常"}</small></div>
            <div className="list-row"><strong>说明</strong><small>{policy.explanation}</small></div>
          </div>}
          <Notice kind="warning">监控频率、首选 GPU ID 和所有默认值在“设置 → 系统与算力”中可学习、修改和恢复默认。</Notice>
        </Panel>
        <Panel title="实时资源">
          <div className="metric-grid">
            <Metric title="CPU 负载" value={telemetry?.cpu_percent == null ? "无法检测" : `${telemetry.cpu_percent}%`} />
            <Metric title="内存负载" value={telemetry?.memory_percent == null ? "无法检测" : `${telemetry.memory_percent}%`} />
          </div>
          <small>采集源：{String(telemetry?.source || "-")} · 采集时间：{String(telemetry?.collected_at || "-")}</small>
        </Panel>
      </div>

      <Panel title="GPU 与 CUDA">
        <DataTable headers={["ID", "型号", "总显存", "空闲显存", "负载", "温度", "驱动"]} rows={gpus.map((gpu) => [gpu.gpu_id, gpu.name, bytes(gpu.total_vram_bytes), bytes(gpu.free_vram_bytes), `${gpu.utilization_percent}%`, `${gpu.temperature_c}°C`, gpu.driver_version])} />
        <small>CUDA 驱动：{capabilities.cuda?.driver_available ? "可用" : "不可用"} · Runtime：{capabilities.cuda?.runtime_version || "未检测到"}</small>
      </Panel>

      <Panel title="磁盘与介质">
        <DataTable headers={["挂载点", "文件系统", "介质", "总容量", "空闲", "只读", "检测源"]} rows={disks.map((disk) => [disk.mount, disk.filesystem, disk.media_type, bytes(disk.total_bytes), bytes(disk.free_bytes), disk.read_only ? "是" : "否", disk.source])} />
        {physicalDisks.length > 0 && <DataTable headers={["物理磁盘", "介质", "容量", "健康", "检测源"]} rows={physicalDisks.map((disk) => [disk.name, disk.media_type, bytes(disk.size_bytes), disk.health_status, disk.source])} />}
      </Panel>

      <Panel title="本地工具链">
        <DataTable headers={["工具", "状态", "版本或模型", "检测源", "错误"]} rows={Object.entries(tools).map(([name, value]) => {
          const tool = value as Row;
          const detail = name === "ollama" ? `${tool.model_count || 0} 个模型` : name === "qdrant" ? tool.status : tool.version || "-";
          return [name, tool.available ? "可用" : "不可用", detail, tool.source, tool.error || "-"];
        })} />
      </Panel>
    </div>
  );
}
