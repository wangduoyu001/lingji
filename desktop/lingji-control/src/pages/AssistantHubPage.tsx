import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api";
import AssistantConnectorPanel from "../components/AssistantConnectorPanel";
import type { PageId, PageProps } from "../types";
import "./AssistantHubPage.css";

type AssistantState = "detected" | "not_found" | "manual_export" | string;
type ImportState = "available" | "manual_export" | "planned" | string;

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
};

type ImportMode = "chatgpt_export" | "codex_report";
type CaptureSubmission = { job_id?: string; duplicate?: boolean; status?: string; capture_id?: string };

type Props = PageProps & { onNavigate: (page: PageId) => void };

const stateLabel = (state: string): string => ({
  detected: "已自动检测",
  not_found: "未检测到",
  manual_export: "等待主人提供导出文件",
  available: "可在授权后导入",
  planned: "适配中",
  configuration_required: "等待配置授权",
  unavailable: "暂不可用",
}[state] ?? state);

const stateTone = (state: string): string => {
  if (["detected", "available", "healthy", "ready"].includes(state)) return "ok";
  if (["planned", "manual_export", "configuration_required"].includes(state)) return "warning";
  return "neutral";
};

const time = (value: string | null): string => value ? new Date(value).toLocaleString() : "暂无";

export default function AssistantHubPage({ api, active, onNavigate }: Props) {
  const [scan, setScan] = useState<AssistantScan | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [paths, setPaths] = useState<Record<ImportMode, string>>({ chatgpt_export: "", codex_report: "" });
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

  const chooseFile = async (mode: ImportMode) => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: false,
        title: mode === "chatgpt_export" ? "授权灵机读取 ChatGPT 导出文件" : "授权灵机读取 Codex Report",
        filters: mode === "chatgpt_export"
          ? [{ name: "ChatGPT Export", extensions: ["zip", "json"] }]
          : [{ name: "Codex Report", extensions: ["json"] }],
      });
      if (typeof selected === "string") setPaths((value) => ({ ...value, [mode]: selected }));
    } catch {
      setResult("文件授权仅在安装版灵机中可用。请使用 Windows 安装包验收。");
    }
  };

  const submitImport = async (mode: ImportMode) => {
    const inputPath = paths[mode];
    if (!inputPath) {
      setResult("请先授权一个导出文件。");
      return;
    }
    setBusy(`import:${mode}`);
    setResult("");
    try {
      const response = await api.post<CaptureSubmission>("/api/capture/file", {
        input_path: inputPath,
        source_type: mode,
        adapter_name: mode === "chatgpt_export" ? "chatgpt_export" : "codex_work_report",
        privacy: "private",
        process_later: true,
        metadata: { origin: "assistant_hub", owner_authorized: true },
      });
      setResult(response.duplicate
        ? "这份内容已经提交过，灵机没有重复创建任务。"
        : `授权已记录，灵机已接管后续处理${response.job_id ? `：${response.job_id}` : ""}。候选长期记忆仍需主人最终确认。`);
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "导入失败");
      setResult(`导入失败：${apiError.message}`);
    } finally {
      setBusy("");
    }
  };

  if (!active) return <div className="assistant-hub-state">灵机核心连接后会自动扫描、连接和汇总 AI 来源。</div>;

  return <div className="assistant-hub-page">
    <section className="assistant-onboarding-hero">
      <div>
        <span className="desktop-eyebrow">自动运行观察台</span>
        <h2>灵机正在主动发现和维护 AI 连接</h2>
        <p>
          安装检测、历史目录元数据扫描、状态刷新和失败重试由灵机自动执行。
          这里只有读取真实正文、修改外部客户端配置和写入永久记忆时才需要你的授权。
        </p>
      </div>
      <button className="button secondary" disabled={busy === "scan"} onClick={() => void load(true)}>
        {busy === "scan" ? "自动扫描中…" : "立即重新扫描"}
      </button>
    </section>

    {error && <div className="assistant-hub-notice error">{error}</div>}

    <section className="assistant-setup-flow" aria-label="灵机自动处理流程">
      <div><strong>1</strong><span><b>自动发现</b><small>确认安装和可用能力，不读取对话正文。</small></span></div>
      <div><strong>2</strong><span><b>自动检查</b><small>验证命令、配置状态和连接条件，失败会后台重试。</small></span></div>
      <div><strong>3</strong><span><b>授权读取</b><small>发现可导入资料后，只在读取正文前请求主人确认。</small></span></div>
      <div><strong>4</strong><span><b>主人定稿</b><small>只有你确认的候选才成为正式永久记忆。</small></span></div>
    </section>

    {scan && <>
      <section className="assistant-scan-summary">
        <div><span>当前工作空间</span><strong>{scan.workspace || "未知"}</strong></div>
        <div><span>自动检测到工具</span><strong>{scan.summary.detected}</strong></div>
        <div><span>等待授权来源</span><strong>{scan.summary.import_ready + scan.summary.requires_manual_export}</strong></div>
        <div><span>待开发适配器</span><strong>{scan.summary.planned}</strong></div>
        <small>最近自动扫描：{time(scan.scanned_at)}</small>
      </section>

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
            <div><dt>候选文件</dt><dd>{assistant.candidate_count.toLocaleString()}</dd></div>
            <div><dt>最近活动</dt><dd>{time(assistant.latest_activity_at)}</dd></div>
          </dl>
          {assistant.discovered_paths.length > 0 && <div className="assistant-path-list">
            <small>已发现以下来源，仅读取了路径和数量元数据：</small>
            {assistant.discovered_paths.map((path) => <code key={path}>{path}</code>)}
          </div>}
          <footer>{assistant.next_action}</footer>
        </article>)}
      </section>
    </>}

    <AssistantConnectorPanel api={api} active={active} />

    <section className="assistant-import-section">
      <div className="assistant-section-heading">
        <div>
          <span className="desktop-eyebrow">需要主人授权的边界</span>
          <h3>选择一次来源，后续解析、去重、入队和进度维护由灵机完成</h3>
        </div>
        <button className="button secondary" onClick={() => onNavigate("activity")}>查看自动处理进度</button>
      </div>
      <div className="assistant-import-grid">
        <ImportCard
          title="ChatGPT 历史"
          detail="授权读取官方导出的 ZIP 或 conversations JSON。"
          path={paths.chatgpt_export}
          busy={busy === "import:chatgpt_export"}
          onChoose={() => void chooseFile("chatgpt_export")}
          onSubmit={() => void submitImport("chatgpt_export")}
        />
        <ImportCard
          title="Codex 工作报告"
          detail="授权读取灵机/Codex 生成的结构化 JSON 工作报告。"
          path={paths.codex_report}
          busy={busy === "import:codex_report"}
          onChoose={() => void chooseFile("codex_report")}
          onSubmit={() => void submitImport("codex_report")}
        />
      </div>
      {result && <div className="assistant-hub-notice">{result}</div>}
    </section>

    <section className="assistant-memory-policy">
      <div>
        <span className="desktop-eyebrow">永久记忆规则</span>
        <h3>灵机自动整理，主人只负责最终批准</h3>
        <p>连接后的 AI 可以读取你批准的记忆，也可以提交候选；导入资料会自动保留来源、去重和进入处理链。只有你在“人工记忆审核”中确认的内容，才成为正式长期记忆。</p>
      </div>
      <div className="assistant-policy-list">
        <span>✓ 自动扫描安装和历史目录元数据</span>
        <span>✓ 自动检测连接、模型和运行状态</span>
        <span>✓ 自动解析、去重、排队和失败重试</span>
        <span>× 未授权不读取真实正文</span>
        <span>× 不允许 AI 直接写入 Core Memory</span>
      </div>
      <button className="button secondary" onClick={() => onNavigate("memory_review")}>查看待批准候选</button>
    </section>
  </div>;
}

function ImportCard({
  title,
  detail,
  path,
  busy,
  onChoose,
  onSubmit,
}: {
  title: string;
  detail: string;
  path: string;
  busy: boolean;
  onChoose: () => void;
  onSubmit: () => void;
}) {
  return <article className="assistant-import-card">
    <div><h4>{title}</h4><p>{detail}</p></div>
    <code>{path || "尚未授权文件"}</code>
    <div>
      <button className="button secondary" onClick={onChoose}>授权文件</button>
      <button className="button" disabled={!path || busy} onClick={onSubmit}>{busy ? "灵机接管中…" : "授权并交给灵机"}</button>
    </div>
  </article>;
}
