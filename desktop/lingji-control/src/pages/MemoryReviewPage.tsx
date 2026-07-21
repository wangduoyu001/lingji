import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api";
import type { PageProps } from "../types";
import { REVIEW_LIMIT, canApprove, integrityMessage } from "./codexWorkspaceContract";
import { MemoryReviewApi } from "./memoryReviewApi";
import type { CoreIntegrity, CoreMemoryDraft, MemoryCandidate, ReviewFilters } from "./memoryReviewTypes";
import "./LocalMemoryLoop.css";

const emptyDraft: CoreMemoryDraft = { title: "", content: "", project_ids: [], memory_type: "decision", importance: "medium", privacy: "private", tags: [] };
const dt = (value?: string) => value ? new Date(value).toLocaleString() : "未知";

export default function MemoryReviewPage({ api, active }: PageProps) {
  const client = useMemo(() => new MemoryReviewApi(api), [api]);
  const [filters, setFilters] = useState<ReviewFilters>({ projectId: "", agent: "", type: "", importance: "", q: "", limit: REVIEW_LIMIT, offset: 0 });
  const [items, setItems] = useState<MemoryCandidate[]>([]);
  const [selected, setSelected] = useState<MemoryCandidate | null>(null);
  const [editContent, setEditContent] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [draft, setDraft] = useState<CoreMemoryDraft>(emptyDraft);
  const [coreMemoryId, setCoreMemoryId] = useState("");
  const [integrity, setIntegrity] = useState<CoreIntegrity | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    if (!active) return;
    abortRef.current?.abort(); const abort = new AbortController(); const id = ++requestId.current; abortRef.current = abort;
    try { const response = await client.candidates(filters, abort.signal); if (id === requestId.current) { setItems(response.items ?? []); setError(null); } }
    catch (reason) { if (id === requestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason); }
  }, [active, client, filters]);

  useEffect(() => { void load(); return () => abortRef.current?.abort(); }, [load]);

  const openCandidate = async (row: MemoryCandidate) => {
    setBusy(`detail:${row.memory_id}`);
    try { const detail = await client.candidate(row.memory_id); setSelected(detail); setEditContent(detail.content ?? ""); setRejectReason(""); setIntegrity(null); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const approve = async (edited: boolean) => {
    if (!selected?.current_hash || busy) return;
    if (!window.confirm("此操作会把候选记忆加入长期记忆，并在后续 Codex 对话中参与取回。")) return;
    setBusy(edited ? "edit-approve" : "approve");
    try {
      if (edited) await client.editApprove(selected.memory_id, selected.current_hash, editContent);
      else await client.approve(selected.memory_id, selected.current_hash);
      setSelected(null); await load();
    } catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const reject = async () => {
    if (!selected?.current_hash || !rejectReason.trim() || busy) return;
    setBusy("reject");
    try { await client.reject(selected.memory_id, selected.current_hash, rejectReason.trim()); setSelected(null); setRejectReason(""); await load(); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const createCore = async () => {
    if (!draft.title.trim() || !draft.content.trim() || busy) return;
    setBusy("create-core");
    try { const result = await client.createCore(draft); setCoreMemoryId(result.memory_id ?? result.id ?? ""); setDraft(emptyDraft); await load(); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const inspectCore = async () => {
    if (!coreMemoryId.trim() || busy) return;
    setBusy("integrity");
    try { setIntegrity(await client.integrity(coreMemoryId.trim())); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  const archiveCore = async () => {
    if (!coreMemoryId.trim() || busy || !window.confirm("归档后不再默认注入 Codex，但不会物理删除文件。")) return;
    setBusy("archive");
    try { await client.archive(coreMemoryId.trim()); setIntegrity(null); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); } finally { setBusy(""); }
  };

  if (!active) return <div className="loop-state">连接本机服务后显示记忆审核。</div>;
  return <div className="loop-page">
    <header className="loop-toolbar"><button className="button secondary" onClick={() => void load()}>刷新</button><span>批准、编辑或拒绝 AI 提出的长期记忆</span></header>
    {error && <div className="loop-state error">{error.status === 409 ? "候选内容已变化，请刷新后重新审核。" : error.status === 401 ? "需要本地授权" : error.status === 503 ? "服务暂不可用" : "操作失败，已保留编辑内容。"}</div>}
    <section className="review-layout">
      <div className="loop-panel"><h2>待审核记忆</h2><div className="loop-filters"><input placeholder="项目" value={filters.projectId} onChange={(e) => setFilters({ ...filters, projectId: e.target.value, offset: 0 })} /><input placeholder="Agent" value={filters.agent} onChange={(e) => setFilters({ ...filters, agent: e.target.value, offset: 0 })} /><input placeholder="类型" value={filters.type} onChange={(e) => setFilters({ ...filters, type: e.target.value, offset: 0 })} /><select value={filters.importance} onChange={(e) => setFilters({ ...filters, importance: e.target.value, offset: 0 })}><option value="">全部重要性</option><option>high</option><option>medium</option><option>low</option></select><input placeholder="关键词" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value, offset: 0 })} /></div>{items.length ? items.map((item) => <button className="loop-card" key={item.memory_id} onClick={() => void openCandidate(item)}><strong>{item.title ?? item.memory_id}</strong><span>{item.content_preview ?? "无预览"}</span><span>{item.project_ids?.join("、") || "未绑定项目"} · {item.proposed_by ?? "未知 Agent"}</span><small>{item.importance ?? "未知"} · 置信度 {item.confidence ?? "未知"} · {dt(item.created_at)}</small></button>) : <p>{Object.values(filters).some((v) => v !== "" && v !== 0 && v !== REVIEW_LIMIT) ? "筛选后没有候选记忆。" : "没有待审核记忆。"}</p>}<div className="loop-pager"><button disabled={filters.offset === 0} onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - REVIEW_LIMIT) })}>上一页</button><button onClick={() => setFilters({ ...filters, offset: filters.offset + REVIEW_LIMIT })}>下一页</button></div></div>
      <div className="loop-panel"><h2>审核详情</h2>{selected ? <><h3>{selected.title ?? selected.memory_id}</h3><p>来源 Session：{selected.source_session_id ?? "未知"}</p><p>来源 Message：{selected.source_message_id ?? "未知"}</p><p>AI 提议理由：{selected.proposal_reason ?? "未知"}</p><p>当前 Hash：{selected.current_hash ?? "未知"}</p><p>相似 Core Memory：{selected.similar_core?.map((item) => item.title ?? item.memory_id).join("；") || "无"}</p><p>影响 Agent：{selected.affected_agents?.join("；") || "未知"}</p><textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} /><div className="review-actions"><button className="button" disabled={!canApprove(selected.current_hash) || Boolean(busy)} onClick={() => void approve(false)}>{busy === "approve" ? "批准中…" : "批准"}</button><button disabled={!canApprove(selected.current_hash) || Boolean(busy)} onClick={() => void approve(true)}>{busy === "edit-approve" ? "保存中…" : "编辑后批准"}</button><input placeholder="拒绝理由（必填）" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} /><button disabled={Boolean(busy) || !rejectReason.trim() || !selected.current_hash} onClick={() => void reject()}>{busy === "reject" ? "拒绝中…" : "拒绝"}</button><button onClick={() => setSelected(null)}>稍后处理</button></div></> : <p>选择候选记忆查看完整内容与来源。</p>}</div>
    </section>
    <section className="loop-panel"><h2>手动新增长期记忆</h2><div className="loop-filters"><input placeholder="标题" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /><input placeholder="项目，逗号分隔" value={draft.project_ids.join(",")} onChange={(e) => setDraft({ ...draft, project_ids: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /><input placeholder="类型" value={draft.memory_type} onChange={(e) => setDraft({ ...draft, memory_type: e.target.value })} /><select value={draft.importance} onChange={(e) => setDraft({ ...draft, importance: e.target.value })}><option>high</option><option>medium</option><option>low</option></select><select value={draft.privacy} onChange={(e) => setDraft({ ...draft, privacy: e.target.value as "private" | "restricted" })}><option>private</option><option>restricted</option></select><input placeholder="Tags，逗号分隔" value={draft.tags.join(",")} onChange={(e) => setDraft({ ...draft, tags: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></div><textarea value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} placeholder="内容" /><button className="button" disabled={busy === "create-core" || !draft.title.trim() || !draft.content.trim()} onClick={() => void createCore()}>{busy === "create-core" ? "加入中…" : "确认加入长期记忆"}</button></section>
    <section className="loop-panel"><h2>长期记忆健康</h2><div className="loop-filters"><input placeholder="Core Memory ID" value={coreMemoryId} onChange={(e) => setCoreMemoryId(e.target.value)} /><button disabled={!coreMemoryId.trim() || Boolean(busy)} onClick={() => void inspectCore()}>查看详情</button><button disabled={!coreMemoryId.trim() || Boolean(busy)} onClick={() => void archiveCore()}>归档</button></div>{integrity ? <div className="danger-note"><strong>{integrity.state}</strong><p>{integrityMessage(integrity.state)}</p><small>{integrity.relative_path ?? "无路径引用"}</small><button onClick={() => setIntegrity(null)}>稍后处理</button></div> : <p>从 Memory Inspector 复制 Core Memory ID 后检查。归档后不再默认注入 Codex，但不会物理删除文件。</p>}</section>
  </div>;
}
