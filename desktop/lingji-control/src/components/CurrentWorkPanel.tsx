import { useEffect, useRef, useState } from "react";
import type { LingJiApi } from "../api";
import { ApiError } from "../api";
import type { CodexCurrent } from "../pages/codexWorkspaceTypes";

const value = (input: unknown, fallback = "未知") => input === null || input === undefined || input === "" ? fallback : String(input);

export default function CurrentWorkPanel({ api, active }: { api: LingJiApi; active: boolean }) {
  const [current, setCurrent] = useState<CodexCurrent | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const controller = useRef<AbortController | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (!active) return;
    controller.current?.abort();
    const abort = new AbortController();
    const id = ++requestId.current;
    controller.current = abort;
    api.get<CodexCurrent>("/api/codex/current", { signal: abort.signal })
      .then((response) => { if (id === requestId.current) { setCurrent(response); setError(null); } })
      .catch((reason) => { if (id === requestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason); });
    return () => abort.abort();
  }, [active, api]);

  if (!active) return <section className="panel"><h2>当前工作</h2><p>连接本机服务后显示。</p></section>;
  if (error) return <section className="panel"><h2>当前工作</h2><p>{error.status === 401 ? "需要本地授权" : "当前工作状态暂不可用"}</p></section>;

  const project = current?.project;
  const session = current?.session;
  const rows = [
    ["当前项目", value(project?.name, "未绑定")], ["当前 Codex Session", value(session?.title, "无活动会话")],
    ["当前分支", value(project?.branch)], ["当前 Worktree", value(project?.worktree_name)],
    ["LingJi MCP", value(current?.mcp_state)], ["Obsidian", value(current?.obsidian_state)],
    ["Memory Index", value(current?.memory_index_state)], ["最近检查点", value(current?.last_checkpoint_at)],
    ["待审核记忆", typeof current?.pending_review_count === "number" ? String(current.pending_review_count) : "未知"],
    ["当前 Activity", value(current?.activity?.summary, "无活动")],
  ];
  return <section className="panel"><h2>当前工作</h2><div className="metric-grid">{rows.map(([label, item]) => <div className="metric" key={label}><span>{label}</span><strong>{item}</strong></div>)}</div></section>;
}
