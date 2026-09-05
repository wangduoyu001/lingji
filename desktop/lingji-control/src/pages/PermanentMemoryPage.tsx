import { useCallback, useState } from "react";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import type { PageResponse } from "./memoryInspectorTypes";
import { usePollingResource } from "../hooks/usePollingResource";

type PermanentMemoryRow = {
  memory_id: string;
  title?: string | null;
  memory_type?: string | null;
  state?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  source?: { label?: string | null } | null;
};

function text(value: unknown, fallback = "尚未获得"): string {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function time(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

export default function PermanentMemoryPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const load = useCallback(
    (signal: AbortSignal) => api.get<PageResponse<PermanentMemoryRow>>(`/api/memory/inspector/memories?memory_type=permanent&limit=${limit}&offset=${offset}`, { signal }),
    [api, offset],
  );
  const resource = usePollingResource<PageResponse<PermanentMemoryRow>>({ fetcher: load, enabled: active, intervalMs: 20_000, staleAfterMs: 60_000 });
  const [openBody, setOpenBody] = useState<{ id: string; title: string; body: string; loading: boolean } | null>(null);

  const rows = resource.data?.items ?? [];
  const pagination = resource.data?.pagination;

  const openMemory = async (row: PermanentMemoryRow) => {
    setOpenBody({ id: row.memory_id, title: text(row.title, "永久记忆"), body: "", loading: true });
    try {
      const detail = await api.get<{ item?: { body?: string | null; conclusion?: string | null; content?: string | null } }>(`/api/memory/inspector/memories/${encodeURIComponent(row.memory_id)}`);
      const item = detail.item ?? {};
      const body = String(item.body ?? item.content ?? item.conclusion ?? "这条记忆还没有可显示的正文。");
      setOpenBody({ id: row.memory_id, title: text(row.title, "永久记忆"), body, loading: false });
    } catch {
      setOpenBody({ id: row.memory_id, title: text(row.title, "永久记忆"), body: "暂时无法读取这条记忆的正文，请稍后重试。", loading: false });
    }
  };

  return (
    <div className="stack permanent-memory-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">永久记忆</span>
          <h2>永久记忆</h2>
          <p>这里只显示你确认过的长期记忆，永久保存。在「灵机整理」里点「确认加入长期记忆」，记忆就会出现在这里。</p>
        </div>
        <span className="auto-refresh-note">{resource.refreshing ? "正在更新" : "自动更新"}</span>
      </section>
      {resource.error && !resource.data && <Notice kind="warning">暂时无法读取永久记忆，灵机会自动重试。</Notice>}
      {resource.loading && !resource.data ? (
        <div className="empty-state" aria-busy="true">正在读取永久记忆…</div>
      ) : rows.length === 0 ? (
        <Empty text="还没有永久记忆。在「灵机整理」里看到重要的记忆卡后，点「确认加入长期记忆」，它就会出现在这里。" />
      ) : (
        <>
          <div className="permanent-memory-list">
            {rows.map((row) => (
              <article key={row.memory_id} className="permanent-memory-item">
                <button className="permanent-memory-open" onClick={() => void openMemory(row)}>
                  <strong>{text(row.title, "未命名记忆")}</strong>
                  <small>来源：{text(row.source?.label)} · 保存时间：{time(row.updated_at || row.created_at)}</small>
                </button>
              </article>
            ))}
          </div>
          <div className="permanent-memory-pager">
            <button className="button secondary" disabled={offset === 0 || resource.refreshing} onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span>{offset + 1}–{offset + rows.length}{pagination?.total != null ? ` / 共 ${pagination.total} 条` : ""}</span>
            <button className="button secondary" disabled={!pagination?.has_more || resource.refreshing} onClick={() => setOffset(offset + limit)}>下一页</button>
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
