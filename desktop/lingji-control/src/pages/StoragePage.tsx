import { useCallback, useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import { Empty, Json, Metric, Panel, bytes } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function StoragePage({ api, active }: PageProps) {
  const [inventory, setInventory] = useState<Row | null>(null);
  const [plans, setPlans] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [confirmation, setConfirmation] = useState("");

  const load = useCallback(async () => {
    if (!active) return;
    const [nextInventory, nextPlans] = await Promise.all([
      api.get<Row>("/api/storage"),
      api.get<Row[]>("/api/storage/plans"),
    ]);
    setInventory(nextInventory);
    setPlans(nextPlans);
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);

  async function createPlan() {
    const plan = await api.post<Row>("/api/storage/plans", {});
    setSelected(plan);
    setConfirmation("");
    await load();
  }

  async function execute() {
    if (!selected) return;
    setSelected(await api.post<Row>(`/api/storage/plans/${selected.plan_id}/execute`, { confirmation }));
    await load();
  }

  async function restore() {
    if (!selected) return;
    setSelected(await api.post<Row>(`/api/storage/plans/${selected.plan_id}/restore`, { confirmation }));
    await load();
  }

  return (
    <div className="stack">
      <div className="toolbar">
        <button className="button secondary" onClick={() => void load()}>刷新</button>
        <button className="button primary" onClick={() => void createPlan()}>生成预览计划</button>
      </div>
      {inventory && <div className="metric-grid"><Metric title="总占用" value={bytes((inventory.totals as Record<string, unknown>)?.bytes as number ?? 0)} /><Metric title="文件" value={String((inventory.totals as Record<string, unknown>)?.files ?? 0)} /><Metric title="磁盘剩余" value={bytes((inventory.totals as Record<string, unknown>)?.disk_free_bytes as number ?? 0)} /><Metric title="剩余比例" value={`${(inventory.totals as Record<string, unknown>)?.disk_free_percent ?? 0}%`} /></div>}
      <Panel title="分类占用"><DataTable headers={["类别", "路径", "文件", "占用", "保护", "可清理"]} rows={(Object.entries(inventory?.categories ?? {}).map(([name, value]) => { const row = value as Row; return [name, String(row.path ?? ""), String(row.files ?? ""), bytes(row.bytes as number ?? 0), row.protected ? "是" : "否", row.cleanup_allowed ? "是" : "否"] as React.ReactNode[]; }))} /></Panel>
      <div className="two-column">
        <Panel title="计划"><div className="list">{plans.map((plan) => <button className="list-button" key={plan.plan_id as React.Key} onClick={async () => setSelected(await api.get<Row>(`/api/storage/plans/${plan.plan_id}`))}><strong>{String(plan.plan_id ?? "")}</strong><small>{String(plan.status ?? "")} · {bytes((plan.summary as Record<string, unknown>)?.bytes as number ?? 0)}</small></button>)}</div></Panel>
        <Panel title="计划详情">{selected ? <><Json value={selected} /><label>确认文字<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label><div className="toolbar"><button className="button danger" onClick={() => void execute()}>执行</button><button className="button secondary" onClick={() => void restore()}>恢复</button></div></> : <Empty text="原始资料和 Vault 永远不会进入自动清理计划。" />}</Panel>
      </div>
    </div>
  );
}
