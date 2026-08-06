import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../api";
import type { LingJiApi } from "../api";
import "./AssistantSetupDirector.css";

type ConnectorId = "codex" | "claude_code" | "workbuddy";

type ReadinessFact = {
  state: string;
  managed?: boolean;
  target?: string;
  command?: string;
  last_error_code?: string;
  method?: string;
  verified?: boolean;
  last_checked_at?: string | null;
  detail?: string;
};

type ConnectorStatus = {
  id: ConnectorId;
  label: string;
  configuration_state: string;
  status_state?: string;
  managed_by_lingji: boolean;
  live_test: boolean | null;
  one_click_supported: boolean;
  client_available?: boolean | null;
  client_command?: string;
  target: string;
  blocking_reason?: string;
  last_test_code?: string;
  last_test_detail?: string;
  last_test_at?: string | null;
  next_action: string;
  readiness?: {
    configuration?: ReadinessFact;
    client?: ReadinessFact;
    real_connection?: ReadinessFact;
  };
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

type VectorSnapshot = {
  state?: string;
  ready?: boolean;
  service_ready?: boolean;
  search_available?: boolean;
  semantic_search_available?: boolean;
  lexical_search_available?: boolean;
  mode?: string | null;
  collection?: string | null;
  collection_exists?: boolean;
  vectors?: number | null;
  reason_code?: string;
  impact?: string;
  last_error?: string | null;
  rebuild_required?: boolean | null;
  stale?: boolean;
  producer?: {
    service?: string;
    instance_id?: string;
    pid?: number;
  };
  recovery?: {
    state?: string;
    automatic_refresh?: boolean;
    action?: string;
  };
  embedding?: {
    state?: string;
    configured_model?: string | null;
    primary_model?: string | null;
    active_model?: string | null;
    available?: boolean;
    verified?: boolean;
    last_error?: string | null;
    unavailable_models?: string[];
  };
};

type SetupSnapshot = {
  connections: ConnectionSnapshot | null;
  vector: VectorSnapshot | null;
  unavailable: string[];
};

type ConnectorPreview = {
  connector_id: ConnectorId;
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
  code?: string;
  copy_payload?: string;
  mcp_runtime_ready?: boolean;
  ok?: boolean;
};

const statusText = (connector: ConnectorStatus): string => {
  const state = connector.status_state ?? connector.configuration_state;
  if (state === "ready") return "连接已验证";
  if (state === "client_launch_blocked") return "命令存在但无法启动";
  if (state === "verification_failed") return "真实验证失败";
  if (state === "blocked") return "已阻塞";
  if (state === "verification_required") return "等待真实验证";
  if (state === "conflict") return "配置冲突";
  if (state === "client_not_found") return "未找到客户端命令";
  if (state === "manual_action_required" || state === "manual_configuration") return "需要在软件内完成";
  if (state === "configuration_required" || state === "not_configured") return "等待连接授权";
  return state || "状态未知";
};

const tone = (connector: ConnectorStatus): string => {
  const state = connector.status_state ?? connector.configuration_state;
  if (state === "ready") return "ok";
  if (["blocked", "conflict", "client_not_found", "client_launch_blocked", "verification_failed"].includes(state)) return "error";
  if (["verification_required", "configuration_required", "manual_action_required", "manual_configuration"].includes(state)) return "warning";
  return "neutral";
};

const humanState = (value: string | undefined): string => ({
  healthy: "正常",
  ready: "已就绪",
  available: "可用",
  verified: "已验证",
  configured: "已配置",
  not_configured: "未配置",
  not_verified: "尚未验证",
  launch_blocked: "启动被阻止",
  not_found: "未找到",
  degraded: "降级",
  empty: "尚无向量",
  configuration_required: "需要配置",
  unavailable: "不可用",
  failed: "失败",
  blocked: "阻塞",
  rebuild_required: "需要重建",
  disabled: "未启用",
}[String(value ?? "").toLowerCase()] ?? String(value || "未知"));

const settled = <T,>(result: PromiseSettledResult<T>): T | null => result.status === "fulfilled" ? result.value : null;

export default function AssistantConnectorPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const [snapshot, setSnapshot] = useState<SetupSnapshot | null>(null);
  const [preview, setPreview] = useState<ConnectorPreview | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async (live = false) => {
    if (!active) return;
    if (live) setBusy("refresh");
    const results = await Promise.allSettled([
      api.get<ConnectionSnapshot>(`/api/assistant-hub/connections${live ? "?live=true" : ""}`),
      api.get<VectorSnapshot>("/api/vector/status"),
    ]);
    const unavailable = ["连接状态", "向量状态"].filter((_, index) => results[index].status === "rejected");
    setSnapshot({
      connections: settled(results[0] as PromiseSettledResult<ConnectionSnapshot>),
      vector: settled(results[1] as PromiseSettledResult<VectorSnapshot>),
      unavailable,
    });
    if (unavailable.length) setMessage(`暂时无法读取：${unavailable.join("、")}。未知状态不会显示成正常。`);
    if (live) setBusy("");
  }, [active, api]);

  useEffect(() => { void load(false); }, [load]);

  const connections = snapshot?.connections;
  const connectors = connections?.connectors ?? [];
  const selected = useMemo(
    () => connectors.find((item) => item.id === preview?.connector_id) ?? null,
    [connectors, preview],
  );
  const readyConnector = connectors.find((item) => item.status_state === "ready");
  const blockingConnector = connectors.find((item) => [
    "blocked", "conflict", "client_not_found", "client_launch_blocked", "verification_failed",
  ].includes(item.status_state ?? ""));
  const nextConnector = connectors.find((item) => [
    "verification_required", "configuration_required",
  ].includes(item.status_state ?? ""));
  const vector = snapshot?.vector;
  const vectorReady = vector?.semantic_search_available === true;

  const primary = useMemo(() => {
    if (!connections?.mcp_runtime.ready) return {
      tone: "error",
      eyebrow: "当前阻塞",
      title: "灵机记忆网关尚未就绪",
      detail: "客户端配置不会被误报成可用。灵机会继续恢复 8767，你也可以立即重新检测。",
      action: "立即重新检测",
      run: () => void load(true),
    };
    if (blockingConnector) return {
      tone: "error",
      eyebrow: "当前阻塞",
      title: `${blockingConnector.label}：${statusText(blockingConnector)}`,
      detail: blockingConnector.blocking_reason || blockingConnector.last_test_detail || "真实客户端验证失败。",
      action: blockingConnector.managed_by_lingji ? "重新验证" : blockingConnector.next_action,
      run: () => blockingConnector.managed_by_lingji ? void test(blockingConnector.id) : void openPreview(blockingConnector.id),
    };
    if (!readyConnector && nextConnector) return {
      tone: "warning",
      eyebrow: "等待授权或验证",
      title: `${nextConnector.label}：${statusText(nextConnector)}`,
      detail: nextConnector.blocking_reason || "灵机会自动检查状态；涉及外部客户端配置时才需要你确认。",
      action: nextConnector.managed_by_lingji ? "立即验证" : "查看配置影响",
      run: () => nextConnector.managed_by_lingji ? void test(nextConnector.id) : void openPreview(nextConnector.id),
    };
    if (!vectorReady) return {
      tone: "warning",
      eyebrow: "语义检索状态",
      title: vector?.state === "empty" ? "Qdrant 可运行，但当前没有向量" : "语义检索暂不可用",
      detail: vectorIssue(vector),
      action: "刷新状态",
      run: () => void load(true),
    };
    return {
      tone: "ok",
      eyebrow: "当前状态",
      title: `${readyConnector?.label ?? "AI 客户端"} 与语义检索均已验证`,
      detail: "配置、命令执行、客户端注册和向量状态来自各自明确证据，不再互相借用绿色状态。",
      action: "重新核验",
      run: () => void load(true),
    };
  }, [blockingConnector, connections?.mcp_runtime.ready, load, nextConnector, readyConnector, vector, vectorReady]);

  const openPreview = async (connectorId: ConnectorId) => {
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

  const test = async (connectorId: ConnectorId) => {
    setBusy(`test:${connectorId}`);
    setMessage("");
    try {
      const result = await api.post<ActionResult>(`/api/assistant-hub/connections/${connectorId}/test`);
      setMessage(result.message);
      await load(false);
    } catch (reason) {
      setMessage(reason instanceof ApiError ? reason.message : "连接测试失败");
    } finally {
      setBusy("");
    }
  };

  const rollback = async (connectorId: ConnectorId) => {
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
    <section className={`assistant-setup-director ${primary.tone}`} aria-label="AI 接入当前状态与下一步">
      <div>
        <span className="desktop-eyebrow">{primary.eyebrow}</span>
        <h3>{primary.title}</h3>
        <p>{primary.detail}</p>
      </div>
      <button className="button primary" disabled={busy !== ""} onClick={primary.run}>{primary.action}</button>
    </section>

    <div className="assistant-readiness-grid" aria-label="AI 接入准备度">
      <ReadinessItem
        label="灵机 MCP Runtime"
        state={connections?.mcp_runtime.ready ? "已运行" : "不可用"}
        tone={connections?.mcp_runtime.ready ? "ok" : "error"}
        detail="127.0.0.1:8767 · Bearer Token · 不开放公网"
      />
      <ReadinessItem
        label="真实 AI 客户端"
        state={readyConnector ? `${readyConnector.label} 已验证` : blockingConnector ? statusText(blockingConnector) : "等待验证"}
        tone={readyConnector ? "ok" : blockingConnector ? "error" : "warning"}
        detail={blockingConnector?.blocking_reason || nextConnector?.blocking_reason || "配置存在、命令可启动、客户端注册验证分别计算"}
      />
      <ReadinessItem
        label="全文检索"
        state={vector?.lexical_search_available === false ? "不可用" : "可用"}
        tone={vector?.lexical_search_available === false ? "error" : "ok"}
        detail="Qdrant 异常不会把全文检索一起伪装成失败"
      />
      <ReadinessItem
        label="语义检索"
        state={vectorReady ? "可用" : humanState(vector?.state)}
        tone={vectorReady ? "ok" : vector?.state === "unavailable" ? "error" : "warning"}
        detail={vectorIssue(vector)}
      />
    </div>

    <div className="assistant-section-heading">
      <div>
        <span className="desktop-eyebrow">客户端状态证据</span>
        <h3>配置、命令启动和真实注册分开显示</h3>
        <p>任何一层失败，整体状态都不会显示为可用。路径存在不再代替命令启动，配置存在也不再代替真实验证。</p>
      </div>
      <button className="button secondary" disabled={!active || busy !== ""} onClick={() => void load(true)}>重新检测全部状态</button>
    </div>

    <div className="assistant-connector-grid">
      {connectors.map((connector) => {
        const readiness = connector.readiness;
        return <article className={`assistant-connector-card ${tone(connector)}`} key={connector.id}>
          <header>
            <div><h4>{connector.label}</h4><small>{connector.target}</small></div>
            <span className={`pill ${tone(connector)}`}>{statusText(connector)}</span>
          </header>
          <dl className="assistant-connector-facts">
            <div>
              <dt>配置</dt>
              <dd>{humanState(readiness?.configuration?.state ?? connector.configuration_state)}</dd>
            </div>
            <div>
              <dt>命令启动</dt>
              <dd>{humanState(readiness?.client?.state ?? (connector.client_available ? "available" : "not_found"))}</dd>
            </div>
            <div>
              <dt>真实客户端验证</dt>
              <dd>{humanState(readiness?.real_connection?.state ?? (connector.live_test ? "verified" : "not_verified"))}</dd>
            </div>
          </dl>
          {readiness?.real_connection?.method && <small className="assistant-evidence-method">
            证据：{readiness.real_connection.method}{readiness.real_connection.last_checked_at ? ` · ${new Date(readiness.real_connection.last_checked_at).toLocaleString()}` : ""}
          </small>}
          <p className={tone(connector) === "error" ? "assistant-connector-problem" : ""}>
            {connector.blocking_reason || readiness?.client?.detail || readiness?.real_connection?.detail || connector.next_action}
          </p>
          <div className="assistant-connector-next"><span>下一步</span><strong>{connector.next_action}</strong></div>
          <div className="assistant-connector-actions">
            {!connector.managed_by_lingji && <button
              className="button"
              disabled={busy !== "" || (!connector.one_click_supported && connector.id !== "workbuddy")}
              onClick={() => void openPreview(connector.id)}
            >{connector.id === "workbuddy" ? "复制连接配置" : "查看并授权连接"}</button>}
            {connector.managed_by_lingji && <>
              <button className="button" disabled={busy !== ""} onClick={() => void test(connector.id)}>立即验证</button>
              <button className="button secondary" disabled={busy !== ""} onClick={() => void rollback(connector.id)}>断开并回滚</button>
            </>}
          </div>
        </article>;
      })}
    </div>

    {vector && <section className={`assistant-vector-truth ${vectorReady ? "ok" : vector.state === "unavailable" ? "error" : "warning"}`}>
      <div>
        <span className="desktop-eyebrow">Qdrant 唯一状态来源</span>
        <h4>{vectorReady ? "语义检索可用" : humanState(vector.state)}</h4>
        <p>{vector.impact || vectorIssue(vector)}</p>
      </div>
      <dl>
        <div><dt>状态生产者</dt><dd>{vector.producer?.service || "MCP 快照"}</dd></div>
        <div><dt>模式</dt><dd>{vector.mode || "未知"}</dd></div>
        <div><dt>Collection</dt><dd>{vector.collection_exists ? "存在" : "不存在"}</dd></div>
        <div><dt>向量</dt><dd>{vector.vectors ?? "未知"}</dd></div>
        <div><dt>原因</dt><dd>{vector.reason_code || "未知"}</dd></div>
        <div><dt>恢复</dt><dd>{humanState(vector.recovery?.state)}</dd></div>
      </dl>
      {vector.recovery?.action && <small>{vector.recovery.action}</small>}
    </section>}

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

    {message && <div className={message.includes("失败") || message.includes("找不到") || message.includes("未找到") || message.includes("拒绝") ? "assistant-hub-notice error" : "assistant-hub-notice"}>{message}</div>}
  </section>;
}

function ReadinessItem({ label, state, detail, tone: itemTone }: { label: string; state: string; detail: string; tone: string }) {
  return <article className={`assistant-readiness-item ${itemTone}`}>
    <span>{label}</span>
    <strong>{state}</strong>
    <small>{detail}</small>
  </article>;
}

function vectorIssue(vector: VectorSnapshot | null | undefined): string {
  if (!vector) return "向量状态暂时不可读取；全文检索仍可用。";
  if (vector.impact) return vector.impact;
  const embedding = vector.embedding;
  const configured = embedding?.configured_model || embedding?.primary_model || "未配置模型";
  if (embedding?.last_error) return `Embedding ${configured} 未激活：${embedding.last_error}`;
  if (embedding?.unavailable_models?.length) return `Embedding 模型不可用：${embedding.unavailable_models.join("、")}。全文检索仍可用。`;
  if (!embedding?.available) return `Embedding 已配置为 ${configured}，但尚未验证或激活；全文检索仍可用。`;
  if (vector.rebuild_required) return "Embedding 已可用，但 Qdrant Collection 合同发生变化，需要授权后安全重建。";
  if (vector.last_error) return `Qdrant ${humanState(vector.state)}：${vector.last_error}`;
  if (!vector.search_available) return `Qdrant 当前为 ${humanState(vector.state)}（${vector.mode || "模式未知"}）；全文检索仍可用。`;
  return "全文检索和语义检索均可用。";
}
