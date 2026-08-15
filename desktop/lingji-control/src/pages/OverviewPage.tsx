import { useCallback, useMemo, useState } from "react";
import AssistantDiscoveryPanel from "../components/AssistantDiscoveryPanel";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import { buildOwnerWorkFeed, type OwnerWorkItem } from "../ownerWorkFeed";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import "../AssistantAutopilot.css";

type OwnerAction = {
  id: string;
  title: string;
  detail: string;
  target: PageId;
};

const numberOrNull = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

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

function workItemTarget(item: OwnerWorkItem): PageId {
  if (item.ownerActionRequired) return "attention";
  if (item.stage === "issue") return "activity";
  return "memory_inspector";
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
  const loadMemories = useCallback(
    (signal: AbortSignal) => api.get<Row>("/api/memory/inspector/memories?limit=20&offset=0", { signal }),
    [api],
  );
  const autopilotResource = usePollingResource({
    fetcher: loadAutopilot,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 20_000,
    pauseWhenHidden: true,
  });
  const memoryResource = usePollingResource({
    fetcher: loadMemories,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 20_000,
    pauseWhenHidden: true,
  });

  if (!data) return <Empty text="灵机核心连接后会自动准备环境并开始工作。" />;

  const d = data as Record<string, unknown>;
  const queueRoot = (d.queue ?? {}) as Record<string, unknown>;
  const progress = (d.memory_progress ?? {}) as Record<string, unknown>;
  const intake = (progress.intake ?? {}) as Record<string, unknown>;
  const retrieval = (progress.retrieval ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? d.vector_status ?? {}) as Record<string, unknown>;
  const events = Array.isArray(d.events) ? d.events : [];
  const expectedDocuments = numberOrNull(intake.documents);
  const chunks = numberOrNull(intake.chunks);
  const coveragePercent = numberOrNull(retrieval.coverage_percent);
  const autopilot = (autopilotResource.data ?? {}) as Record<string, unknown>;

  const feed = useMemo(() => buildOwnerWorkFeed({
    memoryResponse: memoryResource.data,
    queueResponse: queueRoot,
    events,
    expectedDocuments,
    limit: 20,
  }), [memoryResource.data, queueRoot, events, expectedDocuments]);

  const ownerActions = useMemo<OwnerAction[]>(() => {
    const items: OwnerAction[] = [];
    if (importDecisionCount > 0) {
      items.push({
        id: "assistant-import",
        title: `${importDecisionCount} 类 AI 历史等待你授权读取`,
        detail: "灵机只发现了资料位置，还没有读取正文。",
        target: "attention",
      });
    }
    if (pendingReviewCount > 0) {
      items.push({
        id: "memory-review",
        title: `${pendingReviewCount} 条候选记忆等待你确认`,
        detail: "确认后才会成为长期记忆；灵机不会替你决定。",
        target: "memory_review",
      });
    }
    if (vector.rebuild_required === true) {
      items.push({
        id: "vector-rebuild",
        title: "向量索引是否重建需要你确认",
        detail: "这是不可逆维护，灵机不会擅自执行。",
        target: "vector_center",
      });
    }
    const autopilotActions = Array.isArray(autopilot.owner_actions)
      ? autopilot.owner_actions.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
      : [];
    for (const action of autopilotActions) {
      const title = String(action.title ?? "需要你确认一项系统操作");
      if (items.some((item) => item.title === title)) continue;
      items.push({
        id: String(action.code ?? title),
        title,
        detail: String(action.summary ?? "灵机已经停在安全边界，等待你的决定。"),
        target: "attention",
      });
    }
    return items;
  }, [autopilot.owner_actions, importDecisionCount, pendingReviewCount, vector.rebuild_required]);

  const activeItem = feed.items.find((item) => ["queued", "leased", "running", "retrying"].includes(item.status.toLowerCase()));
  const latestItem = feed.items[0] ?? null;
  const focusTitle = activeItem
    ? `正在处理 · ${activeItem.title}`
    : latestItem
      ? `最近处理 · ${latestItem.title}`
      : "当前没有待处理资料";
  const focusDetail = activeItem?.done ?? latestItem?.done ?? "有新资料进入后，这里会直接显示具体资料和处理动作。";

  const heroTitle = ownerActions.length > 0
    ? `你现在有 ${ownerActions.length} 件事要处理`
    : feed.summary.active > 0
      ? "现在不用你做，灵机正在处理资料"
      : feed.summary.issues > 0
        ? "现在不用你做，但有资料处理未完成"
        : "现在不用你做任何事";
  const heroDetail = ownerActions.length > 0
    ? "下面只列真正需要你授权、确认或决定的事项。其余步骤由灵机继续自动处理。"
    : feed.summary.active > 0
      ? `当前有 ${feed.summary.active} 份资料在自动流程中。你可以直接看到是哪一份、已经做到哪一步。`
      : feed.summary.issues > 0
        ? `有 ${feed.summary.issues} 份资料没有完成，失败原因已保留；普通技术问题不会假装成你的待办。`
        : feed.items.length > 0
          ? "最近的资料已经处理到当前状态，没有权限或不可逆事项等你决定。"
          : "当前没有资料任务，也没有需要你确认的事项。";

  const stale = memoryResource.stale || autopilotResource.stale || Boolean(memoryRuntime.stale);

  return (
    <div className="stack observation-page owner-work-home">
      <section className={`owner-action-hero ${ownerActions.length > 0 ? "needs-owner" : feed.summary.issues > 0 ? "has-issue" : "is-clear"}`}>
        <div className="owner-action-copy">
          <span className="desktop-eyebrow">你现在需要做什么</span>
          <h1>{heroTitle}</h1>
          <p>{heroDetail}</p>
          {ownerActions.length > 0 && (
            <div className="owner-action-list">
              {ownerActions.map((action) => (
                <button className="owner-action-item" key={action.id} onClick={() => onNavigate(action.target)}>
                  <span><strong>{action.title}</strong><small>{action.detail}</small></span>
                  <b>去处理</b>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="owner-now-card" aria-label="灵机当前工作">
          <span className="desktop-eyebrow">灵机现在在做什么</span>
          <strong>{focusTitle}</strong>
          <p>{focusDetail}</p>
          <small>{memoryResource.refreshing || autopilotResource.refreshing ? "正在同步最新状态" : "状态自动更新，无需手动刷新"}</small>
        </div>
      </section>

      {stale && <Notice kind="warning">部分状态来自旧快照，灵机正在重新确认。未知状态不会显示成“一切正常”。</Notice>}
      {feed.detailsState === "unavailable" && <Notice kind="warning">{feed.detailsMessage}</Notice>}
      {memoryResource.error && !memoryResource.data && expectedDocuments === null && <Notice kind="warning">资料明细暂时读取失败，灵机会自动重试；当前不会用汇总数字代替明细。</Notice>}

      <section className="owner-work-surface" aria-label="资料工作清单">
        <div className="owner-work-heading">
          <div>
            <span className="desktop-eyebrow">资料工作清单</span>
            <h2>每一份资料，都说清楚做到哪了</h2>
            <p>这里展示真实资料，不再让“已收纳 2 份”成为终点。</p>
          </div>
          <button className="text-button" onClick={() => onNavigate("memory_inspector")}>查看全部记忆</button>
        </div>

        {feed.items.length > 0 ? (
          <div className="owner-work-list">
            {feed.items.map((item) => (
              <article className={`owner-work-item ${item.ownerActionRequired ? "needs-owner" : item.stage === "issue" ? "has-issue" : ""}`} key={item.id}>
                <div className="owner-work-identity">
                  <div className="owner-work-title-row">
                    <strong>{item.title}</strong>
                    <span className={`owner-stage-pill stage-${item.stage}`}>{item.stageLabel}</span>
                  </div>
                  <small>{item.source}{item.occurredAt ? ` · ${relativeTime(item.occurredAt)}` : ""}</small>
                </div>
                <div className="owner-work-fact">
                  <span>灵机已做</span>
                  <p>{item.done}</p>
                </div>
                <div className="owner-work-fact next">
                  <span>下一步</span>
                  <p>{item.nextStep}</p>
                </div>
                <div className="owner-work-action">
                  {item.ownerActionRequired && <span className="pill warning">需要你处理</span>}
                  <button className="text-button" onClick={() => onNavigate(workItemTarget(item))}>
                    {item.ownerActionRequired ? "去确认" : item.stage === "issue" ? "看原因" : "看资料"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : feed.detailsState === "unavailable" ? (
          <div className="owner-work-empty blocked">
            <strong>有资料，但现在拿不到具体明细</strong>
            <p>系统会继续重试读取。明细恢复前不会只显示一个数量假装已经说明白。</p>
          </div>
        ) : (
          <div className="owner-work-empty">
            <strong>当前没有资料任务</strong>
            <p>有新资料进入后，会直接在这里出现标题、处理结果和下一步。</p>
          </div>
        )}
      </section>

      <details className="owner-recent-activity">
        <summary>最近真实活动 · {feed.recentActivity.length}</summary>
        {feed.recentActivity.length > 0 ? (
          <div className="owner-activity-list">
            {feed.recentActivity.map((event) => (
              <div className={`owner-activity-row ${event.tone}`} key={event.id}>
                <span className="owner-activity-dot" />
                <div><strong>{event.title}</strong><small>{event.detail}</small></div>
                <time>{relativeTime(event.occurredAt)}</time>
              </div>
            ))}
          </div>
        ) : <p>最近没有新的实际处理动作。</p>}
      </details>

      <details className="owner-work-stats">
        <summary>系统统计与高级状态</summary>
        <div className="owner-work-stat-grid">
          <span><small>资料</small><strong>{expectedDocuments ?? "待确认"}</strong></span>
          <span><small>检索片段</small><strong>{chunks ?? "待确认"}</strong></span>
          <span><small>索引覆盖</small><strong>{coveragePercent === null ? "待确认" : `${coveragePercent}%`}</strong></span>
        </div>
        <p>{String(retrieval.precision_message ?? "没有验证样本时不宣称准确率。")}</p>
      </details>

      <CurrentWorkPanel api={api} active={active} onPendingReviewCount={setPendingReviewCount} />
      <AssistantDiscoveryPanel
        api={api}
        active={active}
        onOpenCodex={() => onNavigate("codex_workspace")}
        onOpenActivity={() => onNavigate("activity")}
        onOwnerDecisionCount={setImportDecisionCount}
      />
    </div>
  );
}
