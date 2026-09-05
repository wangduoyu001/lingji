import { useCallback, useState } from "react";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";

type ConversationRow = {
  conversation_id: string;
  title?: string | null;
  started_at?: string | null;
  message_count?: number | null;
};
type MessageRow = {
  message_id: string;
  role?: string | null;
  author?: string | null;
  content?: string | null;
  content_preview?: string | null;
  occurred_at?: string | null;
};


function time(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

export default function MemoryLibraryPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState("");
  const [searchApplied, setSearchApplied] = useState("");
  const limit = 30;
  const load = useCallback(
    (signal: AbortSignal) =>
      api.get<{ items?: ConversationRow[]; pagination?: { total?: number | null; has_more?: boolean } }>(
        `/api/memory/inspector/conversations?limit=${limit}&offset=${offset}${searchApplied.trim() ? `&q=${encodeURIComponent(searchApplied.trim())}` : ""}`,
        { signal },
      ),
    [api, offset, searchApplied],
  );
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 20_000, staleAfterMs: 60_000 });
  const [openBody, setOpenBody] = useState<{ id: string; title: string; loading: boolean; messages: Array<{ role: string; author: string; content: string; time: string }> } | null>(null);

  const rows = (resource.data?.items as ConversationRow[] | undefined) ?? [];

  const openConversation = async (row: ConversationRow) => {
    const title = row.title ?? "会话";
    setOpenBody({ id: row.conversation_id, title, loading: true, messages: [] });
    try {
      const response = await api.get<{ items?: MessageRow[] }>(
        `/api/memory/inspector/messages?conversation_id=${encodeURIComponent(row.conversation_id)}&limit=200&offset=0`,
      );
      const messages = (response.items ?? []).map((m) => ({
        role: String(m.role ?? ""),
        author: String(m.author ?? ""),
        content: String(m.content ?? m.content_preview ?? ""),
        time: String(m.occurred_at ?? ""),
      }));
      setOpenBody({ id: row.conversation_id, title, loading: false, messages });
    } catch {
      setOpenBody({ id: row.conversation_id, title, loading: false, messages: [] });
    }
  };

  return (
    <div className="stack memory-library-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">记忆库</span>
          <h2>记忆库</h2>
          <p>灵机记住的每一段对话都在这里，点开就能看完整聊天原文。搜索框支持按内容查找。</p>
        </div>
        <span className="auto-refresh-note">{resource.refreshing ? "正在更新" : "自动更新"}</span>
      </section>
      {resource.error && !resource.data && <Notice kind="warning">暂时无法读取记忆库，灵机会自动重试。</Notice>}
      <div className="library-filters">
        <input
          className="library-search"
          placeholder="搜索对话内容…（回车执行）"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") { setSearchApplied(query); setOffset(0); }
          }}
        />
      </div>
      {resource.loading && !resource.data ? (
        <div className="empty-state" aria-busy="true">正在读取记忆库…</div>
      ) : rows.length === 0 ? (
        <Empty text="没有匹配的对话。换个搜索词试试，或等下一次自动检查。" />
      ) : (
        <>
          <div className="library-list">
            {rows.map((row) => (
              <article key={row.conversation_id} className="library-item">
                <button className="library-item-open" onClick={() => void openConversation(row)}>
                  <strong>{row.title ?? "未命名会话"}</strong>
                  <small>开始：{time(row.started_at)} · {row.message_count == null ? "消息数尚未获得" : `${row.message_count} 条消息`}</small>
                </button>
              </article>
            ))}
          </div>
          <div className="permanent-memory-pager">
            <button className="button secondary" disabled={offset === 0 || resource.refreshing} onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span>{offset + 1}–{offset + rows.length}{resource.data?.pagination?.total != null ? ` / 共 ${resource.data.pagination.total} 段对话` : ""}</span>
            <button className="button secondary" disabled={!resource.data?.pagination?.has_more || resource.refreshing} onClick={() => setOffset(offset + limit)}>下一页</button>
          </div>
        </>
      )}
      {openBody && (
        <div className="action-modal-backdrop" onClick={() => setOpenBody(null)}>
          <div className="action-modal permanent-memory-body" role="dialog" aria-label={openBody.title} onClick={(event) => event.stopPropagation()}>
            <h3>{openBody.title}</h3>
            {openBody.loading ? (
              <p aria-busy="true">正在读取聊天原文…</p>
            ) : openBody.messages.length === 0 ? (
              <p>这段会话还没有可显示的消息。</p>
            ) : (
              <div className="conversation-body">
                {openBody.messages.map((m, index) => (
                  <div key={`${m.role}-${index}`} className="conversation-msg">
                    <span className="pill neutral">{m.role === "user" ? "主人" : m.role === "assistant" ? "AI" : m.role || "尚未获得"}</span>
                    {m.time && <small>{m.time}</small>}
                    <p>{m.content}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="action-modal-actions">
              <button className="button secondary" onClick={() => setOpenBody(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
