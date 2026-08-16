import { useCallback, useEffect, useMemo, useState } from "react";
import type { LingJiApi } from "../api";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageId } from "../types";
import type { CodexCurrent } from "./codexWorkspaceTypes";
import type {
  InspectorStatusResponse,
  MemoryDetailResponse,
  MemoryItem,
  MemorySourceResponse,
  MemoryVectorResponse,
  PageResponse,
} from "./memoryInspectorTypes";

type Snapshot = {
  page: PageResponse<MemoryItem>;
  status: InspectorStatusResponse;
  current: CodexCurrent;
};

type MemoryEvidence = {
  detail: MemoryItem | null;
  source: MemorySourceResponse | null;
  vector: MemoryVectorResponse | null;
};

const PAGE_SIZE = 30;

function typeLabel(value: unknown): string {
  const key = String(value ?? "").toLowerCase();
  const labels: Record<string, string> = {
    decision: "决定",
    preference: "偏好",
    fact: "事实",
    plan: "计划",
    project: "项目",
    experience: "经验",
    core: "核心记忆",
  };
  return labels[key] ?? (key || "记忆");
}

function statusLabel(value: unknown): string {
  const key = String(value ?? "").toLowerCase();
  if (["active", "approved", "ready"].includes(key)) return "已生效";
  if (["pending", "candidate", "pending_review"].includes(key)) return "待确认";
  if (["archived", "inactive"].includes(key)) return "已归档";
  return key || "状态未知";
}

function safeRelativePath(value: unknown): string {
  const raw = String(value ?? "").replaceAll("\\", "/").trim();
  if (!raw || raw.startsWith("/") || raw.startsWith("~/") || /^[A-Za-z]:\//.test(raw)) return "来源路径未公开";
  return raw.split("/").filter((part) => part && part !== "." && part !== "..").join("/") || "来源路径未公开";
}

function chunkPreview(chunks: unknown[] | null | undefined): string {
  if (!Array.isArray(chunks)) return "";
  const text = chunks
    .map((chunk) => {
      if (typeof chunk === "string") return chunk;
      if (!chunk || typeof chunk !== "object" || Array.isArray(chunk)) return "";
      const row = chunk as Record<string, unknown>;
      for (const key of ["content", "text", "content_preview", "summary"]) {
        if (typeof row[key] === "string" && row[key]) return String(row[key]);
      }
      return "";
    })
    .filter(Boolean)
    .join("\n\n")
    .trim();
  return text.slice(0, 1800);
}

export default function MemoryHomePage({
  api,
  active,
  onNavigate,
}: {
  api: LingJiApi;
  active: boolean;
  onNavigate: (page: PageId) => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [memoryType, setMemoryType] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<MemoryItem | null>(null);
  const [evidence, setEvidence] = useState<MemoryEvidence>({ detail: null, source: null, vector: null });
  const [detailBusy, setDetailBusy] = useState(false);
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 280);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => setOffset(0), [debouncedQuery, memoryType]);

  const load = useCallback(async (signal: AbortSignal): Promise<Snapshot> => {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (memoryType) params.set("memory_type", memoryType);
    const [page, status, current] = await Promise.all([
      api.get<PageResponse<MemoryItem>>(`/api/memory/inspector/memories?${params}`, { signal }),
      api.get<InspectorStatusResponse>("/api/memory/inspector/status", { signal }),
      api.get<CodexCurrent>("/api/codex/current", { signal }),
    ]);
    return { page, status, current };
  }, [api, debouncedQuery, memoryType, offset]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 12_000,
    staleAfterMs: 36_000,
    pauseWhenHidden: true,
  });

  const items = resource.data?.page.items ?? [];
  const pagination = resource.data?.page.pagination;
  const status = resource.data?.status;
  const pendingReview = Number(resource.data?.current.pending_review_count ?? 0);
  const memoryCount = status?.memory?.documents ?? pagination?.total ?? null;
  const chunkCount = status?.memory?.chunks ?? null;
  const vectorState = String(status?.vector?.state ?? "unknown").toLowerCase();
  const vectorCoverage = typeof status?.vector?.coverage === "number" ? status.vector.coverage : null;
  const capabilityMessage = vectorState === "ready" || vectorState === "healthy"
    ? `语义检索可用${vectorCoverage !== null ? ` · 已覆盖 ${Math.round(vectorCoverage * (vectorCoverage <= 1 ? 100 : 1))}%` : ""}`
    : "语义检索状态未完全就绪；全文检索仍可作为基础取回能力";

  const visibleTypes = useMemo(() => {
    const set = new Set(items.map((item) => String(item.memory_type ?? "").trim()).filter(Boolean));
    return [...set].sort();
  }, [items]);

  async function openMemory(item: MemoryItem) {
    setSelected(item);
    setEvidence({ detail: null, source: null, vector: null });
    setDetailError("");
    setDetailBusy(true);
    const id = encodeURIComponent(item.memory_id);
    const results = await Promise.allSettled([
      api.get<MemoryDetailResponse>(`/api/memory/inspector/memories/${id}`),
      api.get<MemorySourceResponse>(`/api/memory/inspector/memories/${id}/source`),
      api.get<MemoryVectorResponse>(`/api/memory/inspector/memories/${id}/vector`),
    ]);
    const [detail, source, vector] = results;
    setEvidence({
      detail: detail.status === "fulfilled" ? detail.value.item : null,
      source: source.status === "fulfilled" ? source.value : null,
      vector: vector.status === "fulfilled" ? vector.value : null,
    });
    if (results.some((result) => result.status === "rejected")) {
      setDetailError("部分来源证据暂时读取失败。已显示能够验证的部分，不会补写猜测。");
    }
    setDetailBusy(false);
  }

  if (!active) return <Empty text="灵机核心连接后，这里会显示你的第二永久记忆大脑。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取永久记忆和来源证据…" />;
  if (resource.error && !resource.data) return <Notice kind="error">记忆暂时读取失败。灵机不会把未知状态显示成“没有记忆”。</Notice>;

  const selectedDetail = evidence.detail ?? selected;
  const preview = chunkPreview(selectedDetail?.chunks);
  const canonicalPath = safeRelativePath(evidence.source?.canonical?.relative_path);
  const citations = evidence.source?.canonical?.citations ?? [];
  const links = evidence.source?.links ?? [];
  const vector = evidence.vector?.vector;

  return (
    <div className="workbench-v4 memory-home-v4">
      <section className="v4-page-intro memory-intro">
        <div>
          <span className="v4-kicker">第二永久记忆大脑</span>
          <h2>灵机到底记住了什么</h2>
          <p>这里展示真正存在的长期记忆、来源证据和可取回状态。没有证据的内容不会被包装成“已经记住”。</p>
        </div>
        <div className="v4-intro-actions">
          <button className="v4-button primary" onClick={() => onNavigate("capture_center")}>添加资料</button>
          <button className="v4-button" disabled={pendingReview <= 0} onClick={() => onNavigate("memory_review")}>
            {pendingReview > 0 ? `${pendingReview} 条待确认` : "暂无待确认"}
          </button>
        </div>
      </section>

      {resource.error && resource.data && <Notice kind="warning">记忆状态更新暂时失败，正在显示最近一次可验证结果。</Notice>}

      <section className="memory-query-surface">
        <div className="memory-search-box">
          <span>⌕</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索已经记住的项目、决定、偏好或事实" />
        </div>
        <select value={memoryType} onChange={(event) => setMemoryType(event.target.value)} aria-label="记忆类型">
          <option value="">全部记忆</option>
          {visibleTypes.map((type) => <option value={type} key={type}>{typeLabel(type)}</option>)}
        </select>
      </section>

      <section className="memory-brief-strip">
        <div><span>永久记忆</span><strong>{memoryCount ?? "待确认"}</strong></div>
        <div><span>可取回片段</span><strong>{chunkCount ?? "待确认"}</strong></div>
        <div className="wide"><span>当前取回能力</span><strong>{capabilityMessage}</strong></div>
      </section>

      <section className="memory-browser-layout">
        <div className="memory-list-pane">
          <div className="v4-section-heading compact">
            <div><span className="v4-kicker">已存记忆</span><h3>{pagination?.total !== null && pagination?.total !== undefined ? `${pagination.total} 条可浏览` : "真实记忆列表"}</h3></div>
            <button className="v4-link" onClick={() => onNavigate("memory_inspector")}>查看完整来源链</button>
          </div>

          {items.length ? (
            <div className="memory-card-list">
              {items.map((item) => (
                <button
                  className={`memory-row-card ${selected?.memory_id === item.memory_id ? "active" : ""}`}
                  key={item.memory_id}
                  onClick={() => void openMemory(item)}
                >
                  <div className="memory-row-top"><strong>{item.title || item.memory_id}</strong><span>{typeLabel(item.memory_type)}</span></div>
                  <div className="memory-row-meta"><span>{statusLabel(item.status)}</span><span>{Number(item.chunk_count ?? item.chunks?.length ?? 0)} 个片段</span></div>
                </button>
              ))}
            </div>
          ) : (
            <div className="v4-empty-state">
              <strong>{debouncedQuery || memoryType ? "没有匹配的记忆" : "现在还没有可浏览的永久记忆"}</strong>
              <p>{debouncedQuery || memoryType ? "换一个关键词或清除筛选。" : "新资料会先进入处理和候选流程；只有真实写入后才会出现在这里。"}</p>
            </div>
          )}

          <div className="v4-pager">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>上一页</button>
            <span>第 {Math.floor(offset / PAGE_SIZE) + 1} 页</span>
            <button disabled={!pagination?.has_more} onClick={() => setOffset(offset + PAGE_SIZE)}>下一页</button>
          </div>
        </div>

        <aside className="memory-detail-pane">
          {selectedDetail ? (
            <>
              <div className="memory-detail-head">
                <span className="v4-kicker">记忆详情</span>
                <h3>{selectedDetail.title || selectedDetail.memory_id}</h3>
                <div className="memory-detail-tags"><span>{typeLabel(selectedDetail.memory_type)}</span><span>{statusLabel(selectedDetail.status)}</span></div>
              </div>
              {detailBusy && <p className="v4-muted">正在读取来源证据…</p>}
              {detailError && <Notice kind="warning">{detailError}</Notice>}

              <div className="memory-detail-section">
                <span>记住了什么</span>
                <p>{preview || "当前结构化读取结果没有提供可安全展示的正文片段；标题和来源仍可验证。"}</p>
              </div>

              <div className="memory-detail-section">
                <span>为什么能相信它</span>
                <div className="memory-evidence-grid">
                  <div><small>正式来源</small><strong>{canonicalPath}</strong></div>
                  <div><small>引用位置</small><strong>{citations.length ? `${citations.length} 处` : "暂无行级引用"}</strong></div>
                  <div><small>关联消息</small><strong>{links.length ? `${links.length} 条` : "暂无消息关联"}</strong></div>
                  <div><small>语义索引</small><strong>{String(vector?.state ?? "状态未知")}</strong></div>
                </div>
              </div>

              <div className="memory-detail-section">
                <span>来源证据</span>
                {citations.length ? (
                  <div className="memory-citation-list">
                    {citations.slice(0, 8).map((citation, index) => (
                      <div key={`${citation.chunk_id}-${index}`}><strong>{safeRelativePath(citation.relative_path)}</strong><small>{citation.start_line ? `第 ${citation.start_line}${citation.end_line ? `–${citation.end_line}` : ""} 行` : citation.chunk_id}</small></div>
                    ))}
                  </div>
                ) : <p>当前没有更细的行级引用。灵机不会用推测补齐来源。</p>}
              </div>
            </>
          ) : (
            <div className="memory-detail-empty">
              <span className="v4-kicker">选择一条记忆</span>
              <h3>查看它记住了什么，以及从哪里来的</h3>
              <p>右侧不会只显示一个“已记住”标签，而会尽量给出正文片段、正式来源、引用和索引状态。</p>
            </div>
          )}
        </aside>
      </section>

      <section className="memory-gap-surface">
        <div>
          <span className="v4-kicker">记忆缺口</span>
          <h3>{pendingReview > 0 ? `有 ${pendingReview} 条候选还没有成为永久记忆` : "当前没有可验证的记忆缺口结论"}</h3>
          <p>{pendingReview > 0 ? "这些是系统真实生成、仍需主人确认的候选。" : "缺口分析必须有你的真实数据证据。没有证据时，灵机不会拿通用模板猜“你可能忘了什么”。"}</p>
        </div>
        {pendingReview > 0 && <button className="v4-button" onClick={() => onNavigate("memory_review")}>查看真实候选</button>}
      </section>
    </div>
  );
}
