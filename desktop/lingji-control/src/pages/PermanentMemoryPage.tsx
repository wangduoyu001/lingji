import { useCallback, useState } from "react";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";

type MemoryRow = {
  memory_id: string;
  title?: string | null;
  memory_type?: string | null;
  updated_at?: string | null;
};

function time(value: unknown): string {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
}

export default function PermanentMemoryPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const load = useCallback(
    (signal: AbortSignal) =>
      api.get<{ items?: MemoryRow[]; pagination?: { total?: number | null; has_more?: boolean } }>(
        `/api/memory/inspector/memories?memory_type=structured_evidence&limit=${limit}&offset=${offset}`,
        { signal },
      ),
    [api, offset],
  );
  const resource = usePollingResource<{ items?: MemoryRow[]; pagination?: { total?: number | null; has_more?: boolean } }>({
    fetcher: load, enabled: active, intervalMs: 20_000, staleAfterMs: 60_000,
  });
  const [openBody, setOpenBody] = useState<{ id: string; title: string; body: string; loading: boolean } | null>(null);

  const rows = (resource.data?.items as MemoryRow[] | undefined) ?? [];

  const openMemory = async (row: MemoryRow) => {
    setOpenBody({ id: row.memory_id, title: row.title ?? "记忆内容", body: "", loading: true });
    try {
      const detail = await api.get<{ item?: { chunks?: Array<{ text?: string }>; conclusion?: string | null } }>(
        `/api/memory/inspector/memories/${encodeURIComponent(row.memory_id)}`,
      );
      const chunks = (detail.item?.chunks ?? []).map((c) => String(c.text ?? "")).filter(Boolean);
      const body = chunks.length ? chunks.join("\n\n") : String(detail.item?.conclusion ?? "这条记忆还没有可显示的正文。");
      setOpenBody({ id: row.memory_id, title: row.title ?? "记忆内容", body, loading: false });
    } catch {
      setOpenBody({ id: row.memory_id, title: row.title ?? "记忆内容", body: "暂时无法读取正文，请稍后重试。", loading: false });
    }
  };

  return (
    <div className="stack permanent-memory-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">永久记忆</span>
          <h2>永久记忆</h2>
          <p>灵机自动固化的精炼记忆。原文对话完整保存在“原始数据”里，这里只保留提炼后的结果。</p>
        </div>
        <span className="auto-refresh-note">{resource.refreshing ? "正在更新" : "自动更新"}</span>
      </section>
      {resource.error && !resource.data && <Notice kind="warning">暂时无法读取永久记忆，灵机会自动重试。</Notice>}
      {resource.loading && !resource.data ? (
        <div className="empty-state" aria-busy="true">正在读取永久记忆…</div>
      ) : rows.length === 0 ? (
        <Empty text="还没有固化的记忆。灵机完成提炼后会自动保存在这里。" />
      ) : (
        <>
          <div className="library-list">
            {rows.map((row) => (
              <article key={row.memory_id} className="library-item">
                <button className="library-item-open" onClick={() => void openMemory(row)}>
                  <span className="pill ok">自动固化</span>
                  <strong>{row.title ?? "未命名记忆"}</strong>
                  <small>固化时间：{time(row.updated_at)}</small>
                </button>
              </article>
            ))}
          </div>
          <div className="permanent-memory-pager">
            <button className="button secondary" disabled={offset === 0 || resource.refreshing} onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span>{offset + 1}–{offset + rows.length}{resource.data?.pagination?.total != null ? ` / 共 ${resource.data.pagination.total} 条` : ""}</span>
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
