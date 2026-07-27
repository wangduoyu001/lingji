import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { isTauriDesktopRuntime } from "../api";
import DataTable from "../components/DataTable";
import { Empty, Json, Metric, Notice, Panel } from "../components/ui";
import type { PageProps, Row } from "../types";

type ProcessObservation = {
  pid: number;
  parent_pid: number;
  name: string;
  relation: "lingji_descendant" | "external" | string;
};

type WindowlessAcceptanceReport = {
  schema_version: number;
  started_at_ms: number;
  finished_at_ms: number;
  passed: boolean;
  desktop_pid: number;
  initial_runtime_pid: number | null;
  restarted_runtime_pid: number | null;
  authenticated_before: boolean;
  authenticated_after: boolean;
  forbidden_descendants: ProcessObservation[];
  external_shell_processes: ProcessObservation[];
  phases: Row[];
  failure: string | null;
  report_path: string;
};

export default function AcceptancePage({ api, active }: PageProps) {
  const [form, setForm] = useState({ vault: "", chatgpt_export: "", media: "", deep_zip_check: true, hash_inputs: true });
  const [reports, setReports] = useState<Row[]>([]);
  const [result, setResult] = useState<Row | null>(null);
  const [windowlessResult, setWindowlessResult] = useState<WindowlessAcceptanceReport | null>(null);
  const [error, setError] = useState("");
  const [windowlessError, setWindowlessError] = useState("");
  const [running, setRunning] = useState(false);
  const [windowlessRunning, setWindowlessRunning] = useState(false);
  const desktopRuntime = isTauriDesktopRuntime();

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

  async function runWindowlessAcceptance() {
    if (!desktopRuntime || !active || windowlessRunning) return;
    setWindowlessRunning(true);
    setWindowlessError("");
    setWindowlessResult(null);
    try {
      const payload = await invoke<WindowlessAcceptanceReport>("run_windowless_acceptance");
      setWindowlessResult(payload);
    } catch (reason) {
      setWindowlessError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setWindowlessRunning(false);
    }
  }

  const report = result?.report as Row | undefined;
  return (
    <div className="stack">
      <Panel title="桌面零 Shell 验收">
        <div className="stack">
          <Notice kind="warning">
            本验收完全由 LingJi 桌面端内部执行，不调用 PowerShell、CMD、WMI 或批处理。过程为启动后静置 60 秒、应用内重启 Core、再静置 60 秒，预计约 2 分钟。
          </Notice>
          <div className="toolbar">
            <button
              className="button primary"
              disabled={!desktopRuntime || !active || windowlessRunning}
              onClick={() => void runWindowlessAcceptance()}
            >
              {windowlessRunning ? "正在执行零 Shell 验收…" : "开始桌面零 Shell 验收"}
            </button>
          </div>
          {!desktopRuntime && <Notice kind="error">该验收只能在真实 Windows 安装版中运行，浏览器和开发预览不能冒充结果。</Notice>}
          {windowlessError && <Notice kind="error">{windowlessError}</Notice>}
          {windowlessResult ? (
            <div className="stack">
              <div className="metric-grid">
                <Metric title="验收状态" value={windowlessResult.passed ? "通过" : "失败"} />
                <Metric title="认证健康" value={windowlessResult.authenticated_after ? "是" : "否"} />
                <Metric title="LingJi Shell 子进程" value={String(windowlessResult.forbidden_descendants.length)} />
                <Metric title="外部 Shell" value={String(windowlessResult.external_shell_processes.length)} />
              </div>
              {windowlessResult.failure && <Notice kind="error">{windowlessResult.failure}</Notice>}
              {windowlessResult.external_shell_processes.length > 0 && (
                <Notice kind="warning">
                  检测到不属于 LingJi 进程树的 Shell 进程。它们不会让 LingJi 验收失败，但说明其他程序正在启动 PowerShell、CMD 或 Console Host。
                </Notice>
              )}
              <small>Desktop PID：{windowlessResult.desktop_pid}</small>
              <small>Core PID：{windowlessResult.initial_runtime_pid ?? "-"} → {windowlessResult.restarted_runtime_pid ?? "-"}</small>
              <small>报告：{windowlessResult.report_path}</small>
              <Json value={windowlessResult.phases as React.ReactNode[][]} />
              {windowlessResult.forbidden_descendants.length > 0 && <Json value={windowlessResult.forbidden_descendants as unknown as React.ReactNode[][]} />}
              {windowlessResult.external_shell_processes.length > 0 && <Json value={windowlessResult.external_shell_processes as unknown as React.ReactNode[][]} />}
            </div>
          ) : <Empty text="运行后显示 LingJi 进程树、Core 重启、认证健康和外部 Shell 证据。" />}
        </div>
      </Panel>

      <Notice kind="warning">本功能只读取 Vault、数据库、ChatGPT 导出和样例媒体。唯一允许写入的位置是 <code>storage/reports/acceptance</code>，不会迁移、删除或覆盖输入文件。</Notice>
      <div className="two-column wide-left">
        <Panel title="真实环境只读验收">
          <form className="form-grid" onSubmit={(event) => void run(event)}>
            <label className="span-2">Obsidian Vault<input required value={form.vault} onChange={(event) => setForm({ ...form, vault: event.target.value })} placeholder="E:\\obsidian\\本地知识库" /></label>
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
          {report ? <div className="stack"><div className="metric-grid"><Metric title="状态" value={String(report.status || "未知")} /><Metric title="输入未变化" value={report.inputs_unchanged ? "是" : "否"} /><Metric title="错误" value={String(report.error_count || 0)} /><Metric title="警告" value={String(report.warning_count || 0)} /></div><small>JSON：{String(result?.json_path || "-")}</small><small>Markdown：{String(result?.markdown_path || "-")}</small><Json value={(report.checks ?? []) as React.ReactNode[][]} /></div> : <Empty text="运行后显示状态、输入完整性和报告路径。" />}
        </Panel>
      </div>
      <Panel title="验收历史">
        <div className="toolbar"><button className="button secondary" onClick={() => void load()} disabled={!active}>刷新</button></div>
        <DataTable headers={["时间", "状态", "错误", "警告", "输入未变化", "报告"]} rows={reports.map((item: any): React.ReactNode[] => [String(item.generated_at ?? "-"), String(item.status ?? "-"), item.error_count ?? 0, item.warning_count ?? 0, item.inputs_unchanged ? "是" : "否", String(item.markdown_path ?? String(item.path ?? ""))])} />
      </Panel>
    </div>
  );
}
