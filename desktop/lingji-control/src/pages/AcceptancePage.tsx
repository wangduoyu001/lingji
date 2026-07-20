import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import DataTable from "../components/DataTable";
import { Empty, Json, Metric, Notice, Panel } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function AcceptancePage({ api, active }: PageProps) {
  const [form, setForm] = useState({ vault: "", chatgpt_export: "", media: "", deep_zip_check: true, hash_inputs: true });
  const [reports, setReports] = useState<Row[]>([]);
  const [result, setResult] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    if (!active) return;
    try {
      setReports(await api.get<Row[]>("/api/acceptance/reports?limit=100"));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [active, api]);
  useEffect(() => { void load(); }, [load]);

  async function run(event: FormEvent) {
    event.preventDefault();
    if (!active || running) return;
    setRunning(true);
    setError("");
    try {
      const payload = await api.post<Row>("/api/acceptance/run", {
        vault: form.vault.trim() || null,
        chatgpt_export: form.chatgpt_export.trim() || null,
        media: form.media.trim() || null,
        deep_zip_check: form.deep_zip_check,
        hash_inputs: form.hash_inputs,
      });
      setResult(payload);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setRunning(false);
    }
  }

  const report = result?.report as Row | undefined;
  return (
    <div className="stack">
      <Notice kind="warning">本功能只读取 Vault、数据库、ChatGPT 导出和样例媒体。唯一允许写入的位置是 <code>storage/reports/acceptance</code>，不会迁移、删除或覆盖输入文件。</Notice>
      <div className="two-column wide-left">
        <Panel title="真实环境只读验收">
          <form className="form-grid" onSubmit={(event) => void run(event)}>
            <label className="span-2">Obsidian Vault<input required value={form.vault} onChange={(event) => setForm({ ...form, vault: event.target.value })} placeholder="E:\obsidian\本地知识库" /></label>
            <label className="span-2">ChatGPT 导出 ZIP / JSON / 目录（可选）<input value={form.chatgpt_export} onChange={(event) => setForm({ ...form, chatgpt_export: event.target.value })} /></label>
            <label className="span-2">样例媒体（可选）<input value={form.media} onChange={(event) => setForm({ ...form, media: event.target.value })} /></label>
            <div className="checkbox-stack span-2">
              <label><input type="checkbox" checked={form.deep_zip_check} onChange={(event) => setForm({ ...form, deep_zip_check: event.target.checked })} /> 深度检查 ZIP CRC</label>
              <label><input type="checkbox" checked={form.hash_inputs} onChange={(event) => setForm({ ...form, hash_inputs: event.target.checked })} /> 验收前后计算输入哈希</label>
            </div>
            <button className="button primary" disabled={!active || running}>{running ? "正在只读检查…" : "开始只读验收"}</button>
          </form>
          {error && <Notice kind="error">{error}</Notice>}
        </Panel>
        <Panel title="本次结果">
          {report ? <div className="stack"><div className="metric-grid"><Metric title="状态" value={String(report.status || "未知")} /><Metric title="输入未变化" value={report.inputs_unchanged ? "是" : "否"} /><Metric title="错误" value={String(report.error_count || 0)} /><Metric title="警告" value={String(report.warning_count || 0)} /></div><small>JSON：{String(result?.json_path || "-")}</small><small>Markdown：{String(result?.markdown_path || "-")}</small><Json value={report.checks ?? []} /></div> : <Empty text="运行后显示状态、输入完整性和报告路径。" />}
        </Panel>
      </div>
      <Panel title="验收历史">
        <div className="toolbar"><button className="button secondary" onClick={() => void load()} disabled={!active}>刷新</button></div>
        <DataTable headers={["时间", "状态", "错误", "警告", "输入未变化", "报告"]} rows={reports.map((item) => [item.generated_at || "-", item.status || "-", item.error_count || 0, item.warning_count || 0, item.inputs_unchanged ? "是" : "否", item.markdown_path || item.path])} />
      </Panel>
    </div>
  );
}
