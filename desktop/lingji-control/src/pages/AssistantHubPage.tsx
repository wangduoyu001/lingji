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
  detected: "已检测到",
  not_found: "未检测到",
  manual_export: "需要导出文件",
  available: "可导入",
  planned: "适配中",
  configuration_required: "需要设置",
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

  useEffect(() => { void load(false); }, [load]);

  const chooseFile = async (mode: ImportMode) => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: false,
        title: mode === "chatgpt_export" ? "选择 ChatGPT 导出文件" : "选择 Codex Report",
        filters: mode === "chatgpt_export"
          ? [{ name: "ChatGPT Export", extensions: ["zip", "json"] }]
          : [{ name: "Codex Report", extensions: ["json"] }],
      });
      if (typeof selected === "string") setPaths((value) => ({ ...value, [mode]: selected }));
    } catch {
      setResult("文件选择仅在安装版灵机中可用。请使用 Windows 安装包验收。");
    }
  };

  const submitImport = async (mode: ImportMode) => {
    const inputPath = paths[mode];
    if (!inputPath) {
      setResult("请先选择导出文件。");
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
        metadata: { origin: "assistant_hub" },
      });
      setResult(response.duplicate
        ? "这份内容已经提交过，没有重复创建任务。"
        : `已进入采集队列${response.job_id ? `：${response.job_id}` : ""}。处理完成后到“人工记忆审核”确认长期记忆。`);
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "导入失败");
      setResult(`导入失败：${apiError.message}`);
    } finally {
      setBusy("");
    }
  };

  if (!active) return <div className="assistant-hub-state">连接本机核心后才能扫描、连接和导入 AI 资料。</div>;

  return <div className="assistant-hub-page">
    <section className="assistant-onboarding-hero">
      <div>
        <span className="desktop-eyebrow">第一次使用从这里开始</span>
        <h2>把你正在使用的 AI 接入灵机</h2>
        <p>先扫描本机工具，再连接今后的记忆调用，最后导入已有历史。三个动作含义不同，灵机不会混成一个绿色假状态。</p>
      </div>
      <button className="button primary" disabled={busy === "scan"} onClick={() => void load(true)}>
        {busy === "scan" ? "扫描中…" : "扫描我的 AI 软件"}
      </button>
    </section>

    {error && <div className="assistant-hub-notice error">{error}</div>}

    <section className="assistant-setup-flow" aria-label="首次设置流程">
      <div><strong>1</strong><span><b>扫描</b><small>只确认安装和可用能力，不读取对话正文。</small></span></div>
      <div><strong>2</strong><span><b>连接</b><small>让 AI 今后通过 MCP 读取灵机记忆、提交候选记忆。</small></span></div>
      <div><strong>3</strong><span><b>导入</b><small>把 ChatGPT Export、Codex Report 等旧资料放进处理队列。</small></span></div>
      <div><strong>4</strong><span><b>审核</b><small>只有你确认的候选才成为正式永久记忆。</small></span></div>
    </section>

    {scan && <>
      <section className="assistant-scan-summary">
        <div><span>当前工作空间</span><strong>{scan.workspace || "未知"}</strong></div>
        <div><span>检测到工具</span><strong>{scan.summary.detected}</strong></div>
        <div><span>当前可导入</span><strong>{scan.summary.import_ready + scan.summary.requires_manual_export}</strong></div>
        <div><span>待开发适配器</span><strong>{scan.summary.planned}</strong></div>
        <small>扫描时间：{time(scan.scanned_at)}</small>
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
            {assistant.discovered_paths.map((path) => <code key={path}>{path}</code>)}
          </div>}
          <footer>{assistant.next_action}</footer>
        </article>)}
      </section>
    </>}

    <AssistantConnectorPanel api={api} active={active} />

    <section className="assistant-import-section">
      <div className="assistant-section-heading">
        <div><span className="desktop-eyebrow">导入已有历史</span><h3>选择导出文件，剩下的交给采集队列</h3></div>
        <button className="button secondary" onClick={() => onNavigate("activity")}>查看导入进度</button>
      </div>
      <div className="assistant-import-grid">
        <ImportCard
          title="ChatGPT 历史"
          detail="支持官方导出的 ZIP 或 conversations JSON。"
          path={paths.chatgpt_export}
          busy={busy === "import:chatgpt_export"}
          onChoose={() => void chooseFile("chatgpt_export")}
          onSubmit={() => void submitImport("chatgpt_export")}
        />
        <ImportCard
          title="Codex 工作报告"
          detail="支持灵机/Codex 生成的结构化 JSON 工作报告。"
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
        <h3>默认先审核，不把全部聊天直接写进核心记忆</h3>
        <p>连接后的 AI 可以读取你批准的记忆，也可以提交候选；导入资料会保留来源并进入处理链。只有你在“人工记忆审核”中确认的内容，才成为正式长期记忆。</p>
      </div>
      <div className="assistant-policy-list">
        <span>✓ AI 可读取主人批准的记忆</span>
        <span>✓ AI 可提交候选记忆</span>
        <span>✓ 原始资料保留来源并自动去重</span>
        <span>× 不读取账号 Token 或浏览器登录态</span>
        <span>× 不允许 AI 直接写入 Core Memory</span>
      </div>
      <button className="button" onClick={() => onNavigate("memory_review")}>进入人工记忆审核</button>
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
    <code>{path || "尚未选择文件"}</code>
    <div>
      <button className="button secondary" onClick={onChoose}>选择文件</button>
      <button className="button" disabled={!path || busy} onClick={onSubmit}>{busy ? "提交中…" : "导入到灵机"}</button>
    </div>
  </article>;
}
