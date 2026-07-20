import { useCallback, useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import { Empty, Metric, Notice, Panel, bytes } from "../components/ui";
import type { PageProps, Row } from "../types";

function text(value: unknown, fallback = "-"): string {
  return value === undefined || value === null || value === "" ? fallback : String(value);
}

export default function ModelsPage({ api, active }: PageProps) {
  const [registry, setRegistry] = useState<Row | null>(null);
  const [inventory, setInventory] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!active) return;
    try {
      const [nextRegistry, nextInventory] = await Promise.all([
        api.get<Row>("/api/models/registry"),
        api.get<Row>("/api/models"),
      ]);
      setRegistry(nextRegistry);
      setInventory(nextInventory);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);

  async function refresh() {
    if (!active) return;
    setRefreshing(true);
    try {
      setInventory(await api.post<Row>("/api/models/refresh", {}));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setRefreshing(false);
    }
  }

  if (!inventory || !registry) return <Empty text="连接本机服务后读取模型清单。" />;

  const summary = inventory.summary ?? {};
  const models: Row[] = inventory.models ?? [];
  const providers: Row[] = inventory.providers ?? [];
  const assignments: Row[] = inventory.assignments ?? [];
  const capabilities = registry.capabilities ?? {};

  return (
    <div className="stack">
      <Notice>
        当前页面是只读清单。安装、正在运行和兼容性是三个独立状态。只有完成依赖检测、实际加载和短基准后，模型才可以得到兼容结论。
      </Notice>
      <Notice kind="warning">
        下载、删除、测速和正式默认模型切换尚未启用。它们必须先具备空间检查、影响预览、任务进度、回滚和人工确认，不能因为按钮长得像功能就假装功能已经存在。
      </Notice>
      {error && <Notice kind="error">{error}</Notice>}
      <div className="toolbar">
        <button className="button secondary" disabled={!active || refreshing} onClick={() => void refresh()}>{refreshing ? "正在读取…" : "刷新模型清单"}</button>
        <span>最后读取：{text(inventory.collected_at)}</span>
      </div>

      <div className="metric-grid">
        <Metric title="已安装模型" value={text(summary.installed_models, "0")} />
        <Metric title="正在运行" value={text(summary.running_models, "0")} />
        <Metric title="未完成兼容测试" value={text(summary.unverified_models, "0")} tone={summary.unverified_models ? "warn" : "good"} />
        <Metric title="缺失的配置模型" value={text(summary.missing_assignments, "0")} tone={summary.missing_assignments ? "bad" : "good"} />
      </div>

      <Panel title="模型用途">
        <DataTable headers={["用途", "说明"]} rows={Object.values(capabilities).map((item) => {
          const capability = item as Row;
          return [capability.label, capability.description];
        })} />
      </Panel>

      <Panel title="Ollama 本地模型">
        <DataTable
          headers={["模型", "用途", "安装", "运行", "大小", "参数", "量化", "预计 RAM", "预计显存", "当前设备证据", "兼容性", "最近测速", "当前任务", "错误"]}
          rows={models.map((model) => [
            model.display_name,
            (model.capabilities ?? []).map((value: string) => capabilities[value]?.label || value).join("、") || "官方未声明",
            model.installed ? "已安装" : "未安装",
            model.running ? "运行中" : "未运行",
            bytes(model.size_bytes),
            text(model.parameter_size),
            text(model.quantization),
            model.estimated_ram_bytes == null ? "待实测" : bytes(model.estimated_ram_bytes),
            model.estimated_vram_bytes == null ? "待实测" : bytes(model.estimated_vram_bytes),
            text(model.runtime?.device_evidence, "未运行"),
            text(model.compatibility?.status, "unverified"),
            model.last_benchmark ? text(model.last_benchmark) : "尚未测速",
            model.current_task ? text(model.current_task) : "无",
            text(model.last_error),
          ])}
        />
      </Panel>

      <div className="two-column">
        <Panel title="当前配置引用">
          <DataTable headers={["角色", "模型", "用途", "安装状态", "兼容性"]} rows={assignments.map((item) => [item.role, item.model, capabilities[item.capability]?.label || item.capability, item.installed ? "已安装" : "缺失", item.compatibility?.status || "unverified"])} />
        </Panel>
        <Panel title="Python Provider">
          <DataTable headers={["Provider", "用途", "包", "模型状态", "配置模型", "目录", "错误"]} rows={providers.map((item) => [item.label, (item.capabilities ?? []).map((value: string) => capabilities[value]?.label || value).join("、"), item.package_available ? "已安装" : "未安装", item.installation_status, text(item.configured_model), text(item.model_root), text(item.last_error)])} />
        </Panel>
      </div>

      <Panel title="兼容性判断步骤">
        <div className="list">{(inventory.compatibility_process ?? []).map((step: string, index: number) => <div className="list-row" key={step}><span className="pill neutral">{index + 1}</span><div><strong>{step}</strong><small>{index < 2 ? "P3 后续实现" : "需要真实模型和主人电脑"}</small></div></div>)}</div>
      </Panel>
    </div>
  );
}
