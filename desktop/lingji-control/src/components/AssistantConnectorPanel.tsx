import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../api";
import type { LingJiApi } from "../api";
import "./AssistantSetupDirector.css";

type ConnectorId = "codex" | "claude_code" | "workbuddy";

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
  last_test_detail?: string;
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

type AssistantRecord = {
  id: string;
  label: string;
  detection_state: string;
  import_state: string;
  discovered_paths: string[];
  candidate_count: number;
  message: string;
  next_action: string;
};

type AssistantScan = {
  scanned_at: string;
  safety: {
    read_only: boolean;
    content_read: boolean;
    automatic_core_memory_write: boolean;
    review_required_for_permanent_memory: boolean;
  };
  assistants: AssistantRecord[];
};

type VectorSnapshot = {
  state?: string;
  ready?: boolean;
  mode?: string | null;
  last_error?: string | null;
  rebuild_required?: boolean | null;
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
  assistants: AssistantScan | null;
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
  copy_payload?: string;
  mcp_runtime_ready?: boolean;
  ok?: boolean;
};

const statusText = (connector: ConnectorStatus): string => {
  const state = connector.status_state ?? connector.configuration_state;
  if (state === "ready" || connector.live_test === true) return "连接可用";
  if (state === "blocked") return "已阻塞";
  if (state === "verification_required") return "已配置，待真实验证";
  if (state === "conflict") return "配置冲突";
  if (state === "client_not_found") return "未找到客户端命令";
  if (state === "manual_action_required" || state === "manual_configuration") return "需要在软件内完成";
  if (state === "configuration_required" || state === "not_configured") return "需要连接";
  return state || "状态未知";
};

const tone = (connector: ConnectorStatus): string => {
  const state = connector.status_state ?? connector.configuration_state;
  if (state === "ready" || connector.live_test === true) return "ok";
  if (["blocked", "conflict", "client_not_found"].includes(state)) return "error";
  if (["verification_required", "configuration_required", "manual_action_required", "manual_configuration"].includes(state)) return "warning";
  return "neutral";
};

const humanState = (value: string | undefined): string => ({
  healthy: "正常",
  ready: "已就绪",
  available: "可用",
  degraded: "降级",
  configuration_required: "需要配置",
  unavailable: "不可用",
  failed: "失败",
  rebuild_required: "需要重建",
  disabled: "未启用",
}[String(value ?? "").toLowerCase()] ?? String(value || "未知"));

const importExplanation = (assistant: AssistantRecord): string => {
  if (assistant.id === "codex") {
    const paths = assistant.discovered_paths.length ? assistant.discovered_paths.join("、") : "Codex 本地目录";
    return `发现 ${paths}，共 ${assistant.candidate_count.toLocaleString()} 个文件元数据。当前只支持导入结构化 Codex Report JSON；不会自动读取原始 Session、JSONL 或 Markdown 正文。`;
  }
  if (assistant.id === "chatgpt") {
    return "灵机不能访问 ChatGPT 账号或浏览器登录态。需要先从 ChatGPT 导出 ZIP/JSON，再由你确认文件后导入。";
  }
  if (assistant.id === "claude_code") {
    return `已发现 ${assistant.candidate_count.toLocaleString()} 个 Claude Code 历史文件元数据，但当前导入适配器尚未实现，灵机不会擅自读取正文。`;
  }
  if (assistant.id === "workbuddy") {
    return "已检测到 WorkBuddy 安装，但没有稳定的官方导出目录。当前只能连接 MCP，不能自动导入历史。";
  }
  return assistant.message;
};

const settled = <T,>(result: PromiseSettledResult<T>): T | null => result.status === "fulfilled" ? result.value : null;

export default function AssistantConnectorPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const [snapshot, setSnapshot] = useState<SetupSnapshot | null>(null);
  const [preview, setPreview] = useState<ConnectorPreview | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [importPromptDismissed, setImportPromptDismissed] = useState(false);

  const load = useCallback(async (live = false) => {
    if (!active) return;
    if (live) setBusy("refresh");
    const results = await Promise.allSettled([
      api.get<ConnectionSnapshot>(`/api/assistant-hub/connections${live ? "?live=true" : ""}`),
      api.get<AssistantScan>("/api/assistant-hub/status"),
      api.get<VectorSnapshot>("/api/vector/status"),
    ]);
    const unavailable = ["连接状态", "扫描结果", "向量状态"].filter((_, index) => results[index].status === "rejected");
    setSnapshot({
      connections: settled(results[0] as PromiseSettledResult<ConnectionSnapshot>),
      assistants: settled(results[1] as PromiseSettledResult<AssistantScan>),
      vector: settled(results[2] as PromiseSettledResult<VectorSnapshot>),
      unavailable,
    });
    if (unavailable.length) setMessage(`暂时无法读取：${unavailable.join("、")}。未知状态不会显示成正常。`);
    if (live) setBusy("");
  }, [active, api]);

  useEffect(() => { void load(false); }, [load]);

  const connections = snapshot?.connections;
  const assistants = snapshot?.assistants?.assistants ?? [];
  const connectors = connections?.connectors ?? [];
  const selected = useMemo(
    () => connectors.find((item) => item.id === preview?.connector_id) ?? null,
    [connectors, preview],
  );
  const readyConnector = connectors.find((item) => item.status_state === "ready" || item.live_test === true);
  const blockingConnector = connectors.find((item) => ["blocked", "conflict"].includes(item.status_state ?? ""));
  const nextConnector = connectors.find((item) => ["verification_required", "configuration_required"].includes(item.status_state ?? ""));
  const codexSource = assistants.find((item) => item.id === "codex" && item.detection_state === "detected");
  const vector = snapshot?.vector;
  const embedding = vector?.embedding;
  const vectorReady = Boolean(vector?.ready && embedding?.available);
  const importPromptVisible = Boolean(codexSource && codexSource.candidate_count > 0 && !importPromptDismissed);

  const primary = useMemo(() => {
    if (!connections?.mcp_runtime.ready) return {
      tone: "error",
      eyebrow: "当前阻塞",
      title: "先恢复灵机记忆网关",
      detail: "8767 MCP 网关未就绪，任何客户端配置都无法真正使用。先重启灵机，再重新检测。",
      action: "重新检测",
      run: () => void load(true),
    };
    if (blockingConnector) return {
      tone: "error",
      eyebrow: "当前阻塞",
      title: `${blockingConnector.label} 还不能使用灵机`,
      detail: blockingConnector.blocking_reason || "配置存在，但真实客户端验证失败。",
      action: blockingConnector.managed_by_lingji ? "修复后重新测试" : blockingConnector.next_action,
      run: () => blockingConnector.managed_by_lingji ? void test(blockingConnector.id) : void openPreview(blockingConnector.id),
    };
    if (!readyConnector && nextConnector) return {
      tone: "warning",
      eyebrow: "唯一推荐下一步",
      title: `${nextConnector.label}：${statusText(nextConnector)}`,
      detail: nextConnector.blocking_reason || "先完成一个真实客户端连接，再导入历史资料。",
      action: nextConnector.next_action,
      run: () => nextConnector.managed_by_lingji ? void test(nextConnector.id) : void openPreview(nextConnector.id),
    };
    if (importPromptVisible) return {
      tone: "warning",
      eyebrow: "发现可处理的历史资料",
      title: `已发现 Codex 数据目录，是否查看可导入内容？`,
      detail: importExplanation(codexSource!),
      action: "查看导入说明",
      run: scrollToImport,
    };
    if (!vectorReady) return {
      tone: "warning",
      eyebrow: "下一项待处理",
      title: "语义检索尚未激活",
      detail: vectorIssue(vector),
      action: "刷新状态",
      run: () => void load(true),
    };
    return {
      tone: "ok",
      eyebrow: "当前状态",
      title: "AI 连接已验证，可以开始导入和审核",
      detail: "导入仍需主人确认；导入内容只进入采集与候选链，不会自动写入 Core Memory。",
      action: "查看导入内容",
      run: scrollToImport,
    };
  }, [blockingConnector, connections?.mcp_runtime.ready, importPromptVisible, load, nextConnector, readyConnector, vector, vectorReady]);

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
      await load(true);
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

  function scrollToImport() {
    document.querySelector(".assistant-import-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

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
        label="灵机记忆网关"
        state={connections?.mcp_runtime.ready ? "可用" : "不可用"}
        tone={connections?.mcp_runtime.ready ? "ok" : "error"}
        detail="127.0.0.1:8767 · Bearer Token · 不开放公网"
      />
      <ReadinessItem
        label="真实 AI 客户端"
        state={readyConnector ? `${readyConnector.label} 已验证` : "尚无连接通过"}
        tone={readyConnector ? "ok" : blockingConnector ? "error" : "warning"}
        detail={blockingConnector?.blocking_reason || nextConnector?.blocking_reason || "配置文件存在不等于客户端可用"}
      />
      <ReadinessItem
        label="历史导入"
        state={codexSource ? `发现 ${codexSource.candidate_count.toLocaleString()} 个候选文件` : "等待选择来源"}
        tone={codexSource ? "warning" : "neutral"}
        detail="扫描只读元数据；读取正文和导入必须再次确认"
      />
      <ReadinessItem
        label="Embedding / Qdrant"
        state={vectorReady ? "语义检索可用" : `${humanState(embedding?.state)} / ${humanState(vector?.state)}`}
        tone={vectorReady ? "ok" : "warning"}
        detail={vectorReady ? `模型 ${embedding?.active_model || embedding?.configured_model || "已激活"}` : vectorIssue(vector)}
      />
    </div>

    {importPromptVisible && codexSource && <div className="assistant-import-consent" role="status">
      <div>
        <strong>灵机发现了 Codex 本地历史目录，但还没有读取正文</strong>
        <p>{importExplanation(codexSource)}</p>
      </div>
      <div className="assistant-connector-actions">
        <button className="button secondary" onClick={() => setImportPromptDismissed(true)}>暂不处理</button>
        <button className="button" onClick={scrollToImport}>查看可导入内容</button>
      </div>
    </div>}

    <div className="assistant-section-heading">
      <div>
        <span className="desktop-eyebrow">让 AI 真正使用灵机记忆</span>
        <h3>配置、客户端命令、真实测试分开显示</h3>
        <p>连接不等于导入历史。配置文件写入成功也不等于客户端可用，只有真实测试通过才显示绿色。</p>
      </div>
      <button className="button secondary" disabled={!active || busy !== ""} onClick={() => void load(true)}>重新检测全部状态</button>
    </div>

    <div className={connections?.mcp_runtime.ready ? "assistant-runtime-card ready" : "assistant-runtime-card warning"}>
      <div>
        <strong>{connections?.mcp_runtime.ready ? "灵机记忆网关已运行" : "灵机记忆网关未运行"}</strong>
        <small>本机 127.0.0.1:8767 · Bearer Token 认证 · 不开放公网</small>
      </div>
      <span className={`pill ${connections?.mcp_runtime.ready ? "ok" : "warning"}`}>
        {connections?.mcp_runtime.ready ? "可连接" : "需要重启灵机"}
      </span>
    </div>

    <div className="assistant-connector-grid">
      {connectors.map((connector) => <article className={`assistant-connector-card ${tone(connector)}`} key={connector.id}>
        <header>
          <div><h4>{connector.label}</h4><small>{connector.target}</small></div>
          <span className={`pill ${tone(connector)}`}>{statusText(connector)}</span>
        </header>
        <dl className="assistant-connector-facts">
          <div><dt>配置文件</dt><dd>{connector.managed_by_lingji ? "已写入" : "未由灵机管理"}</dd></div>
          <div><dt>客户端命令</dt><dd>{connector.client_available === true ? "已找到" : connector.client_available === false ? "未找到" : "需在软件内确认"}</dd></div>
          <div><dt>真实测试</dt><dd>{connector.live_test === true ? "通过" : connector.live_test === false ? "失败" : "未完成"}</dd></div>
        </dl>
        <p className={tone(connector) === "error" ? "assistant-connector-problem" : ""}>
          {connector.blocking_reason || connector.last_test_detail || connector.next_action}
        </p>
        <div className="assistant-connector-next"><span>下一步</span><strong>{connector.next_action}</strong></div>
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

    {message && <div className={message.includes("失败") || message.includes("找不到") || message.includes("未找到") ? "assistant-hub-notice error" : "assistant-hub-notice"}>{message}</div>}
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
  const embedding = vector.embedding;
  const configured = embedding?.configured_model || embedding?.primary_model || "未配置模型";
  if (embedding?.last_error) return `Embedding ${configured} 未激活：${embedding.last_error}`;
  if (embedding?.unavailable_models?.length) return `Embedding 模型不可用：${embedding.unavailable_models.join("、")}。全文检索仍可用。`;
  if (!embedding?.available) return `Embedding 已配置为 ${configured}，但尚未验证或激活；全文检索仍可用。`;
  if (vector.rebuild_required) return "Embedding 已可用，但 Qdrant Collection 合同发生变化，需要安全重建。";
  if (vector.last_error) return `Qdrant ${humanState(vector.state)}：${vector.last_error}`;
  if (!vector.ready) return `Qdrant 当前为 ${humanState(vector.state)}（${vector.mode || "模式未知"}），语义检索尚未就绪。`;
  return "语义检索状态未知；全文检索仍可用。";
}
