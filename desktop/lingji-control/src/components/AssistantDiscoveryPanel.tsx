import { useCallback, useEffect, useMemo, useState } from "react";
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

const size = (value: number) => value >= 1024 * 1024
  ? `${(value / 1024 / 1024).toFixed(1)} MB`
  : `${Math.max(1, Math.round(value / 1024))} KB`;

function stateLabel(state: string): string {
  if (state === "detected") return "已识别";
  if (state === "manual_export") return "支持官方导出";
  if (state === "not_found") return "未发现";
  return state || "未知";
}

export default function AssistantDiscoveryPanel({
  api,
  active,
  onOpenCodex,
  onOpenActivity,
  onOwnerDecisionCount,
}: {
  api: LingJiApi;
  active: boolean;
  onOpenCodex: () => void;
  onOpenActivity: () => void;
  onOwnerDecisionCount?: (count: number) => void;
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
  const decisionSources = useMemo(
    () => resource.data?.import_plan?.sources.filter((source) => source.candidates.length > 0) ?? [],
    [resource.data],
  );
  const importSource = decisionSources[0] ?? null;
  const decisionCount = decisionSources.length;

  useEffect(() => {
    onOwnerDecisionCount?.(decisionCount);
  }, [decisionCount, onOwnerDecisionCount]);

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
        : `已交给灵机自动整理${response.job_id ? ` · ${response.job_id}` : ""}。`);
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
        : `已交给灵机自动整理${response.job_id ? ` · ${response.job_id}` : ""}。`);
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
    <section className="assistant-autopilot-panel assistant-autopilot-compact">
      <div className="assistant-autopilot-heading">
        <div>
          <span className="desktop-eyebrow">自动发现</span>
          <h2>{resource.loading ? "正在检查这台电脑" : `已自动识别 ${detected.length} 个 AI 工具`}</h2>
          <p>灵机自己扫描已知位置。没有你的允许，不会读取真实对话正文，也不会自动写入永久记忆。</p>
        </div>
        <div className="assistant-autopilot-live">
          <span className={resource.error ? "status-dot" : "status-dot online"} />
          <div>
            <strong>{resource.error ? "自动重试中" : resource.refreshing ? "正在更新" : "后台持续检查"}</strong>
            <small>无需手动刷新</small>
          </div>
        </div>
      </div>

      <div className="assistant-autopilot-tool-strip" aria-label="已识别 AI 工具">
        {detected.length ? detected.map((assistant) => (
          <button
            type="button"
            className="assistant-tool-chip"
            key={assistant.id}
            onClick={assistant.id === "codex" ? onOpenCodex : undefined}
            disabled={assistant.id !== "codex"}
          >
            <span className="status-dot online" />
            {assistant.label}
          </button>
        )) : (
          <span className="assistant-tool-chip muted">{resource.loading ? "正在识别…" : "暂未发现本机 AI 工具"}</span>
        )}
        {decisionCount > 0 && <span className="pill warning">{decisionCount} 类资料等你授权</span>}
      </div>

      {resource.error && (
        <div className="assistant-autopilot-note warning">
          自动发现暂时失败，灵机会继续重试；这不是需要你手动排查的日常任务。
        </div>
      )}

      {importSource && importSource.candidates[0] && (
        <div className="assistant-autopilot-action">
          <div>
            <span className="desktop-eyebrow">需要你决定</span>
            <strong>允许灵机读取 {importSource.label}？</strong>
            <p>
              {importSource.candidates[0].display_name} · {size(importSource.candidates[0].size_bytes)}
              {decisionCount > 1 ? ` · 另有 ${decisionCount - 1} 类资料等待授权` : ""}
              {" · "}当前只读取了文件元数据。
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

      <details className="assistant-autopilot-more">
        <summary>查看发现详情与手动导入</summary>
        <div className="assistant-autopilot-details">
          <div className="assistant-autopilot-tools">
            {resource.data?.assistants.map((assistant) => (
              <article className="assistant-autopilot-tool" key={assistant.id}>
                <div>
                  <strong>{assistant.label}</strong>
                  <span className={`pill ${assistant.detection_state === "detected" ? "ok" : "neutral"}`}>
                    {stateLabel(assistant.detection_state)}
                  </span>
                </div>
                <p>{assistant.message}</p>
                {assistant.id === "codex" && assistant.detection_state === "detected" && (
                  <button className="text-button" onClick={onOpenCodex}>查看 Codex 工作记录</button>
                )}
              </article>
            ))}
          </div>

          {resource.data?.import_plan && (
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
          )}

          <div className="assistant-autopilot-safety">
            <span>只读元数据</span>
            <span>正文读取需授权</span>
            <span>永久记忆需审核</span>
          </div>
        </div>
      </details>

      {message && <div className="assistant-autopilot-note">{message}</div>}

      <div className="assistant-autopilot-footer">
        <span>普通扫描、检测和重试由灵机自动完成。</span>
        <button className="text-button" onClick={onOpenActivity}>查看自动处理记录</button>
      </div>
    </section>
  );
}
