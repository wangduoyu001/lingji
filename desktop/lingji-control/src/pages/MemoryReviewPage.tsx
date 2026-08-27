import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api";
import { Empty, Notice } from "../components/ui";
import type { PageProps } from "../types";
import type { CaptureInspectorTarget } from "./captureCenterTypes";
import { REVIEW_LIMIT, canApprove, integrityMessage } from "./codexWorkspaceContract";
import { MemoryReviewApi } from "./memoryReviewApi";
import type { CoreIntegrity, CoreMemoryDraft, MemoryCandidate, ReviewFilters } from "./memoryReviewTypes";
import "./LocalMemoryLoop.css";

const emptyDraft: CoreMemoryDraft = { title: "", content: "", project_ids: [], memory_type: "decision", importance: "medium", privacy: "private", tags: [] };
const dt = (value?: string | null) => value ? new Date(value).toLocaleString() : "尚未获得";
const hasFilters = (filters: ReviewFilters) => Boolean(filters.projectId || filters.agent || filters.type || filters.importance || filters.q);
const confidenceLabel = (value: unknown) => typeof value === "number" ? `${Math.round(value * 100)}%` : value == null || value === "" ? "未知" : String(value);

export default function MemoryReviewPage({ api, active, onOpenInspector }: PageProps & { onOpenInspector?: (target: CaptureInspectorTarget) => void }) {
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
    abortRef.current?.abort();
    const abort = new AbortController();
    const id = ++requestId.current;
    abortRef.current = abort;
    try {
      const response = await client.candidates(filters, abort.signal);
      if (id === requestId.current) {
        setItems(response.items ?? []);
        setError(null);
      }
    } catch (reason) {
      if (id === requestId.current && reason instanceof ApiError && reason.code !== "REQUEST_CANCELLED") setError(reason);
    }
  }, [active, client, filters]);

  useEffect(() => { void load(); return () => abortRef.current?.abort(); }, [load]);

  const openCandidate = async (row: MemoryCandidate) => {
    setBusy(`detail:${row.memory_id}`);
    try {
      const detail = await client.candidate(row.memory_id);
      setSelected(detail);
      setEditContent(detail.content ?? "");
      setRejectReason("");
      setIntegrity(null);
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const approve = async (edited: boolean) => {
    if (!selected?.current_hash || busy) return;
    if (!window.confirm("此操作会把候选记忆加入长期记忆，并在后续 Codex 对话中参与取回。")) return;
    setBusy(edited ? "edit-approve" : "approve");
    try {
      if (edited) await client.editApprove(selected.memory_id, selected.current_hash, editContent);
      else await client.approve(selected.memory_id, selected.current_hash);
      setSelected(null);
      await load();
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const reject = async () => {
    if (!selected?.current_hash || !rejectReason.trim() || busy) return;
    setBusy("reject");
    try {
      await client.reject(selected.memory_id, selected.current_hash, rejectReason.trim());
      setSelected(null);
      setRejectReason("");
      await load();
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const createCore = async () => {
    if (!draft.title.trim() || !draft.content.trim() || busy) return;
    setBusy("create-core");
    try {
      const result = await client.createCore(draft);
      setCoreMemoryId(result.memory_id ?? result.id ?? "");
      setDraft(emptyDraft);
      await load();
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const inspectCore = async () => {
    if (!coreMemoryId.trim() || busy) return;
    setBusy("integrity");
    try { setIntegrity(await client.integrity(coreMemoryId.trim())); }
    catch (reason) { if (reason instanceof ApiError) setError(reason); }
    finally { setBusy(""); }
  };

  const archiveCore = async () => {
    if (!coreMemoryId.trim() || busy || !window.confirm("归档后不再默认注入 Codex，但不会物理删除文件。")) return;
    setBusy("archive");
    try {
      await client.archive(coreMemoryId.trim());
      setIntegrity(null);
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason);
    } finally {
      setBusy("");
    }
  };

  const clearFilters = () => setFilters({ projectId: "", agent: "", type: "", importance: "", q: "", limit: REVIEW_LIMIT, offset: 0 });

  if (!active) return <div className="loop-state">连接本机服务后显示记忆审核。</div>;

  return <div className="loop-page memory-review-page">
    <section className="workspace-hero memory-review-hero">
      <div>
        <span className="desktop-eyebrow">OWNER AUTHORITY</span>
        <h2>候选记忆与主人决定</h2>
        <p>决定哪些候选内容可以进入长期记忆。AI 可以提议，但不能替主人按下批准。</p>
      </div>
      <div className="workspace-hero-actions">
        <div className="workspace-counter"><strong>{items.length}</strong><span>当前页候选</span></div>
        <button className="button secondary" disabled={Boolean(busy)} onClick={() => void load()}>刷新候选</button>
      </div>
    </section>

    <Notice kind="warning"><strong>这里是唯一的记忆变更入口。</strong> Auto Review SHADOW 只提供建议和风险解释，不会代替主人点击批准、拒绝、归档或新增长期记忆。</Notice>
    {error && <div className="loop-state error">{error.status === 409 ? "候选内容已变化，请刷新后重新审核。" : error.status === 401 ? "需要本地授权" : error.status === 503 ? "服务暂不可用" : "操作失败，已保留编辑内容。"}</div>}

    <section className="review-workbench">
      <aside className="loop-panel review-queue-panel">
        <header className="loop-panel-heading">
          <div><span className="desktop-eyebrow">INBOX</span><h2>待审核记忆</h2></div>
          {hasFilters(filters) && <button className="text-button" onClick={clearFilters}>清除筛选</button>}
        </header>
        <div className="review-filter-grid">
          <label>项目<input placeholder="全部项目" value={filters.projectId} onChange={(e) => setFilters({ ...filters, projectId: e.target.value, offset: 0 })} /></label>
          <label>提议者<input placeholder="全部 Agent" value={filters.agent} onChange={(e) => setFilters({ ...filters, agent: e.target.value, offset: 0 })} /></label>
          <label>类型<input placeholder="全部类型" value={filters.type} onChange={(e) => setFilters({ ...filters, type: e.target.value, offset: 0 })} /></label>
          <label>重要性<select value={filters.importance} onChange={(e) => setFilters({ ...filters, importance: e.target.value, offset: 0 })}><option value="">全部重要性</option><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
          <label className="review-search-field">关键词<input placeholder="搜索标题或内容" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value, offset: 0 })} /></label>
        </div>

        <div className="review-candidate-list">
          {items.length ? items.map((item) => (
            <button
              className={`review-candidate-card ${selected?.memory_id === item.memory_id ? "active" : ""}`}
              key={item.memory_id}
              onClick={() => void openCandidate(item)}
            >
              <div className="review-card-title"><strong>{item.title ?? item.memory_id}</strong><span className={`pill ${item.importance === "high" ? "warning" : "neutral"}`}>{item.importance ?? "未知"}</span></div>
              <p>{item.content_preview ?? "无预览"}</p>
              <div className="review-card-meta"><span>{item.project_ids?.join("、") || "未绑定项目"}</span><span>{item.proposed_by ?? "未知 Agent"}</span></div>
              <small>置信度 {confidenceLabel(item.confidence)} · {dt(item.created_at)}</small>
            </button>
          )) : <Empty text={hasFilters(filters) ? "筛选后没有候选记忆。" : "没有待审核记忆。"} />}
        </div>
        <div className="loop-pager"><button disabled={filters.offset === 0} onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - REVIEW_LIMIT) })}>上一页</button><span>第 {Math.floor(filters.offset / REVIEW_LIMIT) + 1} 页</span><button onClick={() => setFilters({ ...filters, offset: filters.offset + REVIEW_LIMIT })}>下一页</button></div>
      </aside>

      <section className="loop-panel review-detail-panel">
        {selected ? <>
          <header className="review-detail-header">
            <div><span className="desktop-eyebrow">CANDIDATE DETAIL</span><h2>{selected.title ?? selected.memory_id}</h2><small>{selected.memory_id}</small></div>
            <div className="review-detail-badges"><span className={`pill ${selected.importance === "high" ? "warning" : "neutral"}`}>{selected.importance ?? "未知重要性"}</span><span className="pill neutral">置信度 {confidenceLabel(selected.confidence)}</span></div>
          </header>

          <div className="review-fact-grid">
            <div><strong>来源：{selected.source_name || "尚未获得"}</strong>{selected.source_session_id && onOpenInspector && <button className="text-button" onClick={() => onOpenInspector({ source_type: "codex_session", conversation_id: selected.source_session_id })}>打开来源检查</button>}</div>
            <div><strong>对话：{selected.conversation_title || "尚未获得"}</strong>{selected.source_message_id && onOpenInspector && <button className="text-button" onClick={() => onOpenInspector({ message_id: selected.source_message_id })}>打开原文检查</button>}</div>
            <div><strong>原文片段：{selected.message_excerpt || "尚未获得"}</strong></div>
            <div><strong>时间：{dt(selected.provenance_at || selected.created_at)}</strong></div>
            <div><strong>当前状态：{selected.current_state || "尚未获得"}</strong></div>
            <div><strong>历史状态：{selected.history_state || "尚未获得"}</strong></div>
            <div><span>影响 Agent</span><strong>{selected.affected_agents?.join("、") || "尚未获得"}</strong></div>
            <div><span>当前 Hash</span><strong className="mono-truncate">{selected.current_hash ?? "尚未获得"}</strong></div>
          </div>

          <section className="review-provenance">
            <div><p>为什么：{selected.proposal_reason ?? "尚未获得"}</p></div>
            <div><span>相似长期记忆</span><p>{selected.similar_core?.map((item) => item.title ?? item.memory_id).join("；") || "没有发现相似 Core Memory"}</p></div>
          </section>

          <label className="review-editor">审核后的记忆内容<textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} /></label>

          <div className="review-action-dock">
            <div className="review-approve-actions">
              <button className="button primary" disabled={!canApprove(selected.current_hash) || Boolean(busy)} onClick={() => void approve(false)}>{busy === "approve" ? "批准中…" : "批准"}</button>
              <button className="button secondary" disabled={!canApprove(selected.current_hash) || Boolean(busy)} onClick={() => void approve(true)}>{busy === "edit-approve" ? "保存中…" : "编辑后批准"}</button>
              <button className="button secondary" onClick={() => setSelected(null)}>稍后处理</button>
            </div>
            <div className="review-reject-box">
              <label>拒绝理由（必填）<input placeholder="说明为什么不进入长期记忆" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} /></label>
              <button className="button danger" disabled={Boolean(busy) || !rejectReason.trim() || !selected.current_hash} onClick={() => void reject()}>{busy === "reject" ? "拒绝中…" : "拒绝候选"}</button>
            </div>
          </div>
        </> : <div className="workspace-empty-detail"><span className="desktop-eyebrow">REVIEW</span><h2>选择一条候选记忆</h2><p>右侧会显示完整内容、来源链、相似记忆与影响范围。没有选中时不提供任何变更按钮。</p></div>}
      </section>
    </section>

    <section className="loop-grid memory-maintenance-grid">
      <div className="loop-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">MANUAL MEMORY</span><h2>手动新增长期记忆</h2></div></header>
        <div className="memory-create-grid">
          <label>标题<input placeholder="清晰、可检索的标题" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></label>
          <label>项目<input placeholder="多个项目用逗号分隔" value={draft.project_ids.join(",")} onChange={(e) => setDraft({ ...draft, project_ids: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></label>
          <label>类型<input placeholder="decision / preference / fact" value={draft.memory_type} onChange={(e) => setDraft({ ...draft, memory_type: e.target.value })} /></label>
          <label>重要性<select value={draft.importance} onChange={(e) => setDraft({ ...draft, importance: e.target.value })}><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
          <label>隐私<select value={draft.privacy} onChange={(e) => setDraft({ ...draft, privacy: e.target.value as "private" | "restricted" })}><option value="private">private</option><option value="restricted">restricted</option></select></label>
          <label>标签<input placeholder="多个标签用逗号分隔" value={draft.tags.join(",")} onChange={(e) => setDraft({ ...draft, tags: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></label>
        </div>
        <label>内容<textarea value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} placeholder="记录以后需要被可靠取回的事实、决策或偏好" /></label>
        <div className="panel-footer-actions"><button className="button primary" disabled={busy === "create-core" || !draft.title.trim() || !draft.content.trim()} onClick={() => void createCore()}>{busy === "create-core" ? "加入中…" : "确认加入长期记忆"}</button></div>
      </div>

      <div className="loop-panel">
        <header className="loop-panel-heading"><div><span className="desktop-eyebrow">INTEGRITY</span><h2>长期记忆健康</h2></div></header>
        <p className="panel-description">从 Memory Inspector 复制 Core Memory ID 后检查。归档后不再默认注入 Codex，但不会物理删除文件。</p>
        <label>Core Memory ID<input placeholder="MEM-..." value={coreMemoryId} onChange={(e) => setCoreMemoryId(e.target.value)} /></label>
        <div className="toolbar"><button className="button secondary" disabled={!coreMemoryId.trim() || Boolean(busy)} onClick={() => void inspectCore()}>查看详情</button><button className="button danger" disabled={!coreMemoryId.trim() || Boolean(busy)} onClick={() => void archiveCore()}>归档</button></div>
        {integrity ? <div className="danger-note"><strong>{integrity.state}</strong><p>{integrityMessage(integrity.state)}</p><small>{integrity.relative_path ?? "无路径引用"}</small><button className="text-button" onClick={() => setIntegrity(null)}>收起结果</button></div> : <Empty text="输入 Core Memory ID 后检查文件与数据库引用状态。" />}
      </div>
    </section>
  </div>;
}
