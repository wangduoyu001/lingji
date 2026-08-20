import { useCallback, useMemo } from "react";
import type { LingJiApi } from "../api";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import { buildOwnerWorkFeed, type OwnerWorkItem } from "../ownerWorkFeed";
import {
  buildOwnerAttentionItems,
  hasReviewConsistencyIssue,
  ownerAttentionSummary,
  ownerSourcesUnknown,
} from "../ownerWorkbenchModel";
import type { PageId, Row } from "../types";
import type { CaptureJobsResponse } from "./captureCenterTypes";
import type { CodexCurrent } from "./codexWorkspaceTypes";

type ReviewCandidate = {
  memory_id: string;
  title?: string | null;
  content_preview?: string | null;
  proposal_reason?: string | null;
};

type ReviewResponse = {
  items?: ReviewCandidate[];
  pagination?: { total?: number | null };
};

type ImportCandidate = {
  candidate_id: string;
  display_name?: string | null;
  size_bytes?: number | null;
};

type AssistantSource = {
  id: string;
  label: string;
  candidates?: ImportCandidate[];
};

type AssistantRecord = {
  id: string;
  label: string;
  detection_state: string;
  candidate_count?: number;
  latest_activity_at?: string | null;
  message?: string;
};

type AssistantHub = {
  assistants?: AssistantRecord[];
  import_plan?: { sources?: AssistantSource[] };
};

type HomeSnapshot = {
  autopilot: Row | null;
  memories: Row | null;
  assistants: AssistantHub | null;
  current: CodexCurrent | null;
  reviews: ReviewResponse | null;
  work: CaptureJobsResponse | null;
};

const numberOrNull = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;
const asRecord = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

function relativeTime(value: unknown): string {
  const timestamp = Date.parse(String(value ?? ""));
  if (!Number.isFinite(timestamp)) return "时间待确认";
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return "刚刚";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  return hours < 24 ? `${hours} 小时前` : `${Math.round(hours / 24)} 天前`;
}

function settledValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

function workTone(item: OwnerWorkItem): string {
  if (item.ownerActionRequired) return "owner";
  if (item.stage === "issue") return "issue";
  if (["queued", "leased", "running", "retrying"].includes(item.status.toLowerCase())) return "active";
  return "done";
}

function safeMemoryTitle(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "记忆";
  const row = value as Record<string, unknown>;
  return String(row.title ?? row.memory_id ?? "记忆").slice(0, 160);
}

function nextActorLabel(value: string | null | undefined): string {
  if (value === "system") return "灵机";
  if (value === "owner") return "你";
  if (value === "external") return "外部系统";
  return "无待执行者";
}

export default function OverviewPage({ data, api, active, onNavigate, onOpenReview }: {
  data: Row | null;
  api: LingJiApi;
  active: boolean;
  onNavigate: (page: PageId) => void;
  onOpenReview: (memoryId: string) => void;
}) {
  const load = useCallback(async (signal: AbortSignal): Promise<HomeSnapshot> => {
    const results = await Promise.allSettled([
      api.get<Row>("/api/autopilot/status", { signal }),
      api.get<Row>("/api/memory/inspector/memories?limit=24&offset=0", { signal }),
      api.get<AssistantHub>("/api/assistant-hub/status", { signal }),
      api.get<CodexCurrent>("/api/codex/current", { signal }),
      api.get<ReviewResponse>("/api/memory/review/candidates?limit=8&offset=0", { signal }),
      api.get<CaptureJobsResponse>("/api/capture/jobs?limit=24&offset=0", { signal }),
    ]);
    return {
      autopilot: settledValue(results[0]),
      memories: settledValue(results[1]),
      assistants: settledValue(results[2]),
      current: settledValue(results[3]),
      reviews: settledValue(results[4]),
      work: settledValue(results[5]),
    };
  }, [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 24_000,
    pauseWhenHidden: true,
  });

  if (!data) return <Empty text="灵机核心连接后，会读取真实工作对象和主人边界状态。" />;

  const d = data as Record<string, unknown>;
  const progress = asRecord(d.memory_progress);
  const intake = asRecord(progress.intake);
  const memoryRuntime = asRecord(d.memory_runtime);
  const vector = asRecord(memoryRuntime.vector ?? d.vector_status);
  const expectedDocuments = numberOrNull(intake.documents);
  const memories = resource.data?.memories ?? null;
  const feed = buildOwnerWorkFeed({ jobsResponse: resource.data?.work ?? null, expectedDocuments, limit: 24 });

  const reviewItems = resource.data?.reviews?.items ?? [];
  const assistantSources = resource.data?.assistants?.import_plan?.sources ?? [];
  const detectedAssistants = resource.data?.assistants?.assistants?.filter((assistant) => assistant.detection_state === "detected") ?? [];
  const pendingReviewCount = Number(resource.data?.current?.pending_review_count ?? 0);
  const reviewsLoaded = resource.data?.reviews !== null;
  const assistantsLoaded = resource.data?.assistants !== null;
  const reviewMismatch = hasReviewConsistencyIssue({ pendingReviewCount, reviewsLoaded, reviewItems });
  const unknownOwnerState = ownerSourcesUnknown({ reviewsLoaded, assistantsLoaded });

  const decisions = useMemo(
    () => buildOwnerAttentionItems({
      reviewItems,
      importSources: assistantSources,
      vectorRebuildRequired: vector.rebuild_required === true,
    }),
    [assistantSources, reviewItems, vector.rebuild_required],
  );

  const activeItems = feed.items.filter((item) => ["queued", "leased", "running", "retrying"].includes(item.status.toLowerCase()));
  const recentOutcome = feed.recentActivity.slice(0, 4);
  const recentMemories = Array.isArray((memories as Record<string, unknown> | null)?.items)
    ? ((memories as Record<string, unknown>).items as unknown[]).slice(0, 4)
    : [];
  const nextItem = activeItems[0] ?? feed.items[0] ?? null;
  const attention = ownerAttentionSummary({ items: decisions, sourceUnknown: unknownOwnerState, activeWorkCount: activeItems.length });

  return (
    <div className="workbench-v4 home-v4">
      <section className={`v4-brief-hero ${attention.state === "owner" ? "needs-owner" : attention.state === "unknown" ? "unknown" : "clear"}`}>
        <div className="v4-brief-copy">
          <span className="v4-kicker">现在需要你吗</span>
          <h2>{attention.title}</h2>
          <p>{attention.detail}</p>
        </div>
        <div className="v4-brief-state">
          <span className={`v4-state-orb ${attention.state === "owner" ? "warning" : attention.state === "unknown" ? "unknown" : "ok"}`} />
          <div><strong>{attention.state === "owner" ? "等待主人" : attention.state === "unknown" ? "确认中" : "没有主人待办"}</strong><small>{resource.refreshing ? "正在同步最新事实" : "后台自动更新"}</small></div>
        </div>
      </section>

      {reviewMismatch && <Notice kind="warning">系统汇总报告有待确认记忆，但当前没有读到对应候选对象。灵机不会生成会打开空页面的动作。</Notice>}
      {feed.detailsState === "unavailable" && <Notice kind="warning">{feed.detailsMessage}</Notice>}

      {decisions.length > 0 && (
        <section className="v4-owner-inbox">
          <div className="v4-section-heading"><div><span className="v4-kicker">需要我</span><h3>只有真实 PendingAction 对象</h3></div><button className="v4-link" onClick={() => onNavigate("attention")}>查看全部</button></div>
          <div className="v4-decision-list">
            {decisions.map((decision) => (
              <button
                className="v4-decision-row"
                key={decision.id}
                onClick={() => decision.kind === "memory" ? onOpenReview(decision.memoryId) : onNavigate(decision.target)}
              >
                <span><strong>{decision.title}</strong><small>{decision.detail}</small></span><b>处理</b>
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="v4-home-grid">
        <article className="v4-surface v4-outcomes">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">刚刚替你做了什么</span><h3>有 WorkItem 才显示结果</h3></div><button className="v4-link" onClick={() => onNavigate("activity")}>工作履历</button></div>
          {recentOutcome.length ? (
            <div className="v4-timeline">
              {recentOutcome.map((event) => (
                <div className={`v4-timeline-row ${event.tone}`} key={event.id}>
                  <span className="v4-timeline-dot" />
                  <div><strong>{event.title}</strong><small>{event.detail}</small></div>
                  <time>{relativeTime(event.occurredAt)}</time>
                </div>
              ))}
            </div>
          ) : (
            <div className="v4-empty-state compact"><strong>最近没有新的 WorkItem 结果</strong><p>静态扫描说明、统计数字和孤立事件不会冒充“灵机刚做了什么”。</p></div>
          )}
        </article>

        <article className="v4-surface v4-now">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">现在正在做什么</span><h3>{activeItems.length ? `${activeItems.length} 项真实工作` : "当前没有运行中的 WorkItem"}</h3></div></div>
          {activeItems.length ? (
            <div className="v4-work-stack">
              {activeItems.slice(0, 3).map((item) => (
                <button className="v4-work-row" key={item.id} onClick={() => onNavigate("activity")}>
                  <span className={`v4-work-state ${workTone(item)}`}>{item.stageLabel}</span>
                  <div><strong>{item.title}</strong><small>{item.done}</small></div>
                </button>
              ))}
            </div>
          ) : (
            <div className="v4-empty-state compact"><strong>没有已记录的前台工作</strong><p>发现来源本身不等于已经接管或执行。只有创建 WorkItem 后才会显示在这里。</p></div>
          )}
        </article>
      </section>

      <section className="v4-surface v4-next-surface">
        <div className="v4-section-heading"><div><span className="v4-kicker">下一步</span><h3>{nextItem ? nextItem.nextStep : "当前没有 WorkItem 后续动作"}</h3></div><span className="v4-next-actor">下一执行者：{nextActorLabel(nextItem?.nextActor)}</span></div>
        <p>{nextItem ? `${nextItem.title} · 当前事实：${nextItem.done}` : "系统没有可证明的后续工作时，不会用“继续自动处理”之类文案制造活动感。"}</p>
      </section>

      <section className="v4-home-grid secondary">
        <article className="v4-surface">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">记忆发生了什么变化</span><h3>真实记忆对象</h3></div><button className="v4-link" onClick={() => onNavigate("memory")}>打开记忆</button></div>
          {recentMemories.length ? (
            <div className="v4-memory-mini-list">
              {recentMemories.map((item, index) => <button key={index} onClick={() => onNavigate("memory")}><strong>{safeMemoryTitle(item)}</strong><small>查看真实内容和来源证据</small></button>)}
            </div>
          ) : <div className="v4-empty-state compact"><strong>还没有可展示的永久记忆变化</strong><p>资料数量不等于永久记忆。只有真实记忆对象才会出现在这里。</p></div>}
        </article>

        <article className="v4-surface">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">主动发现</span><h3>{detectedAssistants.length ? `已发现 ${detectedAssistants.length} 个支持来源` : "继续检查已支持环境"}</h3></div></div>
          {detectedAssistants.length ? (
            <div className="v4-discovery-list">
              {detectedAssistants.slice(0, 5).map((assistant) => (
                <div key={assistant.id}><span className="v4-discovery-dot" /><div><strong>{assistant.label}</strong><small>{assistant.message || `只确认到 ${Number(assistant.candidate_count ?? 0).toLocaleString()} 条可用元数据；发现不等于已授权、已接管或已执行`}</small></div></div>
              ))}
            </div>
          ) : <div className="v4-empty-state compact"><strong>暂未发现新的支持来源</strong><p>没有发现时不创建虚假工作。</p></div>}
          {assistantSources.some((source) => (source.candidates?.length ?? 0) > 0) && <button className="v4-inline-alert" onClick={() => onNavigate("attention")}>发现资料需要正文读取授权</button>}
        </article>
      </section>

      <details className="v4-advanced-summary">
        <summary>高级状态与系统统计</summary>
        <div>
          <span>资料统计：{expectedDocuments ?? "待确认"}</span>
          <span>自动维护：{String(resource.data?.autopilot?.state ?? "状态待确认")}</span>
          <span>向量：{String(vector.state ?? "状态待确认")}</span>
        </div>
      </details>
    </div>
  );
}
