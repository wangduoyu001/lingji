import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api";
import type { PageProps, Row } from "../types";
import "./MemoryInspectorPage.css";

type PageResult<T> = { items: T[]; pagination?: { limit?: number; offset?: number; total?: number | null; has_more?: boolean } };
type InspectorStatus = Row & { state?: string; workspace?: string; source_count?: number | null; conversation_count?: number | null; message_count?: number | null; memory_count?: number | null; chunk_count?: number | null; vector_coverage?: number | null; rebuild_required?: boolean | null; as_of?: string | null };

const LIMIT = 30;
const value = (row: Row | null, ...keys: string[]) => keys.map((key) => row?.[key]).find((item) => item !== undefined && item !== null && item !== "");
const text = (item: unknown) => item === undefined || item === null || item === "" ? "未知" : String(item);
const count = (item: unknown) => typeof item === "number" ? item.toLocaleString() : "未知";
const time = (item: unknown) => item ? new Date(String(item)).toLocaleString() : "未知";
const query = (params: Record<string, unknown>) => {
  const result = new URLSearchParams();
  Object.entries(params).forEach(([key, item]) => { if (item !== "" && item !== undefined && item !== null) result.set(key, String(item)); });
  return result.toString();
};
const privacyClass = (row: Row) => String(value(row, "privacy", "privacy_level") || "").toLowerCase() === "restricted" ? " restricted" : "";
const triState = (item: unknown) => item === true ? "需要重建" : item === false ? "无需重建" : "未知";

function StateView({ error, empty, filtered }: { error: ApiError | null; empty: boolean; filtered?: boolean }) {
  if (error?.status === 401) return <div className="inspector-state error">需要本地授权或 Token 配置</div>;
  if (error?.status === 503 || error?.code === "READ_MODEL_UNAVAILABLE") return <div className="inspector-state error">结构化读取模型暂不可用</div>;
  if (error?.code === "NETWORK_UNAVAILABLE") return <div className="inspector-state error">本机控制服务不可用</div>;
  if (error) return <div className="inspector-state error">读取失败，请检查本机服务状态</div>;
  if (empty) return <div className="inspector-state">{filtered ? "筛选后没有结果" : "系统正常，但还没有导入数据"}</div>;
  return null;
}

export default function MemoryInspectorPage({ api, active }: PageProps) {
  const [status, setStatus] = useState<InspectorStatus | null>(null);
  const [sources, setSources] = useState<Row[]>([]);
  const [conversations, setConversations] = useState<Row[]>([]);
  const [messages, setMessages] = useState<Row[]>([]);
  const [source, setSource] = useState<Row | null>(null);
  const [conversation, setConversation] = useState<Row | null>(null);
  const [message, setMessage] = useState<Row | null>(null);
  const [memory, setMemory] = useState<Row | null>(null);
  const [memorySource, setMemorySource] = useState<Row | null>(null);
  const [vector, setVector] = useState<Row | null>(null);
  const [filters, setFilters] = useState({ source_type: "", project: "", privacy: "", status: "", role: "", keyword: "", start_time: "", end_time: "" });
  const [search, setSearch] = useState("");
  const [offsets, setOffsets] = useState({ source: 0, conversation: 0, message: 0 });
  const [totals, setTotals] = useState({ source: null as number | null, conversation: null as number | null, message: null as number | null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const requestId = useRef(0);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => { const id = window.setTimeout(() => setSearch(filters.keyword), 300); return () => window.clearTimeout(id); }, [filters.keyword]);

  const load = useCallback(async () => {
    if (!active) return;
    controller.current?.abort();
    const abort = new AbortController(); controller.current = abort;
    const id = ++requestId.current; setLoading(true); setError(null);
    const common = { project: filters.project, privacy: filters.privacy, status: filters.status, keyword: search, start_time: filters.start_time, end_time: filters.end_time };
    try {
      const [s, c, m, st] = await Promise.all([
        api.get<PageResult<Row>>(`/api/memory/inspector/sources?${query({ ...common, source_type: filters.source_type, limit: LIMIT, offset: offsets.source })}`, { signal: abort.signal }),
        api.get<PageResult<Row>>(`/api/memory/inspector/conversations?${query({ ...common, source_id: value(source, "source_id"), limit: LIMIT, offset: offsets.conversation })}`, { signal: abort.signal }),
        api.get<PageResult<Row>>(`/api/memory/inspector/messages?${query({ ...common, role: filters.role, conversation_id: value(conversation, "conversation_id"), limit: LIMIT, offset: offsets.message })}`, { signal: abort.signal }),
        api.get<InspectorStatus>("/api/memory/inspector/status", { signal: abort.signal }),
      ]);
      if (id !== requestId.current) return;
      setSources(s.items || []); setConversations(c.items || []); setMessages(m.items || []); setStatus(st);
      setTotals({ source: s.pagination?.total ?? null, conversation: c.pagination?.total ?? null, message: m.pagination?.total ?? null });
    } catch (reason) { if (id === requestId.current && !(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) setError(reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Unknown error")); }
    finally { if (id === requestId.current) setLoading(false); }
  }, [active, api, conversation, filters.end_time, filters.privacy, filters.project, filters.role, filters.source_type, filters.start_time, filters.status, offsets, search, source]);

  useEffect(() => { void load(); return () => controller.current?.abort(); }, [load]);
  useEffect(() => { setOffsets((old) => ({ ...old, source: 0, conversation: 0, message: 0 })); }, [filters.source_type, filters.project, filters.privacy, filters.status, filters.role, search, filters.start_time, filters.end_time]);

  const openMemory = async (row: Row) => {
    const memoryId = value(row, "memory_id"); if (!memoryId) return;
    const abort = new AbortController();
    const [detail, origin, vectorResult] = await Promise.allSettled([
      api.get<Row>(`/api/memory/inspector/memories/${encodeURIComponent(String(memoryId))}`, { signal: abort.signal }),
      api.get<Row>(`/api/memory/inspector/memories/${encodeURIComponent(String(memoryId))}/source`, { signal: abort.signal }),
      api.get<Row>(`/api/memory/inspector/memories/${encodeURIComponent(String(memoryId))}/vector`, { signal: abort.signal }),
    ]);
    setMemory(detail.status === "fulfilled" ? (detail.value.item as Row || detail.value) : row);
    setMemorySource(origin.status === "fulfilled" ? origin.value : null);
    setVector(vectorResult.status === "fulfilled" ? vectorResult.value : null);
  };

  const memories = useMemo(() => {
    const linked = value(message, "memories", "memory_links", "related_memories");
    return Array.isArray(linked) ? linked as Row[] : [];
  }, [message]);
  const isRestricted = message ? privacyClass(message).includes("restricted") : false;

  if (!active) return <div className="inspector-state">连接本机服务后显示 Memory Inspector（记忆检查器）</div>;

  return <div className="memory-inspector">
    <div className="inspector-status">
      {[['Source', value(status, 'source_count', 'sources')], ['Conversation', value(status, 'conversation_count', 'conversations')], ['Message', value(status, 'message_count', 'messages')], ['Memory', value(status, 'memory_count', 'memories')], ['Chunk', value(status, 'chunk_count', 'chunks')]].map(([label, item]) => <div key={String(label)}><span>{label}</span><strong>{count(item)}</strong></div>)}
      <div><span>Vector 覆盖</span><strong>{typeof value(status, 'vector_coverage', 'coverage') === 'number' ? `${Number(value(status, 'vector_coverage', 'coverage')) * 100}%` : '未知'}</strong></div>
      <div><span>读取模型</span><strong>{text(value(status, 'state'))}</strong></div>
      <div><span>重建状态</span><strong>{triState(value(status, 'rebuild_required'))}</strong></div>
      <div><span>最后更新</span><strong>{time(value(status, 'as_of', 'updated_at'))}</strong></div>
    </div>

    <div className="inspector-filters">
      {([['source_type','来源类型'],['project','项目'],['privacy','隐私'],['status','状态'],['role','角色']] as const).map(([key,label]) => <input key={key} value={filters[key]} placeholder={label} onChange={(e) => setFilters({ ...filters, [key]: e.target.value })} />)}
      <input value={filters.keyword} placeholder="关键词搜索" onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} />
      <input type="datetime-local" value={filters.start_time} onChange={(e) => setFilters({ ...filters, start_time: e.target.value })} />
      <input type="datetime-local" value={filters.end_time} onChange={(e) => setFilters({ ...filters, end_time: e.target.value })} />
      <button className="button secondary" disabled={loading} onClick={() => void load()}>{loading ? '读取中…' : '刷新'}</button>
    </div>
    {error && <StateView error={error} empty={false} />}

    <div className="inspector-columns">
      <section><h2>Source 来源 <small>{count(totals.source)}</small></h2><StateView error={null} empty={!loading && !sources.length} filtered={Boolean(filters.source_type || filters.project || filters.privacy || filters.status || search)} />{sources.map((row) => <button key={String(value(row,'source_id'))} className={`inspector-item${privacyClass(row)} ${value(source,'source_id') === value(row,'source_id') ? 'active':''}`} onClick={() => { setSource(row); setConversation(null); setMessage(null); }}><strong>{text(value(row,'name','title','source_name'))}</strong><span>{text(value(row,'source_type','type'))} · {text(value(row,'privacy','privacy_level'))}</span><span>项目 {text(value(row,'project'))} · 状态 {text(value(row,'status'))}</span><span>对话 {count(value(row,'conversation_count'))} · 消息 {count(value(row,'message_count'))}</span><small>{time(value(row,'updated_at'))}</small></button>)}<Pager offset={offsets.source} total={totals.source} set={(v) => setOffsets({...offsets,source:v})}/></section>
      <section><h2>Conversation 对话 <small>{count(totals.conversation)}</small></h2><StateView error={null} empty={!loading && !conversations.length} filtered={Boolean(source || filters.project || filters.privacy || filters.status || search)} />{conversations.map((row) => <button key={String(value(row,'conversation_id'))} className={`inspector-item${privacyClass(row)} ${value(conversation,'conversation_id') === value(row,'conversation_id') ? 'active':''}`} onClick={() => { setConversation(row); setMessage(null); }}><strong>{text(value(row,'title'))}</strong><span>{text(value(row,'participants'))}</span><span>{time(value(row,'started_at','start_time'))} → {time(value(row,'ended_at','end_time'))}</span><span>项目 {text(value(row,'project'))} · 隐私 {text(value(row,'privacy'))}</span><small>消息 {count(value(row,'message_count'))}</small></button>)}<Pager offset={offsets.conversation} total={totals.conversation} set={(v) => setOffsets({...offsets,conversation:v})}/></section>
      <section><h2>Message 消息 <small>{count(totals.message)}</small></h2><StateView error={null} empty={!loading && !messages.length} filtered={Boolean(conversation || filters.role || search)} />{messages.map((row) => <button key={String(value(row,'message_id'))} className={`inspector-item${privacyClass(row)} ${value(message,'message_id') === value(row,'message_id') ? 'active':''}`} onClick={async () => { setMessage(row); const id=value(row,'message_id'); if(id){ try { const result=await api.get<Row>(`/api/memory/inspector/messages/${encodeURIComponent(String(id))}`); setMessage((result.item as Row)||result); } catch{} } }}><strong>{text(value(row,'role'))} · {text(value(row,'author'))}</strong><span>{time(value(row,'created_at','timestamp'))}</span><span>模型 {text(value(row,'model'))} · 分支 {text(value(row,'branch','branch_id'))}</span><small>{isRestricted ? '受限内容，点击查看' : text(value(row,'preview','content_preview'))}</small></button>)}<Pager offset={offsets.message} total={totals.message} set={(v) => setOffsets({...offsets,message:v})}/></section>
    </div>

    {message && <aside className="relation-panel"><header><div><h2>Message 详情与 Memory 关系</h2><span>{text(value(message,'message_id'))}</span></div><button onClick={() => setMessage(null)}>关闭</button></header><div className={`message-content${privacyClass(message)}`}>{isRestricted ? <details><summary>restricted 受限内容，主动展开</summary><pre>{text(value(message,'content','body'))}</pre></details> : <pre>{text(value(message,'content','body'))}</pre>}</div><h3>关联 Memory</h3>{memories.length ? memories.map((row) => <button className="memory-link" key={String(value(row,'memory_id'))} onClick={() => void openMemory(row)}>{text(value(row,'title','memory_id'))}</button>) : <p>现有接口未返回 Message → Memory 关联，关系保持明确空状态。</p>}
      {memory && <div className="memory-detail"><h3>{text(value(memory,'title'))}</h3><dl><dt>Memory ID</dt><dd>{text(value(memory,'memory_id'))}</dd><dt>类型</dt><dd>{text(value(memory,'memory_type','type'))}</dd><dt>状态</dt><dd>{text(value(memory,'status'))}</dd><dt>来源</dt><dd>{text(value(memorySource,'source_id','source'))}</dd><dt>Chunk 数量</dt><dd>{count(value(memory,'chunk_count'))}</dd><dt>Vector 状态</dt><dd>{text(value(vector,'state','status'))}</dd><dt>rebuild_required</dt><dd>{triState(value(vector,'rebuild_required'))}</dd></dl><pre>{JSON.stringify(value(vector,'vector') ?? vector, null, 2)}</pre></div>}
    </aside>}
  </div>;
}

function Pager({ offset, total, set }: { offset: number; total: number | null; set: (value: number) => void }) {
  return <div className="inspector-pager"><button disabled={offset === 0} onClick={() => set(Math.max(0, offset - LIMIT))}>上一页</button><span>{Math.floor(offset / LIMIT) + 1} / {total === null ? '未知' : Math.max(1, Math.ceil(total / LIMIT))}</span><button disabled={total !== null && offset + LIMIT >= total} onClick={() => set(offset + LIMIT)}>下一页</button></div>;
}
