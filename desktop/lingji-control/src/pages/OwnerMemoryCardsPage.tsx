import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type LingJiApi } from "../api";
import { Empty, Notice } from "../components/ui";
import type { PageId } from "../types";
import { OwnerMemoryCardsApi } from "./ownerMemoryCardsApi";
import type { OwnerMemoryCard } from "./ownerMemoryCardsTypes";
import { OWNER_MEMORY_CARD_LIMIT } from "./ownerMemoryCardsTypes";
import "./LocalMemoryLoop.css";

const text = (value: unknown, fallback = "尚未获得") => value === null || value === undefined || value === "" ? fallback : String(value);
const time = (value: unknown) => value ? new Date(String(value)).toLocaleString() : "时间尚未获得";
const freshnessLabels: Record<string, string> = { current: "当前", overdue: "可能过时", stale: "可能过时", superseded: "已被新版本替代", source_revoked: "来源已停止", invalidated: "可能过时", archived: "已移出当前记忆", unknown: "尚未判断" };
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
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [editContent, setEditContent] = useState("");
  const [reason, setReason] = useState("");
  const requestId = useRef(0);

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

  const open = async (card: OwnerMemoryCard) => {
    setDetailLoading(true); setError(null); setMessage(null);
    try { const response = await client.detail(card.memory_id); const item = response.item ?? card; setSelected(item); setEditContent(item.conclusion ?? item.developments?.[0] ?? ""); }
    catch (value) { if (value instanceof ApiError) setError(value); }
    finally { setDetailLoading(false); }
  };
  const run = async (kind: string, call: () => Promise<unknown>, confirmation: string) => {
    if (!selected || busy || !window.confirm(confirmation)) return;
    setBusy(kind); setError(null);
    try { await call(); const fresh = await client.detail(selected.memory_id); setSelected(fresh.item); setEditContent(fresh.item.conclusion ?? ""); setReason(""); await load(offset); }
    catch (value) { if (value instanceof ApiError) setError(value); }
    finally { setBusy(""); }
  };
  const source = async () => {
    const id = selected?.evidence?.[0]?.message_id;
    if (!id || busy) return;
    setBusy("source");
    try { const response = await client.message(id); setMessage(response.item ?? null); }
    catch (value) { if (value instanceof ApiError) setError(value); }
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
      return <article className="owner-memory-card" key={card.memory_id} tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); void open(card); } }}>
        <button className="owner-memory-card-title" onClick={() => void open(card)}>{text(card.topic, "未命名记忆")}</button>
        <div className="owner-memory-developments">{evidence.slice(0, 3).map((line, index) => <p key={`${card.memory_id}-${index}`}>{line}</p>)}</div>
        <p className="owner-memory-conclusion"><strong>最新结论：</strong>{text(card.conclusion, "最新结论尚未获得")}</p>
        <div className="owner-memory-freshness"><span className="pill neutral">{freshnessLabels[freshness] ?? "尚未判断"}</span><small>{text(card.freshness?.reason, "时效尚未判断")} · {time(card.freshness?.latest_evidence_at)}</small></div>
        <p className="owner-memory-source"><strong>来源：</strong>{text(card.source?.label)} · {card.source?.message_count == null ? "消息数尚未获得" : `${card.source.message_count} 条消息`}</p>
        <div className="owner-memory-layers">{Object.entries(layerLabels).map(([key, label]) => <span className="pill neutral" key={key}>{label}：{stateLabels[String(card.layers?.[key]?.state || "unknown")] ?? "尚未获得"}</span>)}</div>
        <p className="owner-memory-trust">可信提示：{trustLabels[String(card.trust?.state || "unknown")] ?? "可信度尚未判断"}</p>
        <p className="owner-memory-action">建议：{text(card.action?.label, "查看详情")}</p>
        <button className="button secondary owner-memory-action-button" onClick={() => void open(card)}>{text(card.action?.label, "查看详情")}</button>
      </article>;
    })}</section>}
    <div className="loop-pager owner-memory-pager"><button disabled={offset === 0 || loading} onClick={() => void load(Math.max(0, offset - OWNER_MEMORY_CARD_LIMIT))}>上一页</button><span>{total == null ? `第 ${Math.floor(offset / OWNER_MEMORY_CARD_LIMIT) + 1} 页` : `${Math.floor(offset / OWNER_MEMORY_CARD_LIMIT) + 1} / ${Math.max(1, Math.ceil(total / OWNER_MEMORY_CARD_LIMIT))}`}</span><button disabled={!hasMore || loading} onClick={() => void load(offset + OWNER_MEMORY_CARD_LIMIT)}>下一页</button></div>
    {detailLoading && <div className="workspace-empty-detail" aria-busy="true">正在读取这条记忆…</div>}
    {selected && !detailLoading && <section className="loop-panel owner-memory-detail" aria-label="记忆详情"><header><div><h2 tabIndex={-1}>{text(selected.topic, "记忆详情")}</h2><p>{text(selected.conclusion, "最新结论尚未获得")}</p></div><button className="button secondary" onClick={() => setSelected(null)}>关闭详情</button></header><div className="owner-memory-detail-evidence"><h3>可核对的证据</h3>{(selected.evidence ?? []).slice(0, 3).map((item, index) => <p key={`${item.message_id}-${index}`}>{text(item.preview, "证据摘要尚未获得")} · {time(item.occurred_at)}</p>)}<button className="button secondary" disabled={!selected.evidence?.[0]?.message_id || Boolean(busy)} onClick={() => void source()}>{busy === "source" ? "读取中…" : "查看来源"}</button>{message && <div className="owner-memory-message"><strong>选定来源消息</strong><p>{text(message.content, "原文尚未获得")}</p></div>}</div><div className="owner-memory-actions"><p>{text(selected.action?.reason, "请先确认当前状态")}</p>{(actionType(selected) === "confirm" || actionType(selected) === "review") && <><button className="button primary" disabled={Boolean(busy) || !selected.current_hash} onClick={() => void run("approve", () => client.approve(selected.memory_id, selected.current_hash ?? ""), "确认把这条内容加入长期记忆吗？")}>{busy === "approve" ? "确认中…" : "确认加入长期记忆"}</button><button className="button secondary" disabled={Boolean(busy) || !selected.current_hash} onClick={() => void run("edit-approve", () => client.editApprove(selected.memory_id, selected.current_hash ?? "", editContent), "保存修正后加入长期记忆吗？")}>编辑确认</button><button className="button danger" disabled={Boolean(busy) || !selected.current_hash || !reason.trim()} onClick={() => void run("reject", () => client.reject(selected.memory_id, selected.current_hash ?? "", reason), "拒绝这条候选内容吗？")}>拒绝</button><input aria-label="拒绝理由" placeholder="拒绝理由（必填）" value={reason} onChange={(event) => setReason(event.target.value)} /></>}{actionType(selected) === "correct" && <><textarea aria-label="修正内容" value={editContent} onChange={(event) => setEditContent(event.target.value)} /><input aria-label="修正原因" placeholder="说明为什么修正（必填）" value={reason} onChange={(event) => setReason(event.target.value)} /><button className="button secondary" disabled={Boolean(busy) || !selected.current_hash || !reason.trim()} onClick={() => void run("correct", () => client.correct(selected.memory_id, selected.current_hash ?? "", editContent, reason), "这会生成新的当前版本，旧版本仍保留。继续吗？")}>修正内容</button></>}{actionType(selected) === "invalidate" && <><input aria-label="过时原因" placeholder="说明为什么已经过时（必填）" value={reason} onChange={(event) => setReason(event.target.value)} /><button className="button secondary" disabled={Boolean(busy) || !selected.current_hash || !reason.trim()} onClick={() => void run("invalidate", () => client.invalidate(selected.memory_id, selected.current_hash ?? "", reason), "标记后这条内容会保留在历史中，但不再作为当前记忆。继续吗？")}>标记已经过时</button></>}{actionType(selected) === "archive" && <><input aria-label="移出原因" placeholder="说明为什么移出当前记忆（必填）" value={reason} onChange={(event) => setReason(event.target.value)} /><button className="button danger" disabled={Boolean(busy) || !selected.current_hash || !reason.trim()} onClick={() => void run("archive", () => client.archive(selected.memory_id, selected.current_hash ?? "", reason), "移出当前记忆？原始记录、历史和审计仍会保留。")}>移出当前记忆</button></>}</div></section>}
    <div className="owner-memory-footer"><button className="button secondary" onClick={() => onNavigate("memory_sources")}>查看记忆来源</button><button className="button secondary" onClick={() => onNavigate("diagnostics")}>高级诊断</button></div>
  </div>;
}
