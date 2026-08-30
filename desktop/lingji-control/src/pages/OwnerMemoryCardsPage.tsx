import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type LingJiApi } from "../api";
import { Empty, Notice } from "../components/ui";
import type { PageId } from "../types";
import { OwnerMemoryCardsApi } from "./ownerMemoryCardsApi";
import type { OwnerMemoryCard } from "./ownerMemoryCardsTypes";
import { OWNER_MEMORY_CARD_LIMIT } from "./ownerMemoryCardsTypes";
import "./LocalMemoryLoop.css";

const text = (value: unknown, fallback = "尚未获得") => value === null || value === undefined || value === "" ? fallback : String(value);
const time = (value: unknown) => { if (!value) return "时间尚未获得"; const date = new Date(String(value)); return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString(); };
const freshnessLabels: Record<string, string> = { current: "当前", overdue: "可能过时", stale: "可能过时", superseded: "已被新版本替代", source_revoked: "来源已停止", invalidated: "可能过时", archived: "已移出当前记忆", rejected: "已拒绝", rolled_back: "已回滚", repair_required: "需要修复", not_yet_current: "尚未生效", unknown: "尚未判断" };
const layerLabels: Record<string, string> = { raw: "原始记录", structured: "结构记录", vector: "语义向量", permanent: "长期记忆" };
const stateLabels: Record<string, string> = { available: "已有", complete: "已有", partial: "部分", unknown: "尚未获得", unavailable: "不可用", not_permanent: "尚未加入", pending_owner_review: "待确认", current: "已有" };
const trustLabels: Record<string, string> = { trusted: "来源可核对", conflict: "存在冲突", provenance_mismatch: "来源需要核对", low_confidence: "需要补证据", unknown: "可信度尚未判断" };
const actionType = (card: OwnerMemoryCard) => String(card.action?.type || "");

export default function OwnerMemoryCardsPage({ api, active, onNavigate }: { api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const client = useMemo(() => new OwnerMemoryCardsApi(api), [api]);
  const [items, setItems] = useState<OwnerMemoryCard[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [selected, setSelected] = useState<OwnerMemoryCard | null>(null);
  const [message, setMessage] = useState<{ content?: string | null } | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [editContent, setEditContent] = useState("");
  const [reason, setReason] = useState("");
  const requestId = useRef(0);
  const detailHeadingRef = useRef<HTMLHeadingElement>(null);
  const detailTriggerRef = useRef<HTMLButtonElement>(null);
  const [feedback, setFeedback] = useState("");

  const load = useCallback(async (nextOffset = offset) => {
    if (!active) return;
    const id = ++requestId.current;
    setLoading(true); setError(null);
    try {
      const response = await client.list(nextOffset);
      if (id !== requestId.current) return;
      setItems(Array.isArray(response.items) ? response.items : []);
      const pagination = response.pagination ?? {};
      setOffset(Number(pagination.offset ?? nextOffset));
      setTotal(typeof pagination.total === "number" ? pagination.total : null);
      setHasMore(Boolean(pagination.has_more));
    } catch (value) {
      if (id === requestId.current && value instanceof ApiError) setError(value);
    } finally { if (id === requestId.current) setLoading(false); }
  }, [active, client, offset]);
  useEffect(() => { void load(0); }, [active, client]);

  const open = async (card: OwnerMemoryCard, trigger?: HTMLButtonElement) => {
    detailTriggerRef.current = trigger ?? null;
    setDetailLoading(true); setError(null); setMessage(null);
    try {
      const response = await client.detail(card.memory_id);
      const item = response.item ?? card;
      setSelected(item);
      setSelectedMessageId(item.evidence?.[0]?.message_id ?? null);
      setEditContent(item.conclusion ?? item.developments?.[0] ?? "");
      if (actionType(item) === "correct") {
        try {
          const canonical = await client.canonical(item.memory_id);
          const content = (canonical.item?.chunks ?? []).map((chunk) => String(chunk.text ?? "").trim()).filter(Boolean).join("\n\n");
          if (content) setEditContent(content);
        } catch { /* canonical detail is optional until the owner edits */ }
      }
    }
    catch (value) { if (value instanceof ApiError) setError(value); }
    finally { setDetailLoading(false); }
  };
  const run = async (kind: string, call: () => Promise<unknown>, confirmation: string) => {
    if (!selected || busy || !window.confirm(confirmation)) return;
    setBusy(kind); setError(null);
    try {
      setFeedback("正在保存…");
      const result = await call();
      const resultId = kind === "correct" && result && typeof result === "object" && "id" in result ? String((result as { id?: unknown }).id ?? selected.memory_id) : selected.memory_id;
      const fresh = await client.detail(resultId);
      setSelected(fresh.item); setSelectedMessageId(fresh.item.evidence?.[0]?.message_id ?? null); setEditContent(fresh.item.conclusion ?? ""); setReason(""); setFeedback("已保存，当前状态已刷新。"); await load(offset);
    }
    catch (value) {
      if (value instanceof ApiError) {
        setError(value);
        setFeedback(value.status === 409 ? "这条内容刚刚发生变化，请刷新后再决定。" : "保存失败，请稍后重试。");
      } else {
        setFeedback("保存失败，请稍后重试。");
      }
    }
    finally { setBusy(""); }
  };
  const closeDetail = () => {
    const trigger = detailTriggerRef.current;
    setSelected(null);
    window.setTimeout(() => trigger?.focus(), 0);
  };
  useEffect(() => {
    if (!selected || detailLoading) return;
    detailHeadingRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeDetail();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selected, detailLoading]);
  const source = async () => {
    const id = selectedMessageId;
    if (!id || busy) return;
    setBusy("source");
    setFeedback("正在读取选定来源…");
    try { const response = await client.message(id); setMessage(response.item ?? null); setFeedback("已读取选定来源。"); }
    catch (value) { if (value instanceof ApiError) setError(value); setFeedback("来源暂时无法读取，请稍后重试。"); }
    finally { setBusy(""); }
  };
  const distribution = useMemo(() => Array.from(new Set(items.map((item) => text(item.source?.label, "来源未知")))).join("、") || "尚未获得", [items]);
  if (!active) return <div className="loop-state">连接本机服务后显示记忆内容。</div>;
  return <div className="loop-page owner-memory-cards-page">
    <section className="workspace-hero memory-cards-hero"><div><h2>记忆内容</h2><p>每张卡讲清一件事：发生了什么、最新结论、来源和是否需要你决定。</p></div><button className="button secondary" disabled={loading} onClick={() => void load(offset)}>{loading ? "刷新中…" : "刷新内容"}</button></section>
    {error && <Notice kind="error">{error.status === 409 ? "这条内容刚刚发生变化，请刷新后再决定。" : "记忆内容暂时读不出来，原始记录没有被删除。请稍后重试。"}</Notice>}
    <section className="memory-cards-summary" aria-live="polite"><strong>已显示 {items.length} / 共 {total === null ? "尚未获得" : total} 条</strong><span>来源：{distribution}</span></section>
    {loading && items.length === 0 ? <div className="loop-state" aria-busy="true">正在读取你的记忆内容…</div> : items.length === 0 ? <Empty text="还没有可展示的记忆卡片。接管一个来源并完成一次检查后，这里会出现具体内容。" /> : <section className="owner-memory-card-grid" aria-label="记忆卡片">{items.map((card) => {
      const freshness = String(card.freshness?.state || "unknown");
      const evidence = card.developments ?? card.evidence_lines ?? [];
      return <article className="owner-memory-card" key={card.memory_id} tabIndex={0} onKeyDown={(event) => { if (event.target !== event.currentTarget) return; if (event.key === "Enter" || event.key === " ") { event.preventDefault(); void open(card, event.currentTarget.querySelector<HTMLButtonElement>(".owner-memory-card-title") ?? undefined); } }}>
        <button className="owner-memory-card-title" onClick={(event) => void open(card, event.currentTarget)}>{text(card.topic, "未命名记忆")}</button>
        <div className="owner-memory-developments">{evidence.slice(0, 3).map((line, index) => <p key={`${card.memory_id}-${index}`}>{line}</p>)}</div>
        <p className="owner-memory-conclusion"><strong>最新结论：</strong>{text(card.conclusion, "最新结论尚未获得")}</p>
        <div className="owner-memory-freshness"><span className="pill neutral">{freshnessLabels[freshness] ?? "尚未判断"}</span><small>{text(card.freshness?.reason, "时效尚未判断")} · {time(card.freshness?.latest_evidence_at)}</small></div>
        <p className="owner-memory-source"><strong>来源：</strong>{text(card.source?.label)} · {card.source?.message_count == null ? "消息数尚未获得" : `${card.source.message_count} 条消息`} · 最近证据：{time(card.source?.latest_evidence_at)}</p>
        <div className="owner-memory-layers">{Object.entries(layerLabels).map(([key, label]) => <span className="pill neutral" key={key}>{label}：{stateLabels[String(card.layers?.[key]?.state || "unknown")] ?? "尚未获得"}</span>)}</div>
        <p className="owner-memory-trust">可信提示：{trustLabels[String(card.trust?.state || "unknown")] ?? "可信度尚未判断"}</p>
        <p className="owner-memory-action">建议：{text(card.action?.label, "查看详情")}</p>
        <button className="button secondary owner-memory-action-button" onClick={(event) => void open(card, event.currentTarget)} aria-label={`${text(card.action?.label, "查看详情")}：${text(card.topic, "记忆")}`}>{text(card.action?.label, "查看详情")}</button>
      </article>;
    })}</section>}
    <div className="loop-pager owner-memory-pager"><button disabled={offset === 0 || loading} onClick={() => void load(Math.max(0, offset - OWNER_MEMORY_CARD_LIMIT))}>上一页</button><span>{total == null ? `第 ${Math.floor(offset / OWNER_MEMORY_CARD_LIMIT) + 1} 页` : `${Math.floor(offset / OWNER_MEMORY_CARD_LIMIT) + 1} / ${Math.max(1, Math.ceil(total / OWNER_MEMORY_CARD_LIMIT))}`}</span><button disabled={!hasMore || loading} onClick={() => void load(offset + OWNER_MEMORY_CARD_LIMIT)}>下一页</button></div>
    {detailLoading && <div className="workspace-empty-detail" aria-busy="true">正在读取这条记忆…</div>}
    {selected && !detailLoading && <section className="loop-panel owner-memory-detail" role="dialog" aria-modal="true" aria-labelledby="owner-memory-detail-title" aria-label="记忆详情"><header><div><h2 id="owner-memory-detail-title" ref={detailHeadingRef} tabIndex={-1}>{text(selected.topic, "记忆详情")}</h2><p>{text(selected.conclusion, "最新结论尚未获得")}</p></div><button className="button secondary" onClick={closeDetail}>关闭详情</button></header><div className="owner-memory-detail-evidence"><h3>可核对的证据</h3>{(selected.evidence ?? []).slice(0, 3).map((item, index) => <button className="button secondary owner-memory-evidence-row" type="button" aria-pressed={selectedMessageId === item.message_id} key={`${item.message_id}-${index}`} onClick={() => { setSelectedMessageId(item.message_id ?? null); setMessage(null); }}>{text(item.preview, "证据摘要尚未获得")} · {time(item.occurred_at)}</button>)}<button className="button secondary" disabled={!selectedMessageId || Boolean(busy)} onClick={() => void source()}>{busy === "source" ? "读取中…" : "查看来源"}</button>{message && <div className="owner-memory-message"><strong>选定来源消息</strong><p>{text(message.content, "原文尚未获得")}</p></div>}</div><div className="owner-memory-actions"><p>{text(selected.action?.reason, "请先确认当前状态")}</p>{(() => { const selectedAction = actionType(selected); const isCandidate = selected.kind !== "conversation_evidence" && (selectedAction === "confirm" || ["needs_review", "received", "preparing"].includes(String(selected.state ?? "")) || selected.layers?.permanent?.state === "pending_owner_review"); return <>{selectedAction === "reauthorize_source" && <button className="button primary" onClick={() => { setFeedback("请在记忆来源中重新授权这个来源。"); onNavigate("memory_sources"); }}>重新授权来源</button>}{isCandidate && <><textarea aria-label="候选编辑内容" value={editContent} onChange={(event) => setEditContent(event.target.value)} /><button className="button primary" disabled={Boolean(busy) || !selected.current_hash} onClick={() => void run("approve", () => client.approve(selected.memory_id, selected.current_hash ?? ""), "确认把这条内容加入长期记忆吗？")}>{busy === "approve" ? "确认中…" : "确认加入长期记忆"}</button><button className="button secondary" disabled={Boolean(busy) || !selected.current_hash} onClick={() => void run("edit-approve", () => client.editApprove(selected.memory_id, selected.current_hash ?? "", editContent), "保存修正后加入长期记忆吗？")}>{busy === "edit-approve" ? "编辑确认中…" : "编辑确认"}</button><button className="button danger" disabled={Boolean(busy) || !selected.current_hash || !reason.trim()} onClick={() => void run("reject", () => client.reject(selected.memory_id, selected.current_hash ?? "", reason), "拒绝这条候选内容吗？")}>{busy === "reject" ? "拒绝中…" : "拒绝"}</button><input aria-label="拒绝理由" placeholder="拒绝理由（必填）" value={reason} onChange={(event) => setReason(event.target.value)} /></>}{selected.kind !== "conversation_evidence" && ["correct", "invalidate", "archive"].includes(selectedAction) && <>{selectedAction === "correct" && <textarea aria-label="修正内容" value={editContent} onChange={(event) => setEditContent(event.target.value)} />}<input aria-label={`${selectedAction === "invalidate" ? "过时" : selectedAction === "archive" ? "移出" : "修正"}原因`} placeholder={`${selectedAction === "invalidate" ? "说明为什么已经过时" : selectedAction === "archive" ? "说明为什么移出当前记忆" : "说明为什么修正"}（必填）`} value={reason} onChange={(event) => setReason(event.target.value)} /><button className="button secondary" disabled={Boolean(busy) || !selected.current_hash || !reason.trim() || (selectedAction === "correct" && !editContent.trim())} onClick={() => void run(selectedAction, () => selectedAction === "correct" ? client.correct(selected.memory_id, selected.current_hash ?? "", editContent, reason) : selectedAction === "invalidate" ? client.invalidate(selected.memory_id, selected.current_hash ?? "", reason) : client.archive(selected.memory_id, selected.current_hash ?? "", reason), selectedAction === "correct" ? "这会生成新的当前版本，旧版本仍保留。继续吗？" : selectedAction === "invalidate" ? "标记后这条内容会保留在历史中，但不再作为当前记忆。继续吗？" : "移出当前记忆？原始记录、历史和审计仍会保留。")}>{busy === selectedAction ? selectedAction === "correct" ? "修正中…" : selectedAction === "invalidate" ? "标记中…" : "移出中…" : selectedAction === "correct" ? "修正内容" : selectedAction === "invalidate" ? "标记已经过时" : "移出当前记忆"}</button></>}</>})()}</div><div className="owner-memory-feedback" aria-live="polite">{feedback}</div></section>}
    <div className="owner-memory-footer"><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看记忆来源</button><button className="button secondary" onClick={() => onNavigate("diagnostics")}>高级诊断</button></div>
  </div>;
}
