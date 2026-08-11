import { useCallback, useMemo, useState } from "react";
import type { LingJiApi } from "../api";
import { ApiError } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";

type ImportCandidate = {
  candidate_id: string;
  source_id: string;
  display_name: string;
  size_bytes: number;
  modified_at: string | null;
};

type ImportSource = {
  id: string;
  label: string;
  state: string;
  supported: boolean;
  primary_action: string;
  guide: string;
  candidates: ImportCandidate[];
};

type AssistantRecord = {
  id: string;
  label: string;
  detection_state: string;
  candidate_count: number;
  latest_activity_at: string | null;
  message: string;
};

type AssistantScan = {
  scanned_at: string;
  safety: {
    read_only: boolean;
    content_read: boolean;
    automatic_core_memory_write: boolean;
  };
  summary: {
    assistant_count: number;
    detected: number;
    import_ready: number;
  };
  assistants: AssistantRecord[];
  import_plan?: {
    summary: {
      candidate_count: number;
      automatic_ready: number;
      guided_sources: number;
    };
    sources: ImportSource[];
  };
};

type CaptureSubmission = {
  job_id?: string;
  duplicate?: boolean;
};

const time = (value?: string | null) => value ? new Date(value).toLocaleString() : "暂无";
const size = (value: number) => value >= 1024 * 1024
  ? `${(value / 1024 / 1024).toFixed(1)} MB`
  : `${Math.max(1, Math.round(value / 1024))} KB`;

function stateLabel(state: string): string {
  if (state === "detected") return "已自动识别";
  if (state === "manual_export") return "支持官方导出";
  if (state === "not_found") return "未发现";
  return state || "未知";
}

export default function AssistantDiscoveryPanel({
  api,
  active,
  onOpenCodex,
  onOpenActivity,
}: {
  api: LingJiApi;
  active: boolean;
  onOpenCodex: () => void;
  onOpenActivity: () => void;
}) {
  const fetcher = useCallback(
    (signal: AbortSignal) => api.get<AssistantScan>("/api/assistant-hub/status", { signal }),
    [api],
  );
  const resource = usePollingResource({
    fetcher,
    enabled: active,
    intervalMs: 15_000,
    staleAfterMs: 45_000,
    pauseWhenHidden: true,
  });
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const detected = useMemo(
    () => resource.data?.assistants.filter((assistant) => assistant.detection_state === "detected") ?? [],
    [resource.data],
  );
  const importSource = useMemo(
    () => resource.data?.import_plan?.sources.find((source) => source.candidates.length > 0) ?? null,
    [resource.data],
  );

  async function authorizeCandidate(candidate: ImportCandidate) {
    if (busy) return;
    setBusy(candidate.candidate_id);
    setMessage("");
    try {
      const response = await api.post<CaptureSubmission>(
        `/api/assistant-hub/import-candidates/${candidate.candidate_id}/authorize`,
        { confirmation: `AUTHORIZE_ASSISTANT_IMPORT_${candidate.candidate_id.toUpperCase()}` },
      );
      setMessage(response.duplicate
        ? "这份资料已经处理过，灵机没有重复创建任务。"
        : `已进入自动整理队列${response.job_id ? ` · ${response.job_id}` : ""}。`);
      await resource.refresh();
    } catch (reason) {
      const error = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "导入失败");
      setMessage(`暂时无法导入：${error.message}`);
    } finally {
      setBusy("");
    }
  }

  async function chooseAndImport(source: ImportSource) {
    if (busy || !source.supported) return;
    setMessage("");
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: false,
        title: source.id === "chatgpt" ? "选择 ChatGPT 官方导出包" : "选择 Codex 工作报告",
        filters: source.id === "chatgpt"
          ? [{ name: "ChatGPT Export", extensions: ["zip", "json"] }]
          : [{ name: "Codex Work Report", extensions: ["json"] }],
      });
      if (typeof selected !== "string") return;
      setBusy(source.id);
      const response = await api.post<CaptureSubmission>("/api/assistant-hub/import-selected-file", {
        input_path: selected,
        source_id: source.id,
        confirmation: "AUTHORIZE_SELECTED_ASSISTANT_IMPORT",
      });
      setMessage(response.duplicate
        ? "这份资料已经处理过，灵机没有重复创建任务。"
        : `已进入自动整理队列${response.job_id ? ` · ${response.job_id}` : ""}。`);
      await resource.refresh();
    } catch (reason) {
      const error = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "导入失败");
      setMessage(`暂时无法导入：${error.message}`);
    } finally {
      setBusy("");
    }
  }

  if (!active) return null;

  return (
    <section className="assistant-autopilot-panel">
      <div className="assistant-autopilot-heading">
        <div>
          <span className="desktop-eyebrow">自动发现</span>
          <h2>灵机正在自己检查这台电脑</h2>
          <p>只扫描已知位置和文件元数据。没有你的允许，不会读取真实对话正文，也不会自动写入永久记忆。</p>
        </div>
        <div className="assistant-autopilot-live">
          <span className={resource.error ? "status-dot" : "status-dot online"} />
          <div>
            <strong>{resource.loading ? "首次扫描中" : resource.refreshing ? "正在更新" : "后台自动扫描"}</strong>
            <small>约每 15 秒更新</small>
          </div>
        </div>
      </div>

      {resource.data && (
        <div className="assistant-autopilot-summary">
          <div><span>已识别 AI 工具</span><strong>{resource.data.summary.detected}</strong></div>
          <div><span>发现可导入资料</span><strong>{resource.data.import_plan?.summary.candidate_count ?? 0}</strong></div>
          <div><span>已读取正文</span><strong>{resource.data.safety.content_read ? "是" : "否"}</strong></div>
          <div><span>最近扫描</span><strong>{time(resource.data.scanned_at)}</strong></div>
        </div>
      )}

      {resource.error && (
        <div className="assistant-autopilot-note warning">
          自动扫描暂时失败，灵机会继续重试。日常使用不需要你手动刷新。
        </div>
      )}

      <div className="assistant-autopilot-tools">
        {detected.length ? detected.map((assistant) => (
          <article className="assistant-autopilot-tool" key={assistant.id}>
            <div>
              <strong>{assistant.label}</strong>
              <span className="pill ok">{stateLabel(assistant.detection_state)}</span>
            </div>
            <p>{assistant.message}</p>
            {assistant.id === "codex" && (
              <button className="text-button" onClick={onOpenCodex}>
                查看已识别的 Codex 工作记录
              </button>
            )}
          </article>
        )) : (
          <div className="assistant-autopilot-empty">
            <strong>{resource.loading ? "正在识别本机 AI 工具…" : "暂未识别到本机 AI 工具"}</strong>
            <p>灵机会继续在后台检查，不需要逐个配置扫描路径。</p>
          </div>
        )}
      </div>

      {importSource && importSource.candidates[0] && (
        <div className="assistant-autopilot-action">
          <div>
            <span className="desktop-eyebrow">需要你决定</span>
            <strong>发现 {importSource.label}</strong>
            <p>
              {importSource.candidates[0].display_name} · {size(importSource.candidates[0].size_bytes)}
              {" · "}灵机目前只看到了文件元数据，读取内容前需要你确认。
            </p>
          </div>
          <button
            className="button primary"
            disabled={Boolean(busy)}
            onClick={() => void authorizeCandidate(importSource.candidates[0])}
          >
            {busy ? "正在交给灵机…" : "允许读取并自动整理"}
          </button>
        </div>
      )}

      {!importSource && resource.data?.import_plan && (
        <details className="assistant-autopilot-more">
          <summary>手动导入入口</summary>
          <div className="assistant-autopilot-import-grid">
            {resource.data.import_plan.sources
              .filter((source) => source.supported)
              .map((source) => (
                <button
                  className="assistant-autopilot-import-button"
                  key={source.id}
                  disabled={Boolean(busy)}
                  onClick={() => void chooseAndImport(source)}
                >
                  <strong>{source.label}</strong>
                  <small>{source.guide}</small>
                </button>
              ))}
          </div>
        </details>
      )}

      {message && <div className="assistant-autopilot-note">{message}</div>}

      <div className="assistant-autopilot-footer">
        <span>扫描安全边界：元数据只读 · 不自动读取正文 · 不自动批准永久记忆</span>
        <button className="text-button" onClick={onOpenActivity}>查看自动处理记录</button>
      </div>
    </section>
  );
}
