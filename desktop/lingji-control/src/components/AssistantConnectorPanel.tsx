import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../api";
import type { LingJiApi } from "../api";

type ConnectorStatus = {
  id: "codex" | "claude_code" | "workbuddy";
  label: string;
  configuration_state: string;
  managed_by_lingji: boolean;
  live_test: boolean | null;
  one_click_supported: boolean;
  target: string;
  next_action: string;
};

type ConnectionSnapshot = {
  as_of: string;
  mcp_runtime: {
    state: string;
    ready: boolean;
    host: string;
    port: number;
    url: string;
    authentication: string;
    loopback_only: boolean;
  };
  shared_memory_policy: {
    owner_approved_memory_only: boolean;
    automatic_core_memory_write: boolean;
    candidate_write_available: boolean;
    agent_scope: string;
  };
  connectors: ConnectorStatus[];
};

type ConnectorPreview = {
  connector_id: ConnectorStatus["id"];
  mode: string;
  target: string;
  supported: boolean;
  conflict: boolean;
  changes: string[];
  preview: string;
  confirmation: string;
  unavailable_reason?: string;
  copy_payload?: string;
};

type ActionResult = {
  connector_id: string;
  state: string;
  message: string;
  copy_payload?: string;
  mcp_runtime_ready?: boolean;
  ok?: boolean;
};

const stateText = (connector: ConnectorStatus): string => {
  if (connector.live_test === true) return "连接测试通过";
  if (connector.configuration_state === "configured") return "已设置，等待测试";
  if (connector.configuration_state === "conflict") return "发现同名配置冲突";
  if (connector.configuration_state === "client_not_found") return "未检测到客户端";
  if (connector.configuration_state === "manual_configuration") return "需要在软件内粘贴配置";
  return "尚未设置";
};

const tone = (connector: ConnectorStatus): string => {
  if (connector.live_test === true) return "ok";
  if (["conflict", "client_not_found"].includes(connector.configuration_state)) return "error";
  if (connector.configuration_state === "configured") return "warning";
  return "neutral";
};

export default function AssistantConnectorPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const [snapshot, setSnapshot] = useState<ConnectionSnapshot | null>(null);
  const [preview, setPreview] = useState<ConnectorPreview | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async (live = false) => {
    if (!active) return;
    try {
      setSnapshot(await api.get<ConnectionSnapshot>(`/api/assistant-hub/connections${live ? "?live=true" : ""}`));
    } catch (reason) {
      const error = reason instanceof ApiError ? reason.message : "无法读取 AI 连接状态";
      setMessage(error);
    }
  }, [active, api]);

  useEffect(() => { void load(false); }, [load]);

  const selected = useMemo(
    () => snapshot?.connectors.find((item) => item.id === preview?.connector_id) ?? null,
    [preview, snapshot],
  );

  const openPreview = async (connectorId: ConnectorStatus["id"]) => {
    setBusy(`preview:${connectorId}`);
    setMessage("");
    try {
      setPreview(await api.post<ConnectorPreview>(`/api/assistant-hub/connections/${connectorId}/preview`));
    } catch (reason) {
      setMessage(reason instanceof ApiError ? reason.message : "无法生成安全设置预览");
    } finally {
      setBusy("");
    }
  };

  const apply = async () => {
    if (!preview) return;
    setBusy(`apply:${preview.connector_id}`);
    setMessage("");
    try {
      const result = await api.post<ActionResult>(
        `/api/assistant-hub/connections/${preview.connector_id}/apply`,
        { confirmation: preview.confirmation },
      );
      if (result.copy_payload) {
        await copy(result.copy_payload);
        setMessage(`${result.message} 配置已复制到剪贴板。`);
      } else {
        setMessage(result.message);
      }
      setPreview(null);
      await load(true);
    } catch (reason) {
      setMessage(reason instanceof ApiError ? reason.message : "连接设置失败");
    } finally {
      setBusy("");
    }
  };

  const test = async (connectorId: ConnectorStatus["id"]) => {
    setBusy(`test:${connectorId}`);
    setMessage("");
    try {
      const result = await api.post<ActionResult>(`/api/assistant-hub/connections/${connectorId}/test`);
      setMessage(result.message);
      await load(true);
    } catch (reason) {
      setMessage(reason instanceof ApiError ? reason.message : "连接测试失败");
    } finally {
      setBusy("");
    }
  };

  const rollback = async (connectorId: ConnectorStatus["id"]) => {
    setBusy(`rollback:${connectorId}`);
    setMessage("");
    try {
      const result = await api.post<ActionResult>(
        `/api/assistant-hub/connections/${connectorId}/rollback`,
        { confirmation: `DISCONNECT_${connectorId.toUpperCase()}_FROM_LINGJI` },
      );
      setMessage(result.message);
      await load(false);
    } catch (reason) {
      setMessage(reason instanceof ApiError ? reason.message : "断开失败");
    } finally {
      setBusy("");
    }
  };

  const copy = async (value: string) => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
    throw new Error("当前系统无法写入剪贴板");
  };

  return <section className="assistant-connector-section">
    <div className="assistant-section-heading">
      <div>
        <span className="desktop-eyebrow">让 AI 真正使用灵机记忆</span>
        <h3>连接后，AI 可以读取主人批准的记忆并提交候选记忆</h3>
        <p>连接不等于导入历史。这里负责今后的每次任务调用；上面的导入负责把旧资料放进灵机。</p>
      </div>
      <button className="button secondary" disabled={!active || busy === "refresh"} onClick={() => void load(true)}>重新检测连接</button>
    </div>

    <div className={snapshot?.mcp_runtime.ready ? "assistant-runtime-card ready" : "assistant-runtime-card warning"}>
      <div>
        <strong>{snapshot?.mcp_runtime.ready ? "灵机记忆网关已运行" : "灵机记忆网关未运行"}</strong>
        <small>本机 127.0.0.1:8767 · Bearer Token 认证 · 不开放公网</small>
      </div>
      <span className={`pill ${snapshot?.mcp_runtime.ready ? "ok" : "warning"}`}>
        {snapshot?.mcp_runtime.ready ? "可连接" : "需要重启灵机"}
      </span>
    </div>

    <div className="assistant-connector-grid">
      {(snapshot?.connectors ?? []).map((connector) => <article className="assistant-connector-card" key={connector.id}>
        <header>
          <div><h4>{connector.label}</h4><small>{connector.target}</small></div>
          <span className={`pill ${tone(connector)}`}>{stateText(connector)}</span>
        </header>
        <p>{connector.id === "workbuddy"
          ? "官方未提供稳定配置文件，灵机不会擅自修改。复制后粘贴到自定义连接器页面。"
          : "灵机会先显示改动，再备份现有配置。只管理名为 lingji-memory 的连接项。"}</p>
        <div className="assistant-connector-actions">
          {!connector.managed_by_lingji && <button
            className="button"
            disabled={busy !== "" || (!connector.one_click_supported && connector.id !== "workbuddy")}
            onClick={() => void openPreview(connector.id)}
          >{connector.id === "workbuddy" ? "复制连接配置" : "预览并连接"}</button>}
          {connector.managed_by_lingji && <>
            <button className="button" disabled={busy !== ""} onClick={() => void test(connector.id)}>测试连接</button>
            <button className="button secondary" disabled={busy !== ""} onClick={() => void rollback(connector.id)}>断开并回滚</button>
          </>}
        </div>
      </article>)}
    </div>

    {preview && <div className="assistant-connector-preview" role="dialog" aria-label="AI 连接设置预览">
      <header>
        <div><span className="desktop-eyebrow">写入前确认</span><h4>{selected?.label ?? preview.connector_id}</h4></div>
        <button className="assistant-preview-close" onClick={() => setPreview(null)} aria-label="关闭预览">×</button>
      </header>
      <p><strong>目标：</strong>{preview.target}</p>
      <ul>{preview.changes.map((change) => <li key={change}>{change}</li>)}</ul>
      <pre>{preview.preview}</pre>
      {preview.conflict && <div className="assistant-hub-notice error">发现同名配置冲突，灵机不会覆盖。</div>}
      {preview.unavailable_reason && <div className="assistant-hub-notice error">{preview.unavailable_reason}</div>}
      <div className="assistant-connector-actions">
        <button className="button secondary" onClick={() => setPreview(null)}>取消</button>
        <button className="button" disabled={!preview.supported || preview.conflict || busy !== ""} onClick={() => void apply()}>
          {busy.startsWith("apply:") ? "正在设置…" : preview.connector_id === "workbuddy" ? "复制配置" : "确认连接"}
        </button>
      </div>
    </div>}

    {message && <div className="assistant-hub-notice">{message}</div>}
  </section>;
}
