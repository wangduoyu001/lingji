import { useCallback, useState } from "react";
import AssistantDiscoveryPanel from "../components/AssistantDiscoveryPanel";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import "../AssistantAutopilot.css";

type OverviewEvent = {
  event_id?: number;
  event_type?: string;
  created_at?: string;
  payload?: Record<string, unknown>;
};

type QueueItem = {
  source_type?: string;
  status?: string;
  progress_message?: string | null;
};

type FlowTone = "done" | "active" | "owner" | "issue" | "waiting";
type FlowStage = { id: string; index: string; title: string; state: string; detail: string; tone: FlowTone };

const numberOrNull = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

function stateLabel(value: unknown): string {
  const state = String(value ?? "unknown").toLowerCase();
  const labels: Record<string, string> = {
    healthy: "灵机正在自己工作",
    ready: "灵机已经准备好",
    available: "灵机已经准备好",
    degraded: "灵机正在恢复部分能力",
    configuration_required: "灵机正在完成首次准备",
    warning: "灵机正在处理异常",
    stale: "灵机正在重新确认状态",
    failed: "灵机遇到无法自动处理的问题",
    error: "灵机遇到无法自动处理的问题",
    unavailable: "灵机当前不可用",
    blocked: "灵机当前被阻止",
  };
  return labels[state] ?? "灵机正在运行";
}

function quantity(value: unknown): string {
  return typeof value === "number" ? value.toLocaleString("zh-CN") : "正在确认";
}

function relativeTime(value: unknown): string {
  const timestamp = Date.parse(String(value ?? ""));
  if (!Number.isFinite(timestamp)) return "刚刚";
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return "刚刚";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  return hours < 24 ? `${hours} 小时前` : `${Math.round(hours / 24)} 天前`;
}

function sourceLabel(value: unknown): string {
  const key = String(value ?? "").toLowerCase();
  return ({
    chatgpt_export: "ChatGPT 历史",
    codex_report: "Codex 工作记录",
    media: "媒体资料",
    web: "网页资料",
  } as Record<string, string>)[key] ?? (key || "新资料");
}

function eventText(event: OverviewEvent): { title: string; detail: string; tone: FlowTone } {
  const type = String(event.event_type ?? "");
  const payload = event.payload ?? {};
  const known: Record<string, { title: string; detail: string; tone: FlowTone }> = {
    capture_duplicate: { title: "发现重复资料，已自动跳过", detail: "没有创建第二份任务或重复记忆。", tone: "done" },
    capture_job_retried: { title: "失败任务已自动重新排队", detail: "保留原失败记录，并继续按重试策略处理。", tone: "active" },
    capture_job_cancelled: { title: "任务已结束", detail: "任务已从处理队列移除，历史记录仍保留。", tone: "waiting" },
    capture_paused: { title: "资料收纳已暂停", detail: "暂停期间不会接收新的采集任务。", tone: "issue" },
    capture_resumed: { title: "资料收纳已恢复", detail: "新的资料会继续自动进入处理流程。", tone: "done" },
    autopilot_repair: { title: "已自动修复一个运行问题", detail: "修复后已经重新检查，不需要手动重复操作。", tone: "done" },
    autopilot_cycle_failed: { title: "自动巡检暂时失败", detail: "已保留错误并等待下一轮自动重试。", tone: "issue" },
    real_environment_acceptance: { title: "已完成一次环境检查", detail: "检查结果已保存，可在高级记录中追溯。", tone: "done" },
  };
  if (type === "capture_submitted") {
    return {
      title: `已收下 ${sourceLabel(payload.source_type)}`,
      detail: payload.job_id ? "已进入后台队列，后续解析和索引无需手动触发。" : "已进入后台处理流程。",
      tone: "active",
    };
  }
  return known[type] ?? {
    title: type ? type.replaceAll("_", " ") : "系统状态已更新",
    detail: "这是灵机实际记录的本地事件。",
    tone: "waiting",
  };
}

function queueFocus(queue: QueueItem[]): { title: string; detail: string } | null {
  const current = queue.find((item) => ["running", "leased", "retrying", "queued"].includes(String(item.status ?? "").toLowerCase()));
  if (!current) return null;
  const status = String(current.status ?? "").toLowerCase();
  const action = status === "queued" ? "等待处理" : status === "retrying" ? "自动重试" : "正在处理";
  return {
    title: `${action} · ${sourceLabel(current.source_type)}`,
    detail: String(current.progress_message ?? "解析、整理和索引会继续在后台完成。"),
  };
}

function buildWorkflow({
  documents,
  chunks,
  recentQueue,
  runningTasks,
  completedTasks,
  failedTasks,
  pendingReviewCount,
  ownerDecisionCount,
  coveragePercent,
  vectorState,
  precisionMessage,
}: {
  documents: number | null;
  chunks: number | null;
  recentQueue: QueueItem[];
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  pendingReviewCount: number;
  ownerDecisionCount: number;
  coveragePercent: number | null;
  vectorState: unknown;
  precisionMessage: unknown;
}): FlowStage[] {
  const hasMaterial = (documents ?? 0) > 0 || recentQueue.length > 0;
  const vectorKey = String(vectorState ?? "unknown").toLowerCase();
  const vectorIssue = !["healthy", "ready", "available", "unknown"].includes(vectorKey);
  return [
    { id: "discover", index: "01", title: "发现来源", state: "持续扫描", detail: "识别本机 AI 工具和可导入资料，只读取元数据。", tone: "active" },
    { id: "intake", index: "02", title: "收纳", state: hasMaterial ? `已收纳 ${quantity(documents)} 份` : "等待新资料", detail: chunks === null ? "资料进入后自动去重并排队。" : `当前形成 ${quantity(chunks)} 个可检索片段。`, tone: hasMaterial ? "done" : "waiting" },
    { id: "parse", index: "03", title: "解析", state: runningTasks > 0 ? `${runningTasks} 项处理中` : failedTasks > 0 ? `${failedTasks} 项失败` : completedTasks > 0 ? "最近处理完成" : "等待输入", detail: runningTasks > 0 ? "读取、提取、结构化按队列连续执行。" : failedTasks > 0 ? "失败原因已保留，自动重试到上限后停止。" : "有新资料时自动开始。", tone: runningTasks > 0 ? "active" : failedTasks > 0 ? "issue" : completedTasks > 0 ? "done" : "waiting" },
    { id: "candidate", index: "04", title: "候选", state: pendingReviewCount > 0 ? `${pendingReviewCount} 条待审核` : "没有待审核候选", detail: "提取结果先成为候选，不直接写进永久记忆。", tone: pendingReviewCount > 0 ? "owner" : "done" },
    { id: "confirm", index: "05", title: "确认", state: ownerDecisionCount > 0 ? `${ownerDecisionCount} 项等你决定` : "当前无需确认", detail: ownerDecisionCount > 0 ? "只有权限、永久记忆和不可逆操作会停在这里。" : "安全的后台步骤不会打断你。", tone: ownerDecisionCount > 0 ? "owner" : "done" },
    { id: "index", index: "06", title: "索引", state: vectorIssue ? "语义索引降级" : coveragePercent === null ? "正在确认覆盖" : `覆盖 ${coveragePercent}%`, detail: vectorIssue ? "全文检索继续可用，系统不会擅自重建索引。" : "新增内容会自动更新可重建索引。", tone: vectorIssue ? "issue" : coveragePercent !== null ? "done" : "active" },
    { id: "retrieve", index: "07", title: "取回", state: coveragePercent === null ? "等待索引" : "可以开始检索", detail: String(precisionMessage ?? "没有验证样本时不宣称准确率。"), tone: coveragePercent === null ? "waiting" : "done" },
  ];
}

export default function OverviewPage({ data, api, active, onNavigate }: {
  data: Row | null;
  api: LingJiApi;
  active: boolean;
  onNavigate: (page: PageId) => void;
}) {
  const [importDecisionCount, setImportDecisionCount] = useState(0);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const loadAutopilot = useCallback(
    (signal: AbortSignal) => api.get<Row>("/api/autopilot/status", { signal }),
    [api],
  );
  const autopilotResource = usePollingResource({ fetcher: loadAutopilot, enabled: active, intervalMs: 8_000, staleAfterMs: 20_000, pauseWhenHidden: true });

  if (!data) return <Empty text="灵机核心连接后会自动准备环境并开始工作。" />;

  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queueRoot = (d.queue ?? {}) as Record<string, unknown>;
  const queue = (queueRoot.stats ?? {}) as Record<string, unknown>;
  const recentQueue = Array.isArray(queueRoot.recent) ? queueRoot.recent as QueueItem[] : [];
  const storageAlerts = (((d.storage ?? {}) as Record<string, unknown>).alerts ?? {}) as Record<string, unknown>;
  const progress = (d.memory_progress ?? {}) as Record<string, unknown>;
  const intake = (progress.intake ?? {}) as Record<string, unknown>;
  const updates = (progress.updates ?? {}) as Record<string, unknown>;
  const retrieval = (progress.retrieval ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? d.vector_status ?? {}) as Record<string, unknown>;
  const autopilot = (autopilotResource.data ?? {}) as Record<string, unknown>;
  const recentActions = Array.isArray(autopilot.recent_actions) ? autopilot.recent_actions as Record<string, unknown>[] : [];
  const overviewEvents = Array.isArray(d.events) ? d.events as OverviewEvent[] : [];

  const autopilotKnown = Boolean(autopilotResource.data);
  const fallbackSystemIssueCount = [Number(health.error_count ?? 0) > 0, Number(queue.failed ?? 0) > 0, storageAlerts.below_minimum_free === true].filter(Boolean).length;
  const systemIssueCount = autopilotKnown ? Number(autopilot.background_issue_count ?? 0) : fallbackSystemIssueCount;
  const irreversibleDecisionCount = vector.rebuild_required === true ? 1 : 0;
  const ownerDecisionCount = importDecisionCount + pendingReviewCount + (autopilotKnown ? Number(autopilot.owner_action_count ?? 0) : irreversibleDecisionCount);
  const runningTasks = Number(queue.running ?? 0) + Number(queue.retrying ?? 0);
  const queuedTasks = Number(queue.queued ?? 0);
  const completedTasks = Number(queue.completed ?? 0);
  const failedTasks = Number(queue.failed ?? 0);
  const coveragePercent = numberOrNull(retrieval.coverage_percent);
  const documents = numberOrNull(intake.documents);
  const chunks = numberOrNull(intake.chunks);

  const headline = ownerDecisionCount > 0
    ? `${ownerDecisionCount} 件事需要你决定`
    : runningTasks > 0 || queuedTasks > 0
      ? "灵机正在处理新内容"
      : systemIssueCount > 0
        ? "灵机正在自己处理异常"
        : stateLabel(memoryRuntime.state ?? health.status);

  const autopilotSummary = String(autopilot.summary ?? "").trim();
  const summary = ownerDecisionCount > 0
    ? "能安全自动完成的步骤已经先做完，只有读取正文、永久记忆和不可逆操作会停下来等你。"
    : runningTasks > 0 || queuedTasks > 0
      ? `当前 ${runningTasks} 个任务处理中、${queuedTasks} 个等待处理。完成后会继续解析、整理和更新索引。`
      : autopilotKnown && autopilotSummary
        ? autopilotSummary
        : systemIssueCount > 0
          ? `发现 ${systemIssueCount} 类系统问题，灵机会先自动诊断、重试和复验。`
          : "当前没有需要你操作的事项。来源发现、状态检查和记忆维护仍会在后台继续。";

  const currentFocus = queueFocus(recentQueue);
  const latestAutomaticAction = recentActions[0];
  const focusTitle = currentFocus?.title ?? (latestAutomaticAction?.title ? `刚自动处理 · ${String(latestAutomaticAction.title)}` : "后台持续巡检");
  const focusDetail = currentFocus?.detail ?? (latestAutomaticAction?.verified === true ? "这一步已经自动复验。" : "没有需要你手动刷新的状态。 ");
  const workflowStages = buildWorkflow({ documents, chunks, recentQueue, runningTasks, completedTasks, failedTasks, pendingReviewCount, ownerDecisionCount, coveragePercent, vectorState: vector.state, precisionMessage: retrieval.precision_message });
  const visibleEvents = overviewEvents.slice(0, 5);
  const memoryHeadline = documents === null ? "正在确认记忆状态" : documents === 0 ? "还没有正式收纳的资料" : `已收纳 ${quantity(documents)} 份资料`;
  const memoryDetail = coveragePercent === null ? `${quantity(chunks)} 个片段 · 索引覆盖正在建立` : `${quantity(chunks)} 个片段 · 当前索引覆盖 ${coveragePercent}%`;
  const stale = Boolean(memoryRuntime.stale) || autopilotResource.stale;

  return (
    <div className="stack overview-page observation-page owner-autopilot-home owner-home-v2">
      <section className={`autopilot-command-center ${ownerDecisionCount > 0 ? "needs-owner" : systemIssueCount > 0 ? "has-issue" : "is-calm"}`}>
        <div className="autopilot-command-copy">
          <div className="autopilot-command-kicker">
            <span className="status-dot online" />
            <span>灵机自动驾驶</span>
            <span className="autopilot-command-divider" />
            <span>{ownerDecisionCount > 0 ? "等你决定" : systemIssueCount > 0 ? "自动处理中" : "无需操作"}</span>
          </div>
          <h1>{headline}</h1>
          <p>{summary}</p>
          {ownerDecisionCount > 0 && <button className="button primary" onClick={() => onNavigate("attention")}>只看需要我决定的事</button>}
          {ownerDecisionCount === 0 && systemIssueCount > 0 && <button className="text-button" onClick={() => onNavigate("activity")}>查看自动处理记录</button>}
        </div>
        <div className="autopilot-now-card" aria-label="灵机当前正在做的事">
          <span className="desktop-eyebrow">此刻正在做</span>
          <strong>{focusTitle}</strong>
          <p>{focusDetail}</p>
          <small>{autopilotResource.refreshing ? "正在同步最新状态" : "状态自动更新，无需手动刷新"}</small>
        </div>
      </section>

      {stale && <Notice kind="warning">部分状态来自旧快照，灵机正在后台重新确认，不需要手动刷新。</Notice>}
      {autopilotResource.error && autopilotResource.data && <Notice kind="warning">自动维护状态暂时同步失败，灵机会继续后台运行并自动重试。</Notice>}

      <section className="autopilot-flow-surface" aria-label="自动工作流">
        <div className="autopilot-section-heading">
          <div><span className="desktop-eyebrow">自动工作流</span><h2>从发现到可取回，系统自己往下走</h2></div>
          <button className="text-button" onClick={() => onNavigate("activity")}>查看全部记录</button>
        </div>
        <div className="autopilot-flow-track">
          {workflowStages.map((stage) => (
            <article className={`autopilot-flow-stage ${stage.tone}`} key={stage.id}>
              <div className="autopilot-flow-index">{stage.index}</div>
              <div><span>{stage.title}</span><strong>{stage.state}</strong><small>{stage.detail}</small></div>
            </article>
          ))}
        </div>
      </section>

      <div className="autopilot-home-grid">
        <section className="autopilot-event-stream" aria-label="最近自动处理记录">
          <div className="autopilot-section-heading compact"><div><span className="desktop-eyebrow">最近自动完成</span><h2>不是“在线”，而是真的做过什么</h2></div></div>
          {visibleEvents.length > 0 ? (
            <div className="autopilot-event-list">
              {visibleEvents.map((event, index) => {
                const copy = eventText(event);
                return (
                  <article className={`autopilot-event-item ${copy.tone}`} key={event.event_id ?? `${event.event_type}-${index}`}>
                    <span className="autopilot-event-marker" />
                    <div><strong>{copy.title}</strong><p>{copy.detail}</p></div>
                    <time>{relativeTime(event.created_at)}</time>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="autopilot-empty-stream"><strong>还没有新的处理记录</strong><p>后台巡检和来源扫描仍在继续；有实际动作后这里会留下记录。</p></div>
          )}
        </section>

        <section className="memory-progress-v2" aria-label="记忆进度">
          <span className="desktop-eyebrow">记忆进度</span>
          <h2>{memoryHeadline}</h2>
          <p>{memoryDetail}</p>
          <div className="memory-progress-v2-meter"><span style={{ width: `${coveragePercent ?? 0}%` }} /></div>
          <div className="memory-progress-v2-status">
            <span><small>更新中</small><strong>{quantity(updates.running)}</strong></span>
            <span><small>等待</small><strong>{quantity(updates.queued)}</strong></span>
            <span><small>已完成</small><strong>{quantity(updates.completed)}</strong></span>
          </div>
          <small className="memory-progress-v2-footnote">{String(retrieval.precision_message ?? "没有验证样本时不宣称准确率。")}</small>
        </section>
      </div>

      <CurrentWorkPanel api={api} active={active} onPendingReviewCount={setPendingReviewCount} />
      <AssistantDiscoveryPanel api={api} active={active} onOpenCodex={() => onNavigate("codex_workspace")} onOpenActivity={() => onNavigate("activity")} onOwnerDecisionCount={setImportDecisionCount} />
    </div>
  );
}
