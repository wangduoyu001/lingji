import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api";
import type { PageProps } from "../types";
import type { CaptureInspectorTarget } from "./captureCenterTypes";
import {
  buildConversationQuery,
  buildMessageQuery,
  buildSourceQuery,
  countLabel,
  formatList,
  INSPECTOR_LIMIT,
  isRestricted,
  mapMemorySource,
  mapMemoryVector,
  mapMessageDetail,
  mapStatus,
  rebuildLabel,
  toQueryString,
} from "./memoryInspectorContract";
import type {
  Citation,
  ConversationItem,
  InspectorFilters,
  InspectorStatusResponse,
  MemoryDetailResponse,
  MemoryItem,
  MemoryLink,
  MemorySourceResponse,
  MemoryVectorResponse,
  MessageDetailResponse,
  MessageItem,
  PageResponse,
  SourceItem,
} from "./memoryInspectorTypes";
import "./MemoryInspectorPage.css";

const baseFilters: InspectorFilters = {
  sourceType: "",
  project: "",
  privacy: "",
  status: "",
  role: "",
  q: "",
  fromTime: "",
  toTime: "",
};

function filtersForTarget(target?: CaptureInspectorTarget | null): InspectorFilters {
  return {
    ...baseFilters,
    sourceType: target?.source_type ?? "",
    project: target?.project_id ?? "",
    status: target?.core_memory_only ? "active" : "",
  };
}

const text = (value: unknown): string => value === null || value === undefined || value === "" ? "未知" : String(value);
const dateTime = (value: unknown): string => value ? new Date(String(value)).toLocaleString() : "未知";
const privacyClass = (row: { privacy?: string | null }): string => isRestricted(row) ? " restricted" : "";

function StateView({ error, empty, filtered }: { error: ApiError | null; empty: boolean; filtered?: boolean }) {
  if (error?.status === 401) return <div className="inspector-state error">需要本地授权或 Token 配置</div>;
  if (error?.status === 503 || error?.code === "READ_MODEL_UNAVAILABLE") return <div className="inspector-state error">结构化读取模型暂不可用</div>;
  if (error?.code === "NETWORK_UNAVAILABLE") return <div className="inspector-state error">本机控制服务不可用</div>;
  if (error) return <div className="inspector-state error">读取失败，请检查本机服务状态</div>;
  if (empty) return <div className="inspector-state">{filtered ? "筛选后没有结果" : "系统正常，但还没有导入数据"}</div>;
  return null;
}

export default function MemoryInspectorPage({ api, active, target = null }: PageProps & { target?: CaptureInspectorTarget | null }) {
  const [filters, setFilters] = useState<InspectorFilters>(() => filtersForTarget(target));
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState<ReturnType<typeof mapStatus> | null>(null);
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [selectedSource, setSelectedSource] = useState<SourceItem | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<ConversationItem | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<MessageItem | null>(null);
  const [memoryLinks, setMemoryLinks] = useState<MemoryLink[]>([]);
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(null);
  const [memorySource, setMemorySource] = useState<ReturnType<typeof mapMemorySource> | null>(null);
  const [memoryVector, setMemoryVector] = useState<ReturnType<typeof mapMemoryVector> | null>(null);
  const [detailError, setDetailError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [offsets, setOffsets] = useState({ source: 0, conversation: 0, message: 0 });
  const [totals, setTotals] = useState<{ source: number | null; conversation: number | null; message: number | null }>({ source: null, conversation: null, message: null });
  const listController = useRef<AbortController | null>(null);
  const listRequestId = useRef(0);
  const messageController = useRef<AbortController | null>(null);
  const messageRequestId = useRef(0);
  const memoryController = useRef<AbortController | null>(null);
  const memoryRequestId = useRef(0);
  const targetController = useRef<AbortController | null>(null);
  const targetRequestId = useRef(0);

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQ(filters.q), 300);
    return () => window.clearTimeout(id);
  }, [filters.q]);

  useEffect(() => {
    setFilters(filtersForTarget(target));
    setOffsets({ source: 0, conversation: 0, message: 0 });
  }, [target]);

  const effectiveFilters = { ...filters, q: debouncedQ };

  const loadLists = useCallback(async () => {
    if (!active) return;
    listController.current?.abort();
    const controller = new AbortController();
    const requestId = ++listRequestId.current;
    listController.current = controller;
    setLoading(true);
    setError(null);

    try {
      const [sourceResponse, conversationResponse, messageResponse, statusResponse] = await Promise.all([
        api.get<PageResponse<SourceItem>>(`/api/memory/inspector/sources?${toQueryString(buildSourceQuery(effectiveFilters, offsets.source))}`, { signal: controller.signal }),
        api.get<PageResponse<ConversationItem>>(`/api/memory/inspector/conversations?${toQueryString(buildConversationQuery(effectiveFilters, selectedSource?.source_id ?? "", offsets.conversation))}`, { signal: controller.signal }),
        api.get<PageResponse<MessageItem>>(`/api/memory/inspector/messages?${toQueryString(buildMessageQuery(effectiveFilters, selectedSource?.source_id ?? "", selectedConversation?.conversation_id ?? "", offsets.message))}`, { signal: controller.signal }),
        api.get<InspectorStatusResponse>("/api/memory/inspector/status", { signal: controller.signal }),
      ]);
      if (requestId !== listRequestId.current) return;
      setSources(sourceResponse.items ?? []);
      setConversations(conversationResponse.items ?? []);
      setMessages(messageResponse.items ?? []);
      setStatus(mapStatus(statusResponse));
      setTotals({
        source: sourceResponse.pagination?.total ?? null,
        conversation: conversationResponse.pagination?.total ?? null,
        message: messageResponse.pagination?.total ?? null,
      });
    } catch (reason) {
      if (requestId === listRequestId.current && !(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) {
        setError(reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Unknown error"));
      }
    } finally {
      if (requestId === listRequestId.current) setLoading(false);
    }
  }, [active, api, debouncedQ, filters.fromTime, filters.privacy, filters.project, filters.role, filters.sourceType, filters.status, filters.toTime, offsets, selectedConversation?.conversation_id, selectedSource?.source_id]);

  useEffect(() => {
    void loadLists();
    return () => listController.current?.abort();
  }, [loadLists]);

  useEffect(() => {
    setOffsets({ source: 0, conversation: 0, message: 0 });
  }, [debouncedQ, filters.fromTime, filters.privacy, filters.project, filters.role, filters.sourceType, filters.status, filters.toTime]);

  const openMessage = async (row: MessageItem) => {
    messageController.current?.abort();
    const controller = new AbortController();
    const requestId = ++messageRequestId.current;
    messageController.current = controller;
    setSelectedMessage(row);
    setMemoryLinks([]);
    setSelectedMemory(null);
    setMemorySource(null);
    setMemoryVector(null);
    setDetailError(null);
    try {
      const response = await api.get<MessageDetailResponse>(`/api/memory/inspector/messages/${encodeURIComponent(row.message_id)}`, { signal: controller.signal });
      if (requestId !== messageRequestId.current) return;
      const mapped = mapMessageDetail(response);
      setSelectedMessage(mapped.item ?? row);
      setMemoryLinks(mapped.memoryLinks);
    } catch (reason) {
      if (requestId === messageRequestId.current && !(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) {
        setDetailError(reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Unknown error"));
      }
    }
  };

  const openMemory = async (link: MemoryLink) => {
    memoryController.current?.abort();
    const controller = new AbortController();
    const requestId = ++memoryRequestId.current;
    memoryController.current = controller;
    setDetailError(null);
    const memoryId = encodeURIComponent(link.memory_id);
    const results = await Promise.allSettled([
      api.get<MemoryDetailResponse>(`/api/memory/inspector/memories/${memoryId}`, { signal: controller.signal }),
      api.get<MemorySourceResponse>(`/api/memory/inspector/memories/${memoryId}/source`, { signal: controller.signal }),
      api.get<MemoryVectorResponse>(`/api/memory/inspector/memories/${memoryId}/vector`, { signal: controller.signal }),
    ]);
    if (requestId !== memoryRequestId.current) return;
    const [detail, source, vector] = results;
    if (detail.status === "fulfilled") setSelectedMemory(detail.value.item);
    if (source.status === "fulfilled") setMemorySource(mapMemorySource(source.value));
    if (vector.status === "fulfilled") setMemoryVector(mapMemoryVector(vector.value));
    const rejected = results.find((result) => result.status === "rejected");
    if (rejected?.status === "rejected" && !(rejected.reason instanceof ApiError && rejected.reason.code === "REQUEST_CANCELLED")) {
      setDetailError(rejected.reason instanceof ApiError ? rejected.reason : new ApiError(0, "UNKNOWN", "Unknown error"));
    }
  };

  useEffect(() => {
    if (!active || !target) return;
    targetController.current?.abort();
    const controller = new AbortController();
    const requestId = ++targetRequestId.current;
    targetController.current = controller;
    setDetailError(null);

    const loadTarget = async () => {
      try {
        if (target.source_id) {
          const response = await api.get<{ item: SourceItem }>(`/api/memory/inspector/sources/${encodeURIComponent(target.source_id)}`, { signal: controller.signal });
          if (requestId === targetRequestId.current) setSelectedSource(response.item);
        }
        if (target.conversation_id) {
          const response = await api.get<{ item: ConversationItem }>(`/api/memory/inspector/conversations/${encodeURIComponent(target.conversation_id)}`, { signal: controller.signal });
          if (requestId === targetRequestId.current) setSelectedConversation(response.item);
        }
        if (target.message_id) {
          const response = await api.get<MessageDetailResponse>(`/api/memory/inspector/messages/${encodeURIComponent(target.message_id)}`, { signal: controller.signal });
          if (requestId === targetRequestId.current) {
            const mapped = mapMessageDetail(response);
            setSelectedMessage(mapped.item);
            setMemoryLinks(mapped.memoryLinks);
          }
        }
        if (target.memory_id) {
          await openMemory({ memory_id: target.memory_id, relation_type: "shortcut" });
        }
      } catch (reason) {
        if (requestId === targetRequestId.current && !(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) {
          setDetailError(reason instanceof ApiError ? reason : new ApiError(0, "UNKNOWN", "Unknown error"));
        }
      }
    };

    void loadTarget();
    return () => controller.abort();
  }, [active, api, target]);

  if (!active) return <div className="inspector-state">连接本机服务后显示 Memory Inspector（记忆检查器）</div>;

  return (
    <div className="memory-inspector">
      <div className="inspector-status">
        {[
          ["Source", status?.sources],
          ["Conversation", status?.conversations],
          ["Message", status?.messages],
          ["Memory", status?.memories],
          ["Chunk", status?.chunks],
        ].map(([label, value]) => <div key={String(label)}><span>{label}</span><strong>{countLabel(value)}</strong></div>)}
        <div><span>Vector 覆盖</span><strong>{typeof status?.vectorCoverage === "number" ? `${(status.vectorCoverage * 100).toFixed(2)}%` : "未知"}</strong></div>
        <div><span>Vector 状态</span><strong>{text(status?.vectorState)}</strong></div>
        <div><span>重建状态</span><strong>{rebuildLabel(status?.rebuildRequired)}</strong></div>
        <div><span>最后更新</span><strong>{dateTime(status?.asOf)}</strong></div>
      </div>

      <div className="inspector-filters">
        <input placeholder="来源类型" value={filters.sourceType} onChange={(event) => setFilters({ ...filters, sourceType: event.target.value })} />
        <input placeholder="项目" value={filters.project} onChange={(event) => setFilters({ ...filters, project: event.target.value })} />
        <input placeholder="隐私" value={filters.privacy} onChange={(event) => setFilters({ ...filters, privacy: event.target.value })} />
        <input placeholder="状态" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })} />
        <input placeholder="角色" value={filters.role} onChange={(event) => setFilters({ ...filters, role: event.target.value })} />
        <input placeholder="关键词搜索" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
        <input type="datetime-local" value={filters.fromTime} onChange={(event) => setFilters({ ...filters, fromTime: event.target.value })} />
        <input type="datetime-local" value={filters.toTime} onChange={(event) => setFilters({ ...filters, toTime: event.target.value })} />
        <button className="button secondary" disabled={loading} onClick={() => void loadLists()}>{loading ? "读取中…" : "刷新"}</button>
      </div>

      {error && <StateView error={error} empty={false} />}

      <div className="inspector-columns">
        <section>
          <h2>Source 来源 <small>{countLabel(totals.source)}</small></h2>
          <StateView error={null} empty={!loading && sources.length === 0} filtered={Boolean(filters.sourceType || filters.project || filters.privacy || filters.status || debouncedQ)} />
          {sources.map((row) => (
            <button key={row.source_id} className={`inspector-item${privacyClass(row)} ${selectedSource?.source_id === row.source_id ? "active" : ""}`} onClick={() => { setSelectedSource(row); setSelectedConversation(null); setSelectedMessage(null); }}>
              <strong>{text(row.display_name)}</strong>
              <span>{text(row.source_type)} · {text(row.privacy)}</span>
              <span>项目 {formatList(row.projects)} · 状态 {text(row.status)}</span>
              <span>对话 {countLabel(row.conversation_count)} · 消息 {countLabel(row.message_count)}</span>
              <small>{dateTime(row.updated_at)}</small>
            </button>
          ))}
          <Pager offset={offsets.source} total={totals.source} onChange={(source) => setOffsets({ ...offsets, source })} />
        </section>

        <section>
          <h2>Conversation 对话 <small>{countLabel(totals.conversation)}</small></h2>
          <StateView error={null} empty={!loading && conversations.length === 0} filtered={Boolean(selectedSource || filters.project || filters.privacy || debouncedQ)} />
          {conversations.map((row) => (
            <button key={row.conversation_id} className={`inspector-item${privacyClass(row)} ${selectedConversation?.conversation_id === row.conversation_id ? "active" : ""}`} onClick={() => { setSelectedConversation(row); setSelectedMessage(null); }}>
              <strong>{text(row.title)}</strong>
              <span>参与者 {formatList(row.participants)}</span>
              <span>{dateTime(row.started_at)} → {dateTime(row.ended_at)}</span>
              <span>项目 {formatList(row.projects)} · 隐私 {text(row.privacy)}</span>
              <small>消息 {countLabel(row.message_count)}</small>
            </button>
          ))}
          <Pager offset={offsets.conversation} total={totals.conversation} onChange={(conversation) => setOffsets({ ...offsets, conversation })} />
        </section>

        <section>
          <h2>Message 消息 <small>{countLabel(totals.message)}</small></h2>
          <StateView error={null} empty={!loading && messages.length === 0} filtered={Boolean(selectedConversation || filters.role || debouncedQ)} />
          {messages.map((row) => {
            const restricted = isRestricted(row);
            return (
              <button key={row.message_id} className={`inspector-item${privacyClass(row)} ${selectedMessage?.message_id === row.message_id ? "active" : ""}`} onClick={() => void openMessage(row)}>
                <strong>{text(row.role)} · {text(row.author)}</strong>
                <span>{dateTime(row.occurred_at)}</span>
                <span>模型 {text(row.metadata?.model)} · 分支 {row.metadata?.is_branch === true ? "是" : row.metadata?.is_branch === false ? "否" : "未知"}</span>
                <small>{restricted ? "restricted 受限内容，点击查看" : text(row.content_preview)}</small>
              </button>
            );
          })}
          <Pager offset={offsets.message} total={totals.message} onChange={(message) => setOffsets({ ...offsets, message })} />
        </section>
      </div>

      {(selectedMessage || selectedMemory) && (
        <aside className="relation-panel">
          <header><div><h2>Message 详情与 Memory 关系</h2><span>{selectedMessage?.message_id ?? selectedMemory?.memory_id}</span></div><button onClick={() => { setSelectedMessage(null); setSelectedMemory(null); }}>关闭</button></header>
          {detailError && <div className="inspector-state error">详情读取失败，已保留当前可用数据</div>}
          {selectedMessage && <div className={`message-content${privacyClass(selectedMessage)}`}>
            {isRestricted(selectedMessage) ? <details><summary>restricted 受限内容，主动展开</summary><pre>{text(selectedMessage.content)}</pre></details> : <pre>{text(selectedMessage.content)}</pre>}
          </div>}
          {selectedMessage && <><h3>关联 Memory</h3>
          {memoryLinks.length ? memoryLinks.map((link) => (
            <button className="memory-link" key={`${link.memory_id}-${link.relation_type ?? "unknown"}`} onClick={() => void openMemory(link)}>
              <strong>{link.memory_id}</strong><span>关系 {text(link.relation_type)} · 置信度 {typeof link.confidence === "number" ? link.confidence.toFixed(3) : "未知"}</span>
            </button>
          )) : <p>当前 Message 没有关联 Memory。</p>}</>}

          {selectedMemory && (
            <div className="memory-detail">
              <h3>{text(selectedMemory.title)}</h3>
              <dl>
                <dt>Memory ID</dt><dd>{selectedMemory.memory_id}</dd>
                <dt>类型</dt><dd>{text(selectedMemory.memory_type)}</dd>
                <dt>状态</dt><dd>{text(selectedMemory.status)}</dd>
                <dt>Chunk 数量</dt><dd>{
                  typeof selectedMemory.chunk_count === "number"
                    ? selectedMemory.chunk_count.toLocaleString()
                    : Array.isArray(selectedMemory.chunks)
                      ? selectedMemory.chunks.length.toLocaleString()
                      : "未知"
                }</dd>
                <dt>Vector 状态</dt><dd>{text(memoryVector?.state)}</dd>
                <dt>rebuild_required</dt><dd>{rebuildLabel(memoryVector?.rebuild_required)}</dd>
                <dt>Vault 相对路径</dt><dd>{text(memorySource?.canonical?.relative_path)}</dd>
                <dt>Citations</dt><dd>{
                  Array.isArray(memorySource?.canonical?.citations) && memorySource.canonical.citations.length > 0
                    ? memorySource.canonical.citations.map((c: Citation) =>
                        `${c.chunk_id}${c.relative_path ? ` (${c.relative_path})` : ""}${c.start_line != null ? ` L${c.start_line}` : ""}${c.end_line != null ? `-${c.end_line}` : ""}`
                      ).join("; ")
                    : "无引用来源"
                }</dd>
              </dl>
              <h4>来源 Message Links</h4>
              {memorySource?.links?.length ? memorySource.links.map((link, index) => <p key={`${link.message_id ?? "unknown"}-${index}`}>{text(link.message_id)} · {text(link.relation_type)} · {text(link.citation)}</p>) : <p>未知或没有来源 Message Link。</p>}
              <h4>Vector Chunks</h4>
              <pre>{JSON.stringify(memoryVector?.chunks ?? [], null, 2)}</pre>
            </div>
          )}
        </aside>
      )}
    </div>
  );
}

function Pager({ offset, total, onChange }: { offset: number; total: number | null; onChange: (value: number) => void }) {
  return (
    <div className="inspector-pager">
      <button disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - INSPECTOR_LIMIT))}>上一页</button>
      <span>{Math.floor(offset / INSPECTOR_LIMIT) + 1} / {total === null ? "未知" : Math.max(1, Math.ceil(total / INSPECTOR_LIMIT))}</span>
      <button disabled={total !== null && offset + INSPECTOR_LIMIT >= total} onClick={() => onChange(offset + INSPECTOR_LIMIT)}>下一页</button>
    </div>
  );
}
