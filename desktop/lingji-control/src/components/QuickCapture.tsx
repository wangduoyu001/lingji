import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api";
import type { LingJiApi } from "../api";
import { CaptureCenterApi } from "../pages/captureCenterApi";
import type { CaptureSubmissionResponse } from "../pages/captureCenterTypes";
import "./QuickCapture.css";

type Props = {
  api: LingJiApi;
  active: boolean;
  onOpenWork: (workId: string) => void;
};

export default function QuickCapture({ api, active, onOpenWork }: Props) {
  const client = useMemo(() => new CaptureCenterApi(api), [api]);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CaptureSubmissionResponse | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "k") return;
      event.preventDefault();
      if (!active) return;
      setOpen(true);
      setError("");
      setResult(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active]);

  useEffect(() => {
    if (!open) return;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [open]);

  const submit = async () => {
    const body = text.trim();
    if (!body || submitting) return;
    setSubmitting(true);
    setError("");
    setResult(null);
    try {
      const response = await client.submitText({
        title: body.replace(/\s+/g, " ").slice(0, 80),
        project_ids: [],
        tags: [],
        privacy: "private",
        priority: 0,
        process_later: true,
        metadata: { entry_point: "cmd_k_remember" },
        text: body,
        source_type: "web",
      });
      setResult(response);
      setText("");
    } catch (reason) {
      const apiError = reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Quick capture failed");
      setError(apiError.code ? `${apiError.code}：${apiError.message}` : apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="quick-capture-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
      <section className="quick-capture" role="dialog" aria-modal="true" aria-label="快速记住">
        <header>
          <div>
            <span className="desktop-eyebrow">CMD / CTRL + K</span>
            <h2>快速记住</h2>
          </div>
          <button type="button" onClick={() => setOpen(false)}>关闭</button>
        </header>
        <textarea
          autoFocus
          value={text}
          placeholder="输入要交给灵机记住的内容。提交后会创建真实 WorkItem，可追踪处理结果。"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              void submit();
            }
          }}
        />
        {error ? <p className="quick-capture-error">提交失败，内容已保留。{error}</p> : null}
        {result ? (
          <div className="quick-capture-result">
            <strong>{result.duplicate ? "内容已存在，已定位原工作" : "灵机已接手"}</strong>
            <span>Capture：{result.capture_id ?? "未知"}</span>
            <span>Work：{result.work_id ?? "未返回，不能宣称已接手"}</span>
            <span>Job：{result.job_id ?? "未知"}</span>
            {result.work_id ? <button type="button" onClick={() => { setOpen(false); onOpenWork(result.work_id!); }}>查看工作</button> : null}
          </div>
        ) : null}
        <footer>
          <span>⌘/Ctrl + Enter 提交 · Esc 关闭</span>
          <button className="button primary" type="button" disabled={!text.trim() || submitting} onClick={() => void submit()}>{submitting ? "提交中…" : "记住并追踪"}</button>
        </footer>
      </section>
    </div>
  );
}
