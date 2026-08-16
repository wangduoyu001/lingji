import { useEffect, useRef, useState } from "react";
import type { LingJiApi } from "../api";
import type { CaptureSubmissionResponse } from "../pages/captureCenterTypes";
import type { PageId } from "../types";

type Props = {
  api: LingJiApi;
  connected: boolean;
  onNavigate: (page: PageId) => void;
};

const cleanPrefix = (input: string) => input.replace(/^(记住|记录)\s*[：:]/, "").trim();

function captureFeedback(response: CaptureSubmissionResponse): string {
  const captureId = response.capture_id?.trim();
  const jobId = response.job_id?.trim();
  if (!captureId) {
    return "服务接受了这次提交，但没有返回可追踪的资料编号。灵机不会把它显示成“已经记住”。";
  }
  if (response.duplicate) {
    return `这条资料已经存在，未重复创建。资料 ${captureId}${jobId ? ` · 处理任务 ${jobId}` : ""}。`;
  }
  if (response.status === "queued" && jobId) {
    return `已接收文本资料。资料 ${captureId} · 处理任务 ${jobId} 已进入自动处理队列。`;
  }
  if (response.status === "executed") {
    return `已接收并执行文本资料。资料 ${captureId}${jobId ? ` · 执行 ${jobId}` : ""}。记忆结果以“记忆”页面的真实证据为准。`;
  }
  return `已接收文本资料。资料 ${captureId}${jobId ? ` · 处理任务 ${jobId}` : ""} · 状态 ${response.status || "未知"}。`;
}

export default function GlobalOwnerCommand({ api, connected, onNavigate }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  async function submit() {
    const query = value.trim();
    if (!query || busy) return;
    setFeedback("");

    if (/^(记住|记录)\s*[：:]/.test(query)) {
      const content = cleanPrefix(query);
      if (!content) {
        setFeedback("“记住：”后面还没有内容。把要长期保留的信息直接写在后面即可。");
        return;
      }
      if (!connected) {
        setFeedback("灵机核心还没连接，暂时不能写入资料。内容没有被提交。");
        return;
      }
      setBusy(true);
      try {
        const response = await api.post<CaptureSubmissionResponse>("/api/capture/text", {
          title: content.slice(0, 48),
          text: content,
          source_type: "text",
          project_ids: [],
          tags: ["owner_quick_capture"],
          privacy: "private",
          priority: 100,
          process_later: true,
          metadata: { capture_method: "owner_command_bar" },
        });
        setFeedback(captureFeedback(response));
        setValue("");
      } catch {
        setFeedback("这次记录没有提交成功。灵机会保留现有数据，不会假装已经记住。");
      } finally {
        setBusy(false);
      }
      return;
    }

    if (/(记忆|记得|查找|找回|为什么)/.test(query)) {
      onNavigate("memory");
      setFeedback("已打开记忆。可以继续用关键词筛选真实记忆和来源证据。");
      return;
    }
    if (/(最近|做了什么|工作|任务|进度)/.test(query)) {
      onNavigate("activity");
      setFeedback("已打开工作履历。这里展示真实任务、结果和下一步。");
      return;
    }
    if (/(需要我|决定|授权|待办|确认)/.test(query)) {
      onNavigate("attention");
      setFeedback("已打开“需要我”。只有真实待办对象才会出现在这里。");
      return;
    }
    if (/(添加|导入|文件|网页|媒体)/.test(query)) {
      onNavigate("capture_center");
      setFeedback("已打开添加资料。灵机会在提交后自动处理。");
      return;
    }

    setFeedback("当前全局入口只执行可验证的记录和导航指令。可试试“记住：…”、“查找记忆”或“最近做了什么”。");
  }

  return (
    <div className="owner-command-wrap">
      <div className="owner-command-bar">
        <span className="owner-command-mark">⌘</span>
        <input
          ref={inputRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") void submit(); }}
          placeholder="告诉灵机一件事，或问它去哪里找 · 例如：记住：Mac 版优先云端生图"
          aria-label="灵机全局输入"
        />
        <kbd>⌘K</kbd>
        <button disabled={!value.trim() || busy} onClick={() => void submit()}>{busy ? "处理中" : "执行"}</button>
      </div>
      {feedback && <div className="owner-command-feedback">{feedback}</div>}
    </div>
  );
}
