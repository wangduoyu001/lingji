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
export type KnowledgeEntry = {
  conversation_id: string;
  title: string;
  summary: string;
  key_points: string[];
  category: string;
  model: string;
  revision: number;
  occurred_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};
export type KnowledgeStats = {
  total: number;
  ready: number;
  pending: number;
  by_category: Record<string, number>;
  model?: string | null;
  available: boolean;
};
export type KnowledgeProgress = {
  active: boolean;
  current?: { conversation_id: string; title: string; started_at: string } | null;
  model?: string | null;
  finished?: Array<{ title: string; seconds: number; ok: boolean; at: string }>;
  cumulative_distilled?: number;
  cumulative_failed?: number;
};
export type KnowledgeModel = { name: string; size_bytes: number; active: boolean };

function bytesLabel(value: number | undefined): string {
  if (!value || value <= 0) return "体积未知";
  const gb = value / 1024 ** 3;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${Math.round(value / 1024 ** 2)} MB`;
}

function elapsedLabel(startedAt: string | undefined): string {
  if (!startedAt) return "";
  const started = new Date(startedAt).getTime();
  if (Number.isNaN(started)) return "";
  const seconds = Math.max(0, Math.round((Date.now() - started) / 1000));
  if (seconds < 60) return `${seconds} 秒`;
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
}

function time(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

const CATEGORY_TONE: Record<string, string> = {
  项目: "ok",
  技术: "neutral",
  决策: "warning",
  问题: "bad",
  其他: "neutral",
};

export function KnowledgeSection({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [searchApplied, setSearchApplied] = useState("");
  const limit = 20;
  const resource = usePollingResource<{
    items: KnowledgeEntry[];
    pagination: { total: number; has_more: boolean };
    stats: KnowledgeStats;
    progress?: KnowledgeProgress;
    models?: KnowledgeModel[];
    distill_model?: string;
  }>({
    fetcher: useCallback(
      (signal: AbortSignal) =>
        api.get(
          `/api/observability/knowledge?limit=${limit}&offset=${offset}` +
            `${category ? `&category=${encodeURIComponent(category)}` : ""}` +
            `${searchApplied.trim() ? `&q=${encodeURIComponent(searchApplied.trim())}` : ""}`,
          { signal },
        ),
      [api, offset, category, searchApplied],
    ),
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 25_000,
  });
  const [switchingModel, setSwitchingModel] = useState(false);
  const stats = resource.data?.stats;
  const progress = resource.data?.progress;
  const models = resource.data?.models ?? [];
  const rows = resource.data?.items ?? [];

  const switchModel = async (name: string) => {
    setSwitchingModel(true);
    try {
      await api.post("/api/observability/knowledge/model", { model: name });
      await resource.refresh();
    } catch {
      // 切换失败保持原状，下一次刷新会显示当前生效模型。
    } finally {
      setSwitchingModel(false);
    }
  };

  const [detail, setDetail] = useState<{ entry: KnowledgeEntry | null; loading: boolean; messages: Array<{ role: string; content: string; time: string }> } | null>(null);

  const openDetail = async (entry: KnowledgeEntry) => {
    setDetail({ entry, loading: true, messages: [] });
    try {
      const response = await api.get<{ entry: KnowledgeEntry | null; messages?: MessageRow[] }>(
        `/api/observability/knowledge/${encodeURIComponent(entry.conversation_id)}`,
      );
      setDetail({
        entry: response.entry ?? entry,
        loading: false,
        messages: (response.messages ?? []).map((m) => ({
          role: String(m.role ?? ""),
          content: String(m.content ?? m.content_preview ?? ""),
          time: String(m.occurred_at ?? ""),
        })),
      });
    } catch {
      setDetail({ entry, loading: false, messages: [] });
    }
  };

  return (
    <section className="stack knowledge-section">
      <div className="knowledge-progress-board">
        <div className="knowledge-progress-main">
          <div className="knowledge-progress-status">
            {progress?.active ? (
              <>
                <span className="pill warning">模型正在提炼</span>
                <strong>{progress.current?.title || "未命名对话"}</strong>
                <small>已进行 {elapsedLabel(progress.current?.started_at) || "刚刚开始"}</small>
              </>
            ) : (
              <>
                <span className="pill ok">{progress?.finished?.length ? "模型空闲" : "等待任务"}</span>
                <strong>{progress?.finished?.length ? "刚完成一轮提炼，有新对话会自动继续" : "有新对话时会自动开始提炼"}</strong>
                <small>全程自动，无需操作</small>
              </>
            )}
          </div>
          <div className="knowledge-progress-bar">
            <div className="knowledge-progress-fill" style={{ width: stats && stats.total ? `${Math.round((stats.ready / stats.total) * 100)}%` : "0%" }} />
          </div>
          <small className="knowledge-progress-caption">
            {stats ? `进度 ${stats.ready} / ${stats.total} 段（${stats.total ? Math.round((stats.ready / stats.total) * 100) : 0}%）` : "进度尚未获得"}
            {progress?.cumulative_failed ? ` · 失败 ${progress.cumulative_failed} 段会自动重试` : ""}
          </small>
        </div>
        <div className="knowledge-progress-side">
          <div className="knowledge-model-row">
            <label htmlFor="knowledge-model-select">提炼模型</label>
            <select
              id="knowledge-model-select"
              className="knowledge-model-select"
              disabled={switchingModel || models.length === 0}
              value={resource.data?.distill_model || ""}
              onChange={(event) => void switchModel(event.target.value)}
            >
              <option value="">自动（优先最小模型）</option>
              {models.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name} · {bytesLabel(model.size_bytes)}
                </option>
              ))}
            </select>
            <small>{switchingModel ? "正在切换…" : models.length === 0 ? "未发现本机模型" : "下一轮提炼立即生效"}</small>
          </div>
          {(progress?.finished?.length ?? 0) > 0 && (
            <div className="knowledge-recent">
              <small>最近提炼</small>
              {progress!.finished!.slice().reverse().slice(0, 3).map((item, index) => (
                <div key={index} className="knowledge-recent-row">
                  <span className={`pill ${item.ok ? "ok" : "bad"}`}>{item.ok ? "完成" : "重试"}</span>
                  <small>{item.title}</small>
                  <small>{item.seconds < 60 ? `${Math.round(item.seconds)} 秒` : `${Math.floor(item.seconds / 60)} 分`}</small>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="knowledge-filters">
        <input
          className="library-search"
          placeholder="搜提炼要点：输入关键词…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") { setSearchApplied(query); setOffset(0); }
          }}
        />
        <div className="knowledge-category-row">
          <button className={`pill neutral${category === "" ? " active" : ""}`} onClick={() => { setCategory(""); setOffset(0); }}>全部</button>
          {Object.entries(stats?.by_category ?? {}).map(([name, count]) => (
            <button key={name} className={`pill neutral${category === name ? " active" : ""}`} onClick={() => { setCategory(category === name ? "" : name); setOffset(0); }}>
              {name} · {count}
            </button>
          ))}
        </div>
      </div>
      {resource.error && !resource.data && <Notice kind="warning">提炼要点正在自动准备，灵机会持续重试。</Notice>}
      {resource.loading && !resource.data ? (
        <div className="empty-state" aria-busy="true">正在读取提炼要点…</div>
      ) : rows.length === 0 ? (
        <Empty text={stats && stats.pending > 0 ? `还有 ${stats.pending} 段对话在排队提炼，本机模型正在自动推进。` : "还没有提炼要点。等第一段对话提炼完成后会出现在这里。"} />
      ) : (
        <>
          <div className="knowledge-list">
            {rows.map((entry) => (
              <article key={entry.conversation_id} className="knowledge-item">
                <button className="knowledge-item-open" onClick={() => void openDetail(entry)}>
                  <div className="knowledge-item-head">
                    <span className={`pill ${CATEGORY_TONE[entry.category] ?? "neutral"}`}>{entry.category}</span>
                    {entry.revision > 1 && <span className="pill warning">已更新 {entry.revision - 1} 次</span>}
                    <small>{time(entry.occurred_at ?? entry.created_at)}</small>
                  </div>
                  <strong>{entry.title}</strong>
                  <p>{entry.summary}</p>
                  {entry.key_points.length > 0 && (
                    <ul className="knowledge-points">
                      {entry.key_points.slice(0, 3).map((point, index) => <li key={index}>{point}</li>)}
                    </ul>
                  )}
                  <small className="knowledge-source-hint">点击查看要点详情与对话原文 →</small>
                </button>
              </article>
            ))}
          </div>
          <div className="permanent-memory-pager">
            <button className="button secondary" disabled={offset === 0 || resource.refreshing} onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span>{offset + 1}–{offset + rows.length}{resource.data?.pagination?.total != null ? ` / 共 ${resource.data.pagination.total} 条要点` : ""}</span>
            <button className="button secondary" disabled={!resource.data?.pagination?.has_more || resource.refreshing} onClick={() => setOffset(offset + limit)}>下一页</button>
          </div>
        </>
      )}
      {detail && (
        <div className="action-modal-backdrop" onClick={() => setDetail(null)}>
          <div className="action-modal permanent-memory-body" role="dialog" aria-label="要点详情" onClick={(event) => event.stopPropagation()}>
            <div className="knowledge-item-head">
              {detail.entry && <span className={`pill ${CATEGORY_TONE[detail.entry.category] ?? "neutral"}`}>{detail.entry.category}</span>}
              {detail.entry && detail.entry.revision > 1 && <span className="pill warning">已更新 {detail.entry.revision - 1} 次</span>}
              <small>提炼模型：{detail.entry?.model || "尚未获得"}</small>
            </div>
            <h3>{detail.entry?.title ?? "要点详情"}</h3>
            <p className="knowledge-summary-full">{detail.entry?.summary}</p>
            {detail.entry && detail.entry.key_points.length > 0 && (
              <ul className="knowledge-points">{detail.entry.key_points.map((point, index) => <li key={index}>{point}</li>)}</ul>
            )}
            <h4>来源对话原文</h4>
            {detail.loading ? (
              <p aria-busy="true">正在读取对话原文…</p>
            ) : detail.messages.length === 0 ? (
              <p>这段会话还没有可显示的消息。</p>
            ) : (
              <div className="conversation-body">
                {detail.messages.map((m, index) => (
                  <div key={`${m.role}-${index}`} className="conversation-msg">
                    <span className="pill neutral">{m.role === "user" ? "主人" : m.role === "assistant" ? "AI" : m.role || "尚未获得"}</span>
                    {m.time && <small>{m.time}</small>}
                    <p>{m.content}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="action-modal-actions">
              <button className="button secondary" onClick={() => setDetail(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default function MemoryLibraryPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [tab, setTab] = useState<"knowledge" | "raw">("knowledge");
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
  const resource = usePollingResource({ fetcher: load, enabled: active && tab === "raw", intervalMs: 20_000, staleAfterMs: 60_000 });
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
          <p>灵机自动把每段对话提炼成知识要点，也保留全部聊天原文，随时可以追溯。</p>
        </div>
        <span className="auto-refresh-note">自动更新</span>
      </section>
      <div className="library-tabs">
        <button className={`button ${tab === "knowledge" ? "primary" : "secondary"}`} onClick={() => setTab("knowledge")}>知识要点</button>
        <button className={`button ${tab === "raw" ? "primary" : "secondary"}`} onClick={() => setTab("raw")}>对话原文</button>
      </div>
      {tab === "knowledge" ? (
        <KnowledgeSection api={api} active={active} />
      ) : (
        <>
          <div className="library-filters">
            <input
              className="library-search"
              placeholder="搜你的记忆：输入关键词或一句话…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") { setSearchApplied(query); setOffset(0); }
              }}
            />
          </div>
          {resource.error && !resource.data && <Notice kind="warning">暂时无法读取记忆库，灵机会自动重试。</Notice>}
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
        </>
      )}
    </div>
  );
}
