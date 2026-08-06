import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../api";
import AssistantConnectorPanel from "../components/AssistantConnectorPanel";
import type { PageId, PageProps } from "../types";
import "./AssistantHubPage.css";

type AssistantState = "detected" | "not_found" | "manual_export" | string;
type ImportState = "available" | "manual_export" | "planned" | string;

type ImportCandidate = {
  candidate_id: string;
  source_id: string;
  source_type: string;
  adapter_name: string;
  display_name: string;
  size_bytes: number;
  modified_at: string | null;
};

type ImportSource = {
  id: string;
  label: string;
  state: "candidate_ready" | "guided_action_required" | "not_supported" | string;
  supported: boolean;
  automatic_candidate_available: boolean;
  owner_action_count: number;
  primary_action: string;
  guide: string;
  candidates: ImportCandidate[];
};

type ImportPlan = {
  scanned_at: string;
  safety: {
    metadata_only: boolean;
    content_read: boolean;
    arbitrary_path_submission: boolean;
    owner_authorization_required: boolean;
    automatic_core_memory_write: boolean;
  };
  summary: {
    candidate_count: number;
    automatic_ready: number;
    guided_sources: number;
  };
  sources: ImportSource[];
};

type AssistantRecord = {
  id: string;
  label: string;
  detection_state: AssistantState;
  connection_state: string;
  import_state: ImportState;
  sync_state: string;
  discovered_paths: string[];
  candidate_count: number;
  latest_activity_at: string | null;
  import_modes: string[];
  capabilities: Record<string, unknown>;
  message: string;
  next_action: string;
};

type AssistantScan = {
  workspace: string;
  scanned_at: string;
  safety: {
    read_only: boolean;
    content_read: boolean;
    automatic_core_memory_write: boolean;
    review_required_for_permanent_memory: boolean;
  };
  summary: {
    assistant_count: number;
    detected: number;
    import_ready: number;
    requires_manual_export: number;
    planned: number;
  };
  assistants: AssistantRecord[];
  import_plan?: ImportPlan;
};

type CaptureSubmission = {
  job_id?: string;
  duplicate?: boolean;
  status?: string;
  capture_id?: string;
};

type Props = PageProps & { onNavigate: (page: PageId) => void };

const stateLabel = (state: string): string => ({
  detected: "已自动检测",
  not_found: "未检测到",
  manual_export: "需要官方导出包",
  available: "支持导入",
  planned: "适配中",
  configuration_required: "等待配置授权",
  unavailable: "暂不可用",
}[state] ?? state);

const stateTone = (state: string): string => {
  if (["detected", "available", "healthy", "ready", "candidate_ready"].includes(state)) return "ok";
  if (["planned", "manual_export", "configuration_required", "guided_action_required"].includes(state)) return "warning";
  if (["failed", "blocked"].includes(state)) return "error";
  return "neutral";
};

const time = (value: string | null): string => value ? new Date(value).toLocaleString() : "暂无";
const size = (value: number): string => value >= 1024 * 1024
  ? `${(value / 1024 / 1024).toFixed(1)} MB`
  : `${Math.max(Math.round(value / 1024), 1)} KB`;

export default function AssistantHubPage({ api, active, onNavigate }: Props) {
  const [scan, setScan] = useState<AssistantScan | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState("");

  const load = useCallback(async (rescan = false) => {
    if (!active) return;
    setBusy("scan");
    setError("");
    try {
      setScan(rescan
        ? await api.post<AssistantScan>("/api/assistant-hub/scan")
        : await api.get<AssistantScan>("/api/assistant-hub/status"));
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "扫描失败");
      setError(apiError.message || "无法扫描本机 AI 工具");
    } finally {
      setBusy("");
    }
  }, [active, api]);

  useEffect(() => { void load(true); }, [load]);

  const importPlan = scan?.import_plan ?? null;
  const primaryImport = useMemo(() => {
    if (!importPlan) return null;
    return importPlan.sources.find((source) => source.state === "candidate_ready")
      ?? importPlan.sources.find((source) => source.state === "guided_action_required")
      ?? null;
  }, [importPlan]);

  const authorizeCandidate = async (candidate: ImportCandidate) => {
    setBusy(`candidate:${candidate.candidate_id}`);
    setResult("");
    try {
      const response = await api.post<CaptureSubmission>(
        `/api/assistant-hub/import-candidates/${candidate.candidate_id}/authorize`,
        { confirmation: `AUTHORIZE_ASSISTANT_IMPORT_${candidate.candidate_id.toUpperCase()}` },
      );
      setResult(response.duplicate
        ? `${candidate.display_name} 已处理过，灵机没有重复创建任务。`
        : `${candidate.display_name} 已获授权并进入处理队列${response.job_id ? `：${response.job_id}` : ""}。后续解析、去重和失败重试由灵机完成。`);
      await load(false);
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "导入失败");
      setResult(`导入失败：${apiError.message}`);
    } finally {
      setBusy("");
    }
  };

  const chooseAndImport = async (source: ImportSource) => {
    setResult("");
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: false,
        title: source.id === "chatgpt"
          ? "选择 ChatGPT 官方导出包，选中后立即导入"
          : "选择 Codex Work Report，选中后立即导入",
        filters: source.id === "chatgpt"
          ? [{ name: "ChatGPT Export", extensions: ["zip", "json"] }]
          : [{ name: "Codex Work Report", extensions: ["json"] }],
      });
      if (typeof selected !== "string") return;
      setBusy(`selected:${source.id}`);
      const response = await api.post<CaptureSubmission>("/api/assistant-hub/import-selected-file", {
        input_path: selected,
        source_id: source.id,
        confirmation: "AUTHORIZE_SELECTED_ASSISTANT_IMPORT",
      });
      setResult(response.duplicate
        ? "这份内容已经处理过，灵机没有重复创建任务。"
        : `文件已获授权并进入处理队列${response.job_id ? `：${response.job_id}` : ""}。不需要再次点击提交。`);
      await load(false);
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "导入失败");
      setResult(`导入失败：${apiError.message}`);
    } finally {
      setBusy("");
    }
  };

  const runImport = (source: ImportSource) => {
    const candidate = source.candidates[0];
    if (candidate) {
      void authorizeCandidate(candidate);
      return;
    }
    if (source.supported) void chooseAndImport(source);
  };

  if (!active) return <div className="assistant-hub-state">灵机核心连接后会自动扫描、连接和汇总 AI 来源。</div>;

  return <div className="assistant-hub-page">
    <section className="assistant-onboarding-hero">
      <div>
        <span className="desktop-eyebrow">自动运行观察台</span>
        <h2>灵机正在主动发现 AI 来源并准备导入</h2>
        <p>
          安装检测、受支持导出包的元数据扫描、连接检查、状态刷新和失败重试由灵机自动执行。
          你只在读取真实正文前授权一次，之后不需要填写路径或再次提交。
        </p>
      </div>
      <button className="button secondary" disabled={busy === "scan"} onClick={() => void load(true)}>
        {busy === "scan" ? "自动扫描中…" : "立即重新扫描"}
      </button>
    </section>

    {error && <div className="assistant-hub-notice error">{error}</div>}

    <section className="assistant-setup-flow" aria-label="灵机自动处理流程">
      <div><strong>1</strong><span><b>自动发现</b><small>查找安装、目录和受支持导出包，只读取元数据。</small></span></div>
      <div><strong>2</strong><span><b>自动判断</b><small>区分可直接授权导入、需要一步选择和暂不支持。</small></span></div>
      <div><strong>3</strong><span><b>一次授权</b><small>授权后立即入队，不再要求填写路径或二次提交。</small></span></div>
      <div><strong>4</strong><span><b>自动处理</b><small>解析、去重、进度和重试由灵机维护，永久记忆仍由你定稿。</small></span></div>
    </section>

    {scan && <>
      <section className="assistant-scan-summary">
        <div><span>当前工作空间</span><strong>{scan.workspace || "未知"}</strong></div>
        <div><span>自动检测到工具</span><strong>{scan.summary.detected}</strong></div>
        <div><span>可一步授权的导出包</span><strong>{importPlan?.summary.candidate_count ?? 0}</strong></div>
        <div><span>需要一步选择的来源</span><strong>{importPlan?.summary.guided_sources ?? 0}</strong></div>
        <small>最近自动扫描：{time(scan.scanned_at)} · 未读取任何对话正文</small>
      </section>

      {primaryImport && <section className={`assistant-primary-import ${stateTone(primaryImport.state)}`}>
        <div>
          <span className="desktop-eyebrow">当前导入动作</span>
          <h3>{primaryImport.label}</h3>
          <p>{primaryImport.guide}</p>
          {primaryImport.candidates[0] && <small>
            已发现：{primaryImport.candidates[0].display_name} · {size(primaryImport.candidates[0].size_bytes)} · {time(primaryImport.candidates[0].modified_at)}
          </small>}
        </div>
        <button
          className="button primary"
          disabled={busy !== ""}
          onClick={() => runImport(primaryImport)}
        >
          {busy.startsWith("candidate:") || busy.startsWith("selected:") ? "灵机接管中…" : primaryImport.primary_action}
        </button>
      </section>}

      <section className="assistant-card-grid">
        {scan.assistants.map((assistant) => <article className="assistant-card" key={assistant.id}>
          <header>
            <div><span className="assistant-card-mark">{assistant.label.slice(0, 1)}</span><h3>{assistant.label}</h3></div>
            <span className={`pill ${stateTone(assistant.detection_state)}`}>{stateLabel(assistant.detection_state)}</span>
          </header>
          <p>{assistant.message}</p>
          <dl>
            <div><dt>历史导入</dt><dd>{stateLabel(assistant.import_state)}</dd></div>
            <div><dt>自动同步</dt><dd>{stateLabel(assistant.sync_state)}</dd></div>
            <div><dt>元数据候选</dt><dd>{assistant.candidate_count.toLocaleString()}</dd></div>
            <div><dt>最近活动</dt><dd>{time(assistant.latest_activity_at)}</dd></div>
          </dl>
          <footer>{assistant.next_action}</footer>
        </article>)}
      </section>
    </>}

    <AssistantConnectorPanel api={api} active={active} />

    {importPlan && <section className="assistant-import-section">
      <div className="assistant-section-heading">
        <div>
          <span className="desktop-eyebrow">导入来源</span>
          <h3>能自动发现的直接授权，不能自动发现的只保留一个动作</h3>
          <p>页面不会要求你手工填写路径，也不会在选完文件后再让你点击一次提交。</p>
        </div>
        <button className="button secondary" onClick={() => onNavigate("activity")}>查看自动处理进度</button>
      </div>
      <div className="assistant-import-grid">
        {importPlan.sources.map((source) => <article className={`assistant-import-card ${source.state}`} key={source.id}>
          <div>
            <div className="assistant-import-title-line">
              <h4>{source.label}</h4>
              <span className={`pill ${stateTone(source.state)}`}>
                {source.state === "candidate_ready" ? "已发现导出包" : source.state === "guided_action_required" ? "一步选择" : "暂不支持"}
              </span>
            </div>
            <p>{source.guide}</p>
          </div>
          {source.candidates[0] && <div className="assistant-import-candidate">
            <strong>{source.candidates[0].display_name}</strong>
            <small>{size(source.candidates[0].size_bytes)} · {time(source.candidates[0].modified_at)}</small>
          </div>}
          {source.supported && <button
            className="button"
            disabled={busy !== ""}
            onClick={() => runImport(source)}
          >
            {busy === `candidate:${source.candidates[0]?.candidate_id}` || busy === `selected:${source.id}`
              ? "灵机接管中…"
              : source.primary_action}
          </button>}
        </article>)}
      </div>
      {result && <div className="assistant-hub-notice">{result}</div>}
    </section>}

    <section className="assistant-memory-policy">
      <div>
        <span className="desktop-eyebrow">永久记忆规则</span>
        <h3>灵机自动整理，主人只负责最终批准</h3>
        <p>导入资料会自动保留来源、去重并进入处理链。只有你在“人工记忆审核”中确认的内容，才成为正式长期记忆。</p>
      </div>
      <div className="assistant-policy-list">
        <span>✓ 自动扫描安装、目录和受支持导出包元数据</span>
        <span>✓ 一次授权后自动入队、解析、去重和失败重试</span>
        <span>✓ 不支持的来源明确说明，不展示无效按钮</span>
        <span>× 未授权不读取真实正文</span>
        <span>× 不允许 AI 直接写入 Core Memory</span>
      </div>
      <button className="button secondary" onClick={() => onNavigate("memory_review")}>查看待批准候选</button>
    </section>
  </div>;
}
