import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api";
import type { PageProps } from "../types";
import type { CaptureInspectorTarget } from "./captureCenterTypes";
import type { CodexCurrent } from "./codexWorkspaceTypes";
import MemoryInspectorPage from "./MemoryInspectorPage";

export default function MemoryInspectorLoopPage({ api, active, target }: PageProps & { target: CaptureInspectorTarget | null }) {
  const [current, setCurrent] = useState<CodexCurrent | null>(null);
  const [shortcut, setShortcut] = useState<CaptureInspectorTarget | null>(target);
  const controller = useRef<AbortController | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (!active) return;
    controller.current?.abort(); const abort = new AbortController(); const id = ++requestId.current; controller.current = abort;
    api.get<CodexCurrent>("/api/codex/current", { signal: abort.signal })
      .then((response) => { if (id === requestId.current) setCurrent(response); })
      .catch((reason) => { if (!(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) setCurrent(null); });
    return () => abort.abort();
  }, [active, api]);

  const apply = (next: CaptureInspectorTarget | null) => {
    setShortcut(next);
    const params = new URLSearchParams();
    if (next?.project_id) params.set("project_id", next.project_id);
    if (next?.source_type) params.set("source_type", next.source_type);
    if (next?.conversation_id) params.set("conversation_id", next.conversation_id);
    if (next?.message_id) params.set("message_id", next.message_id);
    if (next?.memory_id) params.set("memory_id", next.memory_id);
    window.history.replaceState(null, "", `${window.location.pathname}${params.size ? `?${params}` : ""}`);
  };

  return <div className="stack">
    <div className="toolbar">
      <button className="button secondary" disabled={!current?.project?.project_id} onClick={() => apply({ project_id: current?.project?.project_id })}>当前项目</button>
      <button className="button secondary" onClick={() => apply({ source_type: "codex" })}>仅 Codex</button>
      <button className="button secondary" disabled={!current?.session?.conversation_ids?.[0]} onClick={() => apply({ project_id: current?.project?.project_id, conversation_id: current?.session?.conversation_ids?.[0] })}>当前 Session</button>
      <button className="button secondary" onClick={() => apply({ ...shortcut, related_memory_only: true })}>仅有关联 Memory</button>
      <button className="button secondary" onClick={() => apply({ ...shortcut, core_memory_only: true })}>仅 Core Memory</button>
      <button className="button secondary" onClick={() => apply(null)}>清除快捷筛选</button>
      <span>{shortcut ? `快捷筛选：${Object.entries(shortcut).filter(([, value]) => value).map(([key, value]) => `${key}=${value}`).join(" · ")}` : "未启用快捷筛选"}</span>
    </div>
    <MemoryInspectorPage key={JSON.stringify(shortcut)} api={api} active={active} />
  </div>;
}
