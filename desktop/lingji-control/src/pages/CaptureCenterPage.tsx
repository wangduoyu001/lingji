import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api";
import type { PageProps } from "../types";
import { CaptureCenterApi } from "./captureCenterApi";
import {
  ACTIVE_POLL_MS,
  acceptsFileMode,
  acceptsMedia,
  basePayload,
  buildJobsQuery,
  canCancel,
  canRetry,
  CAPTURE_PAGE_SIZE,
  errorLabel,
  fileNameOnly,
  hasActiveJobs,
  IDLE_POLL_MS,
  progressLabel,
  restrictedClass,
  resultTarget,
  safeName,
  validateText,
  validateUrl,
} from "./captureCenterContract";
import type {
  CaptureCapabilitiesResponse,
  CaptureInspectorTarget,
  CaptureJob,
  CaptureJobFilters,
  CaptureStatusResponse,
} from "./captureCenterTypes";
import "./CaptureCenterPage.css";

type Tab = "text" | "web" | "file" | "media" | "chatgpt_export" | "codex_report";
type CommonForm = { title: string; projects: string; tags: string; privacy: "private" | "restricted"; priority: number };

type Props = PageProps & {
  onOpenInspector: (target: CaptureInspectorTarget) => void;
  onOpenWork: (workId: string) => void;
};

const emptyCommon: CommonForm = { title: "", projects: "", tags: "", privacy: "private", priority: 0 };
const emptyFilters: CaptureJobFilters = { status: "", sourceType: "", q: "" };
const count = (value: number | null | undefined): string => typeof value === "number" ? value.toLocaleString() : "未知";
const time = (value?: string | null): string => value ? new Date(value).toLocaleString() : "未知";

function ErrorState({ error }: { error: ApiError | null }) {
  if (!error) return null;
  return <div className="capture-notice error">{errorLabel(error.status, error.code)}</div>;
}

function CommonFields({ value, onChange }: { value: CommonForm; onChange: (value: CommonForm) => void }) {
  return (
    <div className="capture-common-grid">
      <label>标题<input value={value.title} onChange={(event) => onChange({ ...value, title: event.target.value })} /></label>
      <label>项目<input value={value.projects} placeholder="多个项目用逗号分隔" onChange={(event) => onChange({ ...value, projects: event.target.value })} /></label>
      <label>标签<input value={value.tags} placeholder="多个标签用逗号分隔" onChange={(event) => onChange({ ...value, tags: event.target.value })} /></label>
      <label>隐私<select value={value.privacy} onChange={(event) => onChange({ ...value, privacy: event.target.value as CommonForm["privacy"] })}><option value="private">private</option><option value="restricted">restricted</option></select></label>
      <label>优先级<input type="number" value={value.priority} onChange={(event) => onChange({ ...value, priority: Number(event.target.value) })} /></label>
    </div>
  );
}

export default function CaptureCenterPage({ api, active, onOpenInspector, onOpenWork }: Props) {
  const client = useMemo(() => new CaptureCenterApi(api), [api]);
  const [tab, setTab] = useState<Tab>("text");
  const [common, setCommon] = useState(emptyCommon);
  const [textBody, setTextBody] = useState("");
  const [url, setUrl] = useState("");
  const [webText, setWebText] = useState("");
  const [author, setAuthor] = useState("");
  const [publishedAt, setPublishedAt] = useState("");
  const [platform, setPlatform] = useState("");
  const [selectedPath, setSelectedPath] = useState("");
  const [fileMode, setFileMode] = useState("web_snapshot");
  const [mediaOptions, setMediaOptions] = useState({ ocr: true, transcription: true, keyframes: false, extractAudio: false });
  const [status, setStatus] = useState<CaptureStatusResponse | null>(null);
  const [capabilities, setCapabilities] = useState<CaptureCapabilitiesResponse | null>(null);
  const [jobs, setJobs] = useState<CaptureJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<CaptureJob | null>(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [debouncedQ, setDebouncedQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [operatingJobId, setOperatingJobId] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState("");
  const [submittedWorkId, setSubmittedWorkId] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(filters.q), 300);
    return () => window.clearTimeout(timer);
  }, [filters.q]);

  const load = useCallback(async () => {
    if (!active) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    const requestId = ++requestIdRef.current;
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const effectiveFilters = { ...filters, q: debouncedQ };
      const [statusResult, capabilitiesResult, jobsResult] = await Promise.allSettled([
        client.status(controller.signal),
        client.capabilities(controller.signal),
        client.jobs(buildJobsQuery(effectiveFilters, offset), controller.signal),
      ]);
      if (requestId !== requestIdRef.current) return;
      if (statusResult.status === "fulfilled") setStatus(statusResult.value);
      if (capabilitiesResult.status === "fulfilled") setCapabilities(capabilitiesResult.value);
      if (jobsResult.status === "fulfilled") {
        setJobs(jobsResult.value.items ?? []);
        setTotal(jobsResult.value.pagination?.total ?? null);
      }
      const rejected = [statusResult, capabilitiesResult, jobsResult].find((result) => result.status === "rejected");
      if (rejected?.status === "rejected") throw rejected.reason;
    } catch (reason) {
      if (requestId === requestIdRef.current && !(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) {
        setError(reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Capture request failed"));
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, [active, client, debouncedQ, filters.sourceType, filters.status, offset]);

  useEffect(() => {
    void load();
    return () => controllerRef.current?.abort();
  }, [load]);

  useEffect(() => {
    if (!active) return;
    const interval = hasActiveJobs(jobs) ? ACTIVE_POLL_MS : IDLE_POLL_MS;
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void load(); }, interval);
    return () => window.clearInterval(timer);
  }, [active, jobs, load]);

  useEffect(() => setOffset(0), [debouncedQ, filters.sourceType, filters.status]);

  const chooseFile = async () => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const mode = tab === "chatgpt_export" ? "chatgpt_export" : tab === "codex_report" ? "codex_report" : fileMode;
      const filters = tab === "media"
        ? [{ name: "音频和视频", extensions: ["mp4", "mov", "mkv", "avi", "webm", "m4v", "flv", "ts", "mts", "m2ts", "mp3", "wav", "m4a", "aac", "flac", "ogg", "opus", "wma"] }]
        : mode === "chatgpt_export"
          ? [{ name: "ChatGPT Export", extensions: ["zip", "json"] }]
          : mode === "codex_report"
            ? [{ name: "Codex Report", extensions: ["json"] }]
            : [{ name: "Web Snapshot", extensions: ["html", "htm", "json", "txt", "md"] }];
      const selected = await open({ multiple: false, directory: false, filters });
      if (typeof selected === "string") setSelectedPath(selected);
    } catch {
      setSubmissionMessage("文件选择仅在已配置 Dialog Plugin 的桌面应用中可用");
      setSubmittedWorkId(null);
    }
  };

  const submit = async () => {
    if (submitting) return;
    setSubmissionMessage("");
    setSubmittedWorkId(null);
    setError(null);
    const commonPayload = basePayload(common);
    let validation: string | null = null;
    if (tab === "text") validation = validateText(textBody);
    if (tab === "web") validation = validateUrl(url);
    if (["file", "chatgpt_export", "codex_report"].includes(tab) && !selectedPath) validation = "请选择文件";
    if (tab === "media" && !selectedPath) validation = "请选择媒体文件";
    const effectiveMode = tab === "chatgpt_export" ? "chatgpt_export" : tab === "codex_report" ? "codex_report" : fileMode;
    if (["file", "chatgpt_export", "codex_report"].includes(tab) && selectedPath && !acceptsFileMode(selectedPath, effectiveMode)) validation = "文件扩展名与所选模式不匹配";
    if (tab === "media" && selectedPath && !acceptsMedia(selectedPath)) validation = "当前媒体扩展名不受支持";
    if (validation) { setSubmissionMessage(validation); return; }

    setSubmitting(true);
    try {
      const response = tab === "text"
        ? await client.submitText({ ...commonPayload, text: textBody, source_type: "web" })
        : tab === "web"
          ? await client.submitWeb({ ...commonPayload, url, text: webText || undefined, author: author || undefined, published_at: publishedAt || undefined, platform: platform || undefined })
          : tab === "media"
            ? await client.submitMedia({ ...commonPayload, input_path: selectedPath, allow_ocr: mediaOptions.ocr, allow_transcription: mediaOptions.transcription, extract_keyframes: mediaOptions.keyframes, extract_audio: mediaOptions.extractAudio })
            : await client.submitFile({ ...commonPayload, input_path: selectedPath, source_type: effectiveMode === "web_snapshot" ? "web" : effectiveMode, adapter_name: effectiveMode });
      setSubmittedWorkId(response.work_id ?? null);
      setSubmissionMessage(
        response.duplicate
          ? `内容已存在，已定位原工作${response.work_id ? `：${response.work_id}` : ""}`
          : response.work_id
            ? `灵机已接手：${response.work_id}${response.job_id ? ` · ${response.job_id}` : ""}`
            : "提交已返回，但没有 work_id，不能宣称灵机已接手",
      );
      await load();
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Submission failed");
      setSubmissionMessage(errorLabel(apiError.status, apiError.code));
    } finally {
      setSubmitting(false);
    }
  };

  const operate = async (job: CaptureJob, action: "cancel" | "retry") => {
    if (operatingJobId) return;
    setOperatingJobId(job.job_id);
    setSubmissionMessage("");
    setSubmittedWorkId(null);
    try {
      if (action === "cancel") await client.cancel(job.job_id); else await client.retry(job.job_id);
      await load();
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Job operation failed");
      setSubmissionMessage(errorLabel(apiError.status, apiError.code));
    } finally {
      setOperatingJobId(null);
    }
  };

  const setMode = async (action: "pause" | "resume") => {
    try { if (action === "pause") await client.pause(); else await client.resume(); await load(); }
    catch (reason) { const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Mode operation failed"); setSubmissionMessage(errorLabel(apiError.status, apiError.code)); }
  };

  if (!active) return <div className="capture-state">连接本机服务后显示 Capture Center（手动投喂中心）</div>;

  const media = capabilities?.media;
  const paused = status?.mode === "paused";

  return (
    <div className="capture-center">
      <div className="capture-status-grid">
        <div><span>Capture Mode</span><strong>{status?.mode ?? "未知"}</strong></div>
        <div><span>Worker</span><strong>{status?.worker_state ?? "未知"}</strong></div>
        {(["queued", "running", "retrying", "completed", "failed", "cancelled"] as const).map((key) => <div key={key}><span>{key}</span><strong>{count(status?.[key])}</strong></div>)}
        <div><span>最后更新时间</span><strong>{time(status?.updated_at)}</strong></div>
      </div>

      <div className="capture-toolbar">
        <button disabled={paused} onClick={() => void setMode("pause")}>暂停</button>
        <button disabled={!paused} onClick={() => void setMode("resume")}>恢复</button>
        <button disabled={loading} onClick={() => void load()}>{loading ? "刷新中…" : "刷新"}</button>
      </div>

      {paused && <div className="capture-notice warning">采集已暂停，新提交可能被拒绝。</div>}
      {capabilities?.state === "configuration_required" && <div className="capture-notice warning">需要配置 Capture Service 后才能使用全部能力。</div>}
      <ErrorState error={error} />
      {submissionMessage && <div className="capture-notice"><span>{submissionMessage}</span>{submittedWorkId ? <button onClick={() => onOpenWork(submittedWorkId)}>查看工作</button> : null}</div>}

      <section className="capture-submit-panel">
        <div className="capture-tabs">
          {([ ["text", "文本"], ["web", "网页"], ["file", "文件"], ["media", "媒体"], ["chatgpt_export", "ChatGPT Export"], ["codex_report", "Codex Report"] ] as Array<[Tab, string]>).map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => { setTab(id); setSelectedPath(""); }}>{label}</button>)}
        </div>
        <CommonFields value={common} onChange={setCommon} />

        {tab === "text" && <label className="capture-wide">正文<textarea value={textBody} onChange={(event) => setTextBody(event.target.value)} /></label>}
        {tab === "web" && <div className="capture-form-grid"><label>URL<input value={url} onChange={(event) => setUrl(event.target.value)} /></label><label>作者<input value={author} onChange={(event) => setAuthor(event.target.value)} /></label><label>发布时间<input type="datetime-local" value={publishedAt} onChange={(event) => setPublishedAt(event.target.value)} /></label><label>平台<input value={platform} onChange={(event) => setPlatform(event.target.value)} /></label><label className="capture-wide">可选正文<textarea value={webText} onChange={(event) => setWebText(event.target.value)} /></label></div>}
        {["file", "chatgpt_export", "codex_report"].includes(tab) && <div className="capture-file-row">{tab === "file" && <label>模式<select value={fileMode} onChange={(event) => setFileMode(event.target.value)}><option value="web_snapshot">Web Snapshot</option><option value="chatgpt_export">ChatGPT Export</option><option value="codex_report">Codex Report</option></select></label>}<button onClick={() => void chooseFile()}>选择单个文件</button><span>{fileNameOnly(selectedPath)}</span></div>}
        {tab === "media" && <div className="capture-media-options"><button onClick={() => void chooseFile()}>选择单个媒体文件</button><span>{fileNameOnly(selectedPath)}</span><label><input type="checkbox" checked={mediaOptions.ocr} disabled={media?.ocr === false} onChange={(event) => setMediaOptions({ ...mediaOptions, ocr: event.target.checked })} />OCR</label><label><input type="checkbox" checked={mediaOptions.transcription} disabled={media?.transcription === false} onChange={(event) => setMediaOptions({ ...mediaOptions, transcription: event.target.checked })} />转写</label><label><input type="checkbox" checked={mediaOptions.keyframes} disabled={media?.keyframes === false} onChange={(event) => setMediaOptions({ ...mediaOptions, keyframes: event.target.checked })} />关键帧</label><label><input type="checkbox" checked={mediaOptions.extractAudio} disabled={media?.extract_audio === false} onChange={(event) => setMediaOptions({ ...mediaOptions, extractAudio: event.target.checked })} />提取音频</label>{media?.reasons && Object.values(media.reasons).map((reason) => <small key={reason}>{reason}</small>)}</div>}
        <button className="button primary" disabled={submitting || paused} onClick={() => void submit()}>{submitting ? "提交中…" : "提交并排队"}</button>
      </section>

      <section className="capture-jobs-panel">
        <div className="capture-job-filters">
          <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">全部状态</option>{["queued", "running", "retrying", "completed", "failed", "cancelled"].map((item) => <option key={item}>{item}</option>)}</select>
          <input placeholder="来源类型" value={filters.sourceType} onChange={(event) => setFilters({ ...filters, sourceType: event.target.value })} />
          <input placeholder="关键词搜索" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
        </div>
        {!loading && jobs.length === 0 && <div className="capture-state">{filters.status || filters.sourceType || debouncedQ ? "筛选后没有任务" : "系统正常，但还没有手动投喂任务"}</div>}
        <div className="capture-job-list">
          {jobs.map((job) => (
            <article key={job.job_id} className={`capture-job${restrictedClass(job.privacy)}`}>
              <button className="capture-job-main" onClick={() => setSelectedJob(job)}><strong>{safeName(job)}</strong><span>{job.source_type ?? "未知"} · {job.adapter_name ?? "未知"}</span><span>{job.status} · 进度 {progressLabel(job)}</span><span>Work {job.work_id ?? "未关联"}</span><span>尝试 {count(job.attempts)}/{count(job.max_attempts)}</span><small>{job.error_message || job.result_summary || "无错误摘要"}</small><small>{time(job.created_at)} → {time(job.updated_at)}</small></button>
              <div className="capture-job-actions"><button disabled={!canCancel(job.status) || operatingJobId === job.job_id} onClick={() => void operate(job, "cancel")}>取消</button><button disabled={!canRetry(job.status) || operatingJobId === job.job_id} onClick={() => void operate(job, "retry")}>重试</button>{job.work_id && <button onClick={() => onOpenWork(job.work_id!)}>查看工作</button>}{job.status === "running" && <span>处理中，当前版本不支持强制终止</span>}{job.status === "completed" && resultTarget(job) && <button onClick={() => onOpenInspector(resultTarget(job)!)}>查看结果</button>}</div>
            </article>
          ))}
        </div>
        <div className="capture-pager"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - CAPTURE_PAGE_SIZE))}>上一页</button><span>{Math.floor(offset / CAPTURE_PAGE_SIZE) + 1} / {total === null ? "未知" : Math.max(1, Math.ceil(total / CAPTURE_PAGE_SIZE))}</span><button disabled={total !== null && offset + CAPTURE_PAGE_SIZE >= total} onClick={() => setOffset(offset + CAPTURE_PAGE_SIZE)}>下一页</button></div>
      </section>

      {selectedJob && <aside className="capture-detail"><header><div><h2>任务详情</h2><span>{selectedJob.job_id}</span></div><button onClick={() => setSelectedJob(null)}>关闭</button></header><dl><dt>Work ID</dt><dd>{selectedJob.work_id ?? "未关联"}</dd><dt>名称</dt><dd>{safeName(selectedJob)}</dd><dt>来源</dt><dd>{selectedJob.source_type ?? "未知"}</dd><dt>Adapter</dt><dd>{selectedJob.adapter_name ?? "未知"}</dd><dt>状态</dt><dd>{selectedJob.status}</dd><dt>进度</dt><dd>{progressLabel(selectedJob)}</dd><dt>尝试</dt><dd>{count(selectedJob.attempts)}/{count(selectedJob.max_attempts)}</dd><dt>错误代码</dt><dd>{selectedJob.error_code ?? "未知"}</dd><dt>稳定错误摘要</dt><dd>{selectedJob.error_message ?? "未知"}</dd><dt>创建</dt><dd>{time(selectedJob.created_at)}</dd><dt>更新</dt><dd>{time(selectedJob.updated_at)}</dd><dt>完成</dt><dd>{time(selectedJob.completed_at)}</dd></dl>{selectedJob.work_id && <button className="button" onClick={() => onOpenWork(selectedJob.work_id!)}>查看工作事实</button>}{selectedJob.status === "completed" && resultTarget(selectedJob) && <button className="button primary" onClick={() => onOpenInspector(resultTarget(selectedJob)!)}>在 Memory Inspector 查看结果</button>}</aside>}
    </div>
  );
}
