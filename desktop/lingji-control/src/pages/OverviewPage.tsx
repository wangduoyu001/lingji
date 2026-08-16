import { useCallback, useMemo } from "react";
import type { LingJiApi } from "../api";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import { buildOwnerWorkFeed, type OwnerWorkItem } from "../ownerWorkFeed";
import type { PageId, Row } from "../types";
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
};

type OwnerDecision = {
  id: string;
  title: string;
  detail: string;
  target: PageId;
  memoryId?: string;
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
    ]);
    return {
      autopilot: settledValue(results[0]),
      memories: settledValue(results[1]),
      assistants: settledValue(results[2]),
      current: settledValue(results[3]),
      reviews: settledValue(results[4]),
    };
  }, [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 24_000,
    pauseWhenHidden: true,
  });

  if (!data) return <Empty text="灵机核心连接后，会先自动扫描已授权环境，再告诉你发生了什么。" />;

  const d = data as Record<string, unknown>;
  const queueRoot = asRecord(d.queue);
  const progress = asRecord(d.memory_progress);
  const intake = asRecord(progress.intake);
  const memoryRuntime = asRecord(d.memory_runtime);
  const vector = asRecord(memoryRuntime.vector ?? d.vector_status);
  const events = Array.isArray(d.events) ? d.events : [];
  const expectedDocuments = numberOrNull(intake.documents);
  const memories = resource.data?.memories ?? null;
  const feed = buildOwnerWorkFeed({ memoryResponse: memories, queueResponse: queueRoot, events, expectedDocuments, limit: 24 });

  const reviewItems = resource.data?.reviews?.items ?? [];
  const assistantSources = resource.data?.assistants?.import_plan?.sources ?? [];
  const importCandidates = assistantSources.flatMap((source) => (source.candidates ?? []).map((candidate) => ({ source, candidate })));
  const detectedAssistants = resource.data?.assistants?.assistants?.filter((assistant) => assistant.detection_state === "detected") ?? [];
  const pendingReviewCount = Number(resource.data?.current?.pending_review_count ?? 0);
  const reviewMismatch = pendingReviewCount > 0 && resource.data?.reviews !== null && reviewItems.length === 0;

  const decisions = useMemo<OwnerDecision[]>(() => {
    const result: OwnerDecision[] = [];
    for (const candidate of reviewItems.slice(0, 3)) {
      result.push({
        id: `memory:${candidate.memory_id}`,
        title: candidate.title || "一条候选记忆等待确认",
        detail: candidate.proposal_reason || candidate.content_preview || "这条内容只有确认后才会进入永久记忆。",
        target: "memory_review",
        memoryId: candidate.memory_id,
      });
    }
    for (const item of importCandidates.slice(0, 3)) {
      result.push({
        id: `import:${item.candidate.candidate_id}`,
        title: `允许读取 ${item.source.label} · ${item.candidate.display_name || "发现的新资料"}`,
        detail: "目前只读取了文件元数据。正文访问需要你的明确授权。",
        target: "attention",
      });
    }
    if (vector.rebuild_required === true) {
      result.push({
        id: "vector-rebuild",
        title: "向量索引重建需要你确认",
        detail: "这是不可逆维护动作，因此灵机停在主人边界，没有自动执行。",
        target: "vector_center",
      });
    }
    return result;
  }, [importCandidates, reviewItems, vector.rebuild_required]);

  const activeItems = feed.items.filter((item) => ["queued", "leased", "running", "retrying"].includes(item.status.toLowerCase()));
  const recentOutcome = feed.recentActivity.slice(0, 4);
  const recentMemories = Array.isArray((memories as Record<string, unknown> | null)?.items)
    ? ((memories as Record<string, unknown>).items as unknown[]).slice(0, 4)
    : [];
  const nextItem = activeItems[0] ?? feed.items[0] ?? null;
  const currentCodex = resource.data?.current?.activity ?? null;
  const unknownOwnerState = resource.data?.reviews === null || resource.data?.assistants === null;

  const heroTitle = decisions.length > 0
    ? `有 ${decisions.length} 件事真的需要你`
    : unknownOwnerState
      ? "正在确认有没有事情需要你"
      : "现在不用你做任何事";
  const heroDetail = decisions.length > 0
    ? "这些事项都有真实对象和明确原因。其余扫描、整理、重试和索引由灵机自己继续。"
    : unknownOwnerState
      ? "部分主人边界状态暂时没读到，灵机正在自动重试；未知不会被显示成“没有待办”。"
      : activeItems.length > 0
        ? `灵机正在自动处理 ${activeItems.length} 项工作，你不用守着它。`
        : "没有权限、冲突或不可逆事项等你处理。灵机会继续观察已授权来源。";

  return (
    <div className="workbench-v4 home-v4">
      <section className={`v4-brief-hero ${decisions.length ? "needs-owner" : unknownOwnerState ? "unknown" : "clear"}`}>
        <div className="v4-brief-copy">
          <span className="v4-kicker">现在需要你吗</span>
          <h2>{heroTitle}</h2>
          <p>{heroDetail}</p>
        </div>
        <div className="v4-brief-state">
          <span className={`v4-state-orb ${decisions.length ? "warning" : unknownOwnerState ? "unknown" : "ok"}`} />
          <div><strong>{decisions.length ? "等待主人" : unknownOwnerState ? "确认中" : "灵机自己继续"}</strong><small>{resource.refreshing ? "正在同步最新事实" : "后台自动更新"}</small></div>
        </div>
      </section>

      {reviewMismatch && <Notice kind="warning">系统报告有待确认记忆，但当前没有读到对应候选对象。灵机不会给你一个会打开空页面的“去处理”按钮。</Notice>}
      {feed.detailsState === "unavailable" && <Notice kind="warning">{feed.detailsMessage}</Notice>}

      {decisions.length > 0 && (
        <section className="v4-owner-inbox">
          <div className="v4-section-heading"><div><span className="v4-kicker">需要我</span><h3>只有真正跨过主人边界的事</h3></div><button className="v4-link" onClick={() => onNavigate("attention")}>查看全部</button></div>
          <div className="v4-decision-list">
            {decisions.map((decision) => (
              <button
                className="v4-decision-row"
                key={decision.id}
                onClick={() => decision.memoryId ? onOpenReview(decision.memoryId) : onNavigate(decision.target)}
              >
                <span><strong>{decision.title}</strong><small>{decision.detail}</small></span><b>处理</b>
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="v4-home-grid">
        <article className="v4-surface v4-outcomes">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">刚刚替你做了什么</span><h3>真实结果</h3></div><button className="v4-link" onClick={() => onNavigate("activity")}>工作履历</button></div>
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
            <div className="v4-empty-state compact"><strong>最近没有新的完成动作</strong><p>没有实际动作时，这里不会制造“系统很忙”的假动态。</p></div>
          )}
        </article>

        <article className="v4-surface v4-now">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">现在正在做什么</span><h3>{activeItems.length ? `${activeItems.length} 项自动工作` : currentCodex ? "Codex 工作正在进行" : "当前没有前台工作"}</h3></div></div>
          {activeItems.length ? (
            <div className="v4-work-stack">
              {activeItems.slice(0, 3).map((item) => (
                <button className="v4-work-row" key={item.id} onClick={() => onNavigate(item.memoryId ? "memory" : "activity")}>
                  <span className={`v4-work-state ${workTone(item)}`}>{item.stageLabel}</span>
                  <div><strong>{item.title}</strong><small>{item.done}</small></div>
                </button>
              ))}
            </div>
          ) : currentCodex ? (
            <div className="v4-current-callout"><strong>{currentCodex.summary || "Codex 工作正在进行"}</strong><p>阶段：{currentCodex.stage || "状态更新中"}</p></div>
          ) : (
            <div className="v4-empty-state compact"><strong>系统空闲</strong><p>没有需要等待的任务。后台发现和状态检查仍按已授权范围继续。</p></div>
          )}
        </article>
      </section>

      <section className="v4-surface v4-next-surface">
        <div className="v4-section-heading"><div><span className="v4-kicker">接下来灵机会做什么</span><h3>{nextItem ? nextItem.nextStep : "继续观察已授权来源"}</h3></div><span className="v4-next-actor">下一执行者：{nextItem?.ownerActionRequired ? "你" : "灵机"}</span></div>
        <p>{nextItem ? `${nextItem.title} · 当前：${nextItem.done}` : "目前没有排队资料。发现新的可信变化后，灵机会先判断能否安全自动处理；只有必须由你决定时才会打扰你。"}</p>
      </section>

      <section className="v4-home-grid secondary">
        <article className="v4-surface">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">记忆发生了什么变化</span><h3>最近进入第二永久记忆大脑的内容</h3></div><button className="v4-link" onClick={() => onNavigate("memory")}>打开记忆</button></div>
          {recentMemories.length ? (
            <div className="v4-memory-mini-list">
              {recentMemories.map((item, index) => <button key={index} onClick={() => onNavigate("memory")}><strong>{safeMemoryTitle(item)}</strong><small>查看真实内容和来源证据</small></button>)}
            </div>
          ) : <div className="v4-empty-state compact"><strong>还没有可展示的永久记忆变化</strong><p>资料数量不等于永久记忆。只有真实记忆对象才会出现在这里。</p></div>}
        </article>

        <article className="v4-surface">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">主动发现</span><h3>{detectedAssistants.length ? `已发现 ${detectedAssistants.length} 个可接管工具` : "继续扫描已支持环境"}</h3></div></div>
          {detectedAssistants.length ? (
            <div className="v4-discovery-list">
              {detectedAssistants.slice(0, 5).map((assistant) => (
                <div key={assistant.id}><span className="v4-discovery-dot" /><div><strong>{assistant.label}</strong><small>{assistant.message || `已识别 ${Number(assistant.candidate_count ?? 0).toLocaleString()} 条记录元数据`}</small></div></div>
              ))}
            </div>
          ) : <div className="v4-empty-state compact"><strong>暂未发现新的支持来源</strong><p>扫描是后台行为，不需要你手动刷新。</p></div>}
          {importCandidates.length > 0 && <button className="v4-inline-alert" onClick={() => onNavigate("attention")}>发现 {importCandidates.length} 份资料需要正文读取授权</button>}
        </article>
      </section>

      <details className="v4-advanced-summary">
        <summary>高级状态与系统统计</summary>
        <div>
          <span>资料统计：{expectedDocuments ?? "待确认"}</span>
          <span>自动驾驶：{String(resource.data?.autopilot?.state ?? "状态待确认")}</span>
          <span>向量：{String(vector.state ?? "状态待确认")}</span>
        </div>
      </details>
    </div>
  );
}
