import { useCallback, useEffect, useState } from "react";
import { Empty, Notice, Panel } from "../components/ui";
import type { ObsidianStatus, PageProps, SettingsSnapshot } from "../types";

const OBSIDIAN_KEYS = [
  "obsidian_cli_enabled",
  "obsidian_cli_path",
  "obsidian_vault_path",
  "obsidian_vault_name",
  "obsidian_cli_timeout_seconds",
  "obsidian_cli_dry_run",
] as const;

type Draft = Record<(typeof OBSIDIAN_KEYS)[number], string | number | boolean>;

const STATE_LABELS: Record<string, string> = {
  healthy: "健康",
  degraded: "降级",
  disabled: "已禁用",
  unavailable: "不可用",
  configuration_required: "需要配置",
};

function errorText(reason: unknown): string {
  return reason instanceof Error ? reason.message : String(reason);
}

function stateTone(state: string): string {
  if (state === "healthy") return "success";
  if (state === "configuration_required" || state === "degraded") return "warning";
  if (state === "unavailable") return "error";
  return "neutral";
}

export default function ObsidianPage({ api, active }: PageProps) {
  const [status, setStatus] = useState<ObsidianStatus | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "loaded" | "failed">("idle");

  const load = useCallback(async () => {
    if (!active) return;
    setBusy(true);
    setLoadState("loading");
    try {
      const [nextStatus, settings] = await Promise.all([
        api.get<ObsidianStatus>("/api/obsidian/status"),
        api.get<SettingsSnapshot>("/api/settings"),
      ]);
      const values = settings.values;
      setStatus(nextStatus);
      setDraft({
        obsidian_cli_enabled: Boolean(values.obsidian_cli_enabled),
        obsidian_cli_path: String(values.obsidian_cli_path || ""),
        obsidian_vault_path: String(values.obsidian_vault_path || ""),
        obsidian_vault_name: String(values.obsidian_vault_name || ""),
        obsidian_cli_timeout_seconds: Number(values.obsidian_cli_timeout_seconds || 15),
        obsidian_cli_dry_run: Boolean(values.obsidian_cli_dry_run),
      });
      setError("");
      setLoadState("loaded");
    } catch (reason) {
      setError(errorText(reason));
      setLoadState("failed");
    } finally {
      setBusy(false);
    }
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);

  async function choosePath(kind: "cli" | "vault") {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: kind === "vault",
        title: kind === "vault" ? "选择 Obsidian Vault" : "选择 Obsidian CLI",
      });
      if (typeof selected === "string" && draft) {
        setDraft({ ...draft, [kind === "vault" ? "obsidian_vault_path" : "obsidian_cli_path"]: selected });
      }
    } catch {
      setError("浏览器模式无法打开系统选择器，请手动填写路径。");
    }
  }

  async function validate() {
    if (!draft) return;
    setBusy(true);
    setError("");
    try {
      const next = await api.post<ObsidianStatus>("/api/obsidian/validate", { values: draft });
      setStatus(next);
      setMessage(next.state === "healthy" ? "配置验证通过，尚未保存。" : "配置已验证，请根据状态提示修正。" );
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError("");
    try {
      await api.patch<SettingsSnapshot>("/api/settings", { values: draft });
      const next = await api.post<ObsidianStatus>("/api/obsidian/refresh");
      setStatus(next);
      setMessage("Obsidian 设置已保存。");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  if (!active && !status) return <Empty text="连接本机服务后显示 Obsidian 状态。" />;
  if (!draft) return <Empty text={loadState === "loading" ? "正在读取 Obsidian 配置…" : loadState === "failed" ? `Obsidian 配置读取失败：${error || "请检查本机服务后重试。"}` : "尚未加载 Obsidian 配置。"} />;

  return <div className="stack">
    {!active && <Notice kind="warning">本机控制服务已断开，页面保留上次状态。</Notice>}
    {error && <Notice kind="error">{error}</Notice>}
    {message && <Notice>{message}</Notice>}

    <div className="toolbar">
      <button className="button secondary" disabled={!active || busy} onClick={() => void load()}>{busy ? "处理中…" : "刷新状态"}</button>
      {status && <span className={`pill ${stateTone(status.state)}`}>{STATE_LABELS[status.state] || status.state}</span>}
      <span>版本：{status?.version || "-"}</span>
      <span>CLI 来源：{status?.cli_discovery_source || "-"}</span>
      <span>Vault 来源：{status?.vault_discovery_source || "-"}</span>
    </div>

    <div className="vector-detail-grid">
      <Panel title="Obsidian CLI 状态">
        <dl className="detail-list">
          <div><dt>CLI</dt><dd>{status?.cli_path_display || "未配置"}</dd></div>
          <div><dt>Vault</dt><dd>{status?.vault_path_display || "未配置"}</dd></div>
          <div><dt>Vault 名称</dt><dd>{status?.vault_name || "-"}</dd></div>
          <div><dt>超时</dt><dd>{status?.timeout_seconds ?? 15} 秒</dd></div>
          <div><dt>Dry Run</dt><dd>{status?.dry_run ? "开启" : "关闭"}</dd></div>
          <div><dt>兼容层</dt><dd>{status?.capabilities.compatibility_forwarding ? "转发到 src.obsidian" : "-"}</dd></div>
        </dl>
        {status?.issues.map((issue) => <Notice kind="warning" key={issue.code}>{issue.code}：{issue.message}</Notice>)}
      </Panel>

      <Panel title="Obsidian 配置">
        <div className="settings-list">
          <label><input type="checkbox" checked={Boolean(draft.obsidian_cli_enabled)} onChange={(event) => setDraft({ ...draft, obsidian_cli_enabled: event.target.checked })} /> 启用 Obsidian CLI</label>
          <label>CLI 路径<div className="toolbar"><input value={String(draft.obsidian_cli_path)} onChange={(event) => setDraft({ ...draft, obsidian_cli_path: event.target.value })} placeholder="留空时自动发现" /><button className="button secondary" onClick={() => void choosePath("cli")}>选择文件</button></div></label>
          <label>Vault 路径<div className="toolbar"><input value={String(draft.obsidian_vault_path)} onChange={(event) => setDraft({ ...draft, obsidian_vault_path: event.target.value })} placeholder="Workspace Vault 优先" /><button className="button secondary" onClick={() => void choosePath("vault")}>选择目录</button></div></label>
          <label>Vault 名称<input value={String(draft.obsidian_vault_name)} onChange={(event) => setDraft({ ...draft, obsidian_vault_name: event.target.value })} placeholder="留空时从路径推导" /></label>
          <label>CLI 超时（秒）<input type="number" min={1} max={300} value={Number(draft.obsidian_cli_timeout_seconds)} onChange={(event) => setDraft({ ...draft, obsidian_cli_timeout_seconds: Number(event.target.value) })} /></label>
          <label><input type="checkbox" checked={Boolean(draft.obsidian_cli_dry_run)} onChange={(event) => setDraft({ ...draft, obsidian_cli_dry_run: event.target.checked })} /> Dry Run，不执行写命令</label>
        </div>
        <div className="toolbar sticky-actions">
          <button className="button secondary" disabled={busy || !active} onClick={() => void validate()}>验证但不保存</button>
          <button className="button primary" disabled={busy || !active} onClick={() => void save()}>保存设置</button>
        </div>
      </Panel>
    </div>
  </div>;
}
