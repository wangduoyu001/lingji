import { useCallback, useState } from "react";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";

type MemoryRow = {
  memory_id: string;
  title?: string | null;
  memory_type?: string | null;
  memory_tier?: string | null;
  status?: string | null;
  tags?: unknown;
  valid_from?: string | null;
  updated_at?: string | null;
  relative_path?: string | null;
};

const TYPE_LABELS: Record<string, string> = {
  structured_evidence: "自动提炼",
  note: "笔记",
  core: "核心记忆",
  permanent: "永久记忆",
};

const TYPE_PLAIN: Record<string, string> = {
  structured_evidence: "灵机从你的记录里自动整理出的内容",
  note: "普通笔记内容",
  core: "核心记忆",
  permanent: "主人确认过的长期记忆",
};

function time(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

function categoryOf(row: MemoryRow): string {
  const t = String(row.memory_type ?? "");
  return TYPE_LABELS[t] ?? "未分类";
}

export default function MemoryLibraryPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const [category, setCategory] = useState<string>("全部");
  const [query, setQuery] = useState("");
  const limit = 30;
  const load = useCallback(
    (signal: AbortSignal) =>
      api.get<unknown>(
        `/api/memory/inspector/memories?limit=${limit}&offset=${offset}${query.trim() ? `&q=${encodeURIComponent(query.trim())}` : ""}`,
        { signal },
      ),
    [api, offset, query],
  );
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 20_000, staleAfterMs: 60_000 });
  const [openBody, setOpenBody] = useState<{ id: string; title: string; body: string; loading: boolean } | null>(null);

  const allRows = (resource.data?.items as MemoryRow[] | undefined) ?? [];
  const rows = category === "全部" ? allRows : allRows.filter((row) => categoryOf(row) === category);
  const categories = Array.from(new Set(allRows.map(categoryOf)));

  const openMemory = async (row: MemoryRow) => {
    setOpenBody({ id: row.memory_id, title: row.title ?? "记忆内容", body: "", loading: true });
    try {
      const detail = await api.get<{ item?: { body?: string | null; content?: string | null; conclusion?: string | null } }>(
        `/api/memory/inspector/memories/${encodeURIComponent(row.memory_id)}`,
      );
      const item = detail.item ?? {};
      const body = String(item.body ?? item.content ?? item.conclusion ?? "这条记忆还没有可显示的正文。");
      setOpenBody({ id: row.memory_id, title: row.title ?? "记忆内容", body, loading: false });
    } catch {
      setOpenBody({ id: row.memory_id, title: row.title ?? "记忆内容", body: "暂时无法读取正文，请稍后重试。", loading: false });
    }
  };

  return (
    <div className="stack memory-library-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">记忆库</span>
          <h2>记忆库</h2>
          <p>灵机记住的全部内容都在这里：自动提炼的对话记录、主人确认过的长期记忆。每条都可以打开看原文。</p>
        </div>
        <span className="auto-refresh-note">{resource.refreshing ? "正在更新" : "自动更新"}</span>
      </section>
      {resource.error && !resource.data && <Notice kind="warning">暂时无法读取记忆库，灵机会自动重试。</Notice>}
      <div className="library-filters">
        <input
          className="library-search"
          placeholder="搜索记忆…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") setOffset(0);
          }}
        />
        <div className="library-categories">
          {["全部", ...categories].map((label) => (
            <button key={label} className={`pill ${category === label ? "ok" : "neutral"}`} onClick={() => { setCategory(label); setOffset(0); }}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {resource.loading && !resource.data ? (
        <div className="empty-state" aria-busy="true">正在读取记忆库…</div>
      ) : rows.length === 0 ? (
        <Empty text="没有匹配的记忆。换个搜索词或分类试试。" />
      ) : (
        <>
          <div className="library-list">
            {rows.map((row) => (
              <article key={row.memory_id} className="library-item">
                <button className="library-item-open" onClick={() => void openMemory(row)}>
                  <span className="pill neutral">{categoryOf(row)}</span>
                  <strong>{row.title ?? "未命名记忆"}</strong>
                  <small>更新：{time(row.updated_at)}</small>
                  <small className="library-item-plain">{TYPE_PLAIN[String(row.memory_type)] ?? "记忆内容"}</small>
                </button>
              </article>
            ))}
          </div>
          <div className="permanent-memory-pager">
            <button className="button secondary" disabled={offset === 0 || resource.refreshing} onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span>{offset + 1}–{offset + rows.length}</span>
            <button className="button secondary" disabled={!resource.data?.pagination?.has_more || resource.refreshing} onClick={() => setOffset(offset + limit)}>下一页</button>
          </div>
        </>
      )}
      {openBody && (
        <div className="action-modal-backdrop" onClick={() => setOpenBody(null)}>
          <div className="action-modal permanent-memory-body" role="dialog" aria-label={openBody.title} onClick={(event) => event.stopPropagation()}>
            <h3>{openBody.title}</h3>
            {openBody.loading ? (
              <p aria-busy="true">正在读取正文…</p>
            ) : (
              <pre className="permanent-memory-text">{openBody.body}</pre>
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
