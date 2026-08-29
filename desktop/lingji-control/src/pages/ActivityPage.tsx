import { useCallback, useState } from "react";
import { Empty, Panel, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { WorkHistoryItem, WorkHistoryResponse } from "../contracts/workFact";

const shown = (value: unknown, fallback = "检查结果尚未获得"): string => value === null || value === undefined || value === "" ? fallback : String(value);
const time = (value: unknown): string => {
  if (!value) return "时间尚未获得";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间尚未获得" : date.toLocaleString();
};
const phaseLabel = (value: unknown, status: unknown): string => {
  if (value) return String(value);
  if (status === "failed") return "没有完成";
  if (status === "completed" || status === "success") return "已完成";
  return "正在处理";
};

function readableActivityName(value: unknown): string {
  const name = String(value ?? "");
  return /^扫描\s+obsidian$/i.test(name) || name.toLowerCase() === "obsidian"
    ? "Obsidian 长期记忆区"
    : name;
}

function readableNextActor(item: WorkHistoryItem): string {
  if (item.next_action?.actor === "system" || item.summary?.next_actor === "system") return "灵机会继续自动检查";
  return shown(item.summary?.next_actor, "暂时没有下一步");
}

const EMPTY_SCAN_SUMMARIES = [
  /^扫描完成，已检查\s*0\s*个来源文件（新增\s*0，复用\s*0）$/,
  /^扫描完成，已检查\s*0\s*个来源文件\s*\(新增\s*0，复用\s*0\)$/,
];

function normalizeActivityResult(item: WorkHistoryItem): string | null {
  const outcomeSummary = String(item.outcome?.summary ?? "").trim();
  if (outcomeSummary) {
    if (EMPTY_SCAN_SUMMARIES.some((pattern) => pattern.test(outcomeSummary))) return "检查完成，未发现新内容";
    return outcomeSummary;
  }
  const summaryResult = String(item.summary?.result ?? "").trim();
  return summaryResult || null;
}

function activitySourceIdentity(item: WorkHistoryItem): string | null {
  const summarySourceId = String(item.summary?.source_id ?? "").trim();
  if (summarySourceId) return `source:${summarySourceId}`;
  const workSourceId = String(item.work?.source_id ?? "").trim();
  return workSourceId ? `source:${workSourceId}` : null;
}

function isQuietSuccessfulScan(item: WorkHistoryItem): boolean {
  const status = item.outcome?.status || item.work?.status;
  const sourceId = activitySourceIdentity(item);
  const title = String(item.work?.title ?? "");
  const result = normalizeActivityResult(item);
  return (status === "completed" || status === "success")
    && Boolean(sourceId)
    && (/^扫描\s+obsidian$/i.test(title) || String(item.summary?.source ?? "").toLowerCase() === "obsidian")
    && result === "检查完成，未发现新内容"
    && !item.failure
    && !(item.pending_actions ?? []).length;
}

type ActivityItem = WorkHistoryItem & { display_result?: string };

function collapseQuietActivity(items: WorkHistoryItem[]): ActivityItem[] {
  const output: ActivityItem[] = [];
  let run: WorkHistoryItem[] = [];
  let runIdentity: string | null = null;
  const flush = () => {
    if (!run.length) return;
    const first = run[0];
    if (run.length >= 2) {
      output.push({
        ...first,
        display_result: `Obsidian 长期记忆区已自动检查，未发现新内容；近期已检查${run.length}次`,
      });
    } else {
      output.push(first);
    }
    run = [];
    runIdentity = null;
  };
  for (const item of items) {
    const quiet = isQuietSuccessfulScan(item);
    const identity = quiet ? activitySourceIdentity(item) : null;
    if (quiet && run.length && identity === runIdentity) {
      run.push(item);
      continue;
    }
    flush();
    if (quiet) {
      run = [item];
      runIdentity = identity;
    } else {
      output.push(item);
    }
  }
  flush();
  return output;
}

function WorkCard({ item }: { item: ActivityItem }) {
  const summary = item.summary ?? {};
  const status = item.outcome?.status || item.work?.status;
  const result = item.display_result || normalizeActivityResult(item) || (status === "failed" ? "失败" : status === "completed" || status === "success" ? "成功" : null);
  return <article className="activity-card">
    <div className="activity-card-heading"><div><span className={`timeline-marker ${status === "failed" ? "failed" : status === "completed" || status === "success" ? "completed" : ""}`} /><strong>{readableActivityName(item.work?.title || summary.source) || "一项灵机工作"}</strong></div><span className={`pill ${status === "failed" ? "failed" : status === "completed" || status === "success" ? "success" : "neutral"}`}>{phaseLabel(summary.phase, status)}</span></div>
    <p className="activity-card-result">结果：{shown(result || item.outcome?.summary)}</p>
    <div className="activity-card-meta"><span>时间：{time(summary.time || item.work?.updated_at || item.work?.created_at)}</span><span>来源：{readableActivityName(summary.source) || "来源尚未获得"}</span><span>下一步：{readableNextActor(item)}</span></div>
    <details className="activity-diagnostics"><summary>查看技术详情（执行事件）</summary><small>工作 ID：{shown(item.work?.work_id)} · 状态码：{shown(status)} · 来源 ID：{shown(summary.source_id || item.work?.source_id)}</small>{(item.events ?? []).length > 0 && <pre>{JSON.stringify(item.events ?? [], null, 2)}</pre>}</details>
  </article>;
}

export default function ActivityPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [offset, setOffset] = useState(0);
  const load = useCallback((signal: AbortSignal) => api.get<WorkHistoryResponse>(`/api/work/history?limit=20&offset=${offset}`, { signal }), [api, offset]);
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 5000, staleAfterMs: 15000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示活动记录。" />;
  if (resource.loading && !resource.data) return <Notice>正在读取活动记录…</Notice>;
  if (resource.error && !resource.data) return <Notice kind="error">活动读取失败：{resource.error.message}</Notice>;
  const items = collapseQuietActivity(resource.data?.items ?? []);
  return (
    <div className="stack observation-page activity-page">
      <Panel title="最近工作">
        <div className="activity-toolbar"><p>这里展示灵机最近实际完成、失败或仍在处理的工作。</p><button className="button secondary" disabled={resource.refreshing} onClick={() => void resource.refresh({ force: true })}>{resource.refreshing ? "检查中…" : "现在检查"}</button></div>
        {resource.stale && <Notice kind="warning">活动数据暂时过期，正在自动重试。</Notice>}
        {resource.error && <Notice kind="error">活动刷新失败：{resource.error.message}</Notice>}
        {items.length ? <div className="activity-card-list">{items.map((item) => <WorkCard key={item.work?.work_id ?? `${offset}-${item.summary?.time}`} item={item} />)}</div> : <Empty text="灵机还没有完成过可显示的工作。" />}
        <div className="loop-pager activity-pager"><button disabled={offset === 0 || resource.loading} onClick={() => setOffset(Math.max(0, offset - 20))}>上一页</button><span>第 {Math.floor(offset / 20) + 1} 页{resource.data?.total == null ? " · 总数尚未获得" : ` · 共 ${resource.data.total} 条`}</span><button disabled={!resource.data?.has_more || resource.loading} onClick={() => setOffset(offset + 20)}>下一页</button></div>
      </Panel>
    </div>
  );
}
