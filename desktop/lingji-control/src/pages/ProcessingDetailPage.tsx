import { useCallback, useState } from "react";
import { Empty } from "../components/ui";
import type { LingJiApi } from "../api";
import { usePollingResource } from "../hooks/usePollingResource";

type PipelineBlock = { key: string; label: string; plain: string; count: number | null };
type PipelineData = {
  pipeline: PipelineBlock[];
  failed_detail: Array<{ name: string; time?: string | null; what?: string; next?: string }>;
  reused_detail: Array<{ name: string; time?: string | null }>;
  latest_scans: Array<{ scan_id: string; status: string; total: number | null; queued: number | null; reused: number | null; completed: number | null; failed: number | null; updated_at: string | null }>;
  timeline: Array<{ time?: string | null; action: string; object: string }>;
};

const BLOCK_TITLES: Record<string, string> = {
  fetch: "原始获取",
  parse: "解析成功",
  dedupe: "去重复用",
  filter_failed: "筛选拒绝",
  extract: "提炼消息",
  memory: "记忆层更新",
  vectorize: "向量化",
};

export default function ProcessingDetailPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback((signal: AbortSignal) => api.get<PipelineData>("/api/observability/pipeline", { signal }).catch(() => null), [api]);
  const resource = usePollingResource<PipelineData | null>({ fetcher: load, enabled: active, intervalMs: 10_000, staleAfterMs: 30_000 });
  const [openBlock, setOpenBlock] = useState<string | null>(null);
  const data = resource.data;
  if (!active) return <Empty text="连接灵机后显示处理详情。" />;
  if (resource.loading && !data) return <div className="empty-state" aria-busy="true">正在读取处理详情…</div>;
  if (!data) return <Empty text="处理详情暂时读不出来，灵机会自动重试。" />;

  const detailFor = (key: string) => {
    if (key === "filter_failed") return data.failed_detail;
    if (key === "dedupe") return data.reused_detail;
    return null;
  };

  return (
    <div className="stack processing-detail-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">处理详情</span>
          <h2>处理详情</h2>
          <p>扫描 → 提炼 → 候选 → 记忆 → 时间线 → 向量 → RAG：每个环节的全部数据，直接平铺展示。</p>
        </div>
        <span className="auto-refresh-note">{resource.refreshing ? "正在更新" : "自动更新"}</span>
      </section>

      <div className="pipeline-grid">
        {data.pipeline.map((block) => (
          <article key={block.key} className="pipeline-block">
            <header>
              <strong>{block.label}</strong>
              <span className="pipeline-count">{block.count == null ? "尚未获得" : block.count}</span>
            </header>
            <p>{block.plain}</p>
            {(() => {
              const detail = detailFor(block.key);
              if (!detail || detail.length === 0) return null;
              const open = openBlock === block.key;
              return (
                <div className="pipeline-block-detail">
                  <button className="button secondary" onClick={() => setOpenBlock(open ? null : block.key)}>
                    {open ? "收起明细" : `查看明细（${detail.length}）`}
                  </button>
                  {open && (
                    <div className="pipeline-detail-list">
                      {detail.map((row, index) => (
                        <div key={`${row.name}-${index}`} className="pipeline-detail-row">
                          <strong>{row.name}</strong>
                          {row.time && <small>{row.time}</small>}
                          {"what" in row && <small>原因：{row.what}</small>}
                          {"next" in row && <small>接下来：{row.next}</small>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })()}
          </article>
        ))}
        <article className="pipeline-block">
          <header><strong>RAG 检索（AI 内部）</strong><span className="pill neutral">给 AI 用</span></header>
          <p>记忆的检索管线：向量索引 + 关键词索引，供 AI 回答时引用。主人界面不展示内部细节，出现异常时会在服务状态里提示。</p>
        </article>
      </div>

      <section className="pipeline-scans">
        <h3>最近的检查任务</h3>
        <div className="pipeline-scans-list">
          {data.latest_scans.map((scan) => (
            <div key={scan.scan_id} className="change-row">
              <small>{scan.updated_at ?? "时间尚未获得"}</small>
              <span className={`pill ${scan.status === "completed" ? "ok" : scan.status === "failed" ? "bad" : "warning"}`}>{scan.status === "completed" ? "已完成" : scan.status === "running" ? "进行中" : scan.status === "failed" ? "未完成" : scan.status}</span>
              <span>检查 {scan.total == null ? "尚未获得" : scan.total} 个</span>
              <span>新 {scan.queued == null ? "尚未获得" : scan.queued} · 复用 {scan.reused == null ? "尚未获得" : scan.reused}</span>
              {scan.failed != null && scan.failed > 0 && <span className="pill bad">拒绝 {scan.failed}</span>}
            </div>
          ))}
        </div>
      </section>

      <section className="pipeline-timeline">
        <h3>时间线事件</h3>
        <div className="changes-list">
          {data.timeline.map((event, index) => (
            <div key={`${event.time}-${index}`} className="change-row">
              <small className="change-time">{event.time ?? "时间尚未获得"}</small>
              <span className="pill neutral">{event.action}</span>
              <small>对象：{event.object}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
