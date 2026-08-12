import { useCallback, useState } from "react";
import AssistantDiscoveryPanel from "../components/AssistantDiscoveryPanel";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import "../AssistantAutopilot.css";

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

function authLabel(value: unknown): string {
  const state = String(value ?? "not_configured").toLowerCase();
  if (state === "verified") return "已连接";
  if (state === "permission_insufficient") return "权限不足";
  if (["expired", "invalid"].includes(state)) return "需重新认证";
  if (state === "error") return "认证暂不可用";
  return "等待认证";
}

export default function OverviewPage({
  data,
  api,
  active,
  onNavigate,
}: {
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
  const autopilotResource = usePollingResource({
    fetcher: loadAutopilot,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 20_000,
    pauseWhenHidden: true,
  });

  if (!data) return <Empty text="灵机核心连接后会自动准备环境并开始工作。" />;

  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queue = ((d.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const storageRoot = (d.storage ?? {}) as Record<string, unknown>;
  const storageAlerts = (storageRoot.alerts ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? d.vector_status ?? {}) as Record<string, unknown>;
  const runtimeState = memoryRuntime.state ?? health.status;
  const stale = Boolean(memoryRuntime.stale) || autopilotResource.stale;
  const autopilot = (autopilotResource.data ?? {}) as Record<string, unknown>;
  const autopilotKnown = Boolean(autopilotResource.data);
  const recentActions = Array.isArray(autopilot.recent_actions)
    ? autopilot.recent_actions as Record<string, unknown>[]
    : [];
  const latestAutomaticAction = recentActions[0];
  const authProviders = Array.isArray((d.auth_status as Record<string, unknown> | undefined)?.providers)
    ? ((d.auth_status as Record<string, unknown>).providers as Record<string, unknown>[])
    : [];

  const irreversibleDecisionCount = vector.rebuild_required === true ? 1 : 0;
  const autopilotOwnerCount = Number(autopilot.owner_action_count ?? 0);
  const autopilotBackgroundCount = Number(autopilot.background_issue_count ?? 0);
  const fallbackSystemIssueCount = [
    Number(health.error_count ?? 0) > 0,
    Number(queue.failed ?? 0) > 0,
    storageAlerts.below_minimum_free === true,
  ].filter(Boolean).length;
  const systemIssueCount = autopilotKnown ? autopilotBackgroundCount : fallbackSystemIssueCount;
  const ownerDecisionCount = importDecisionCount
    + pendingReviewCount
    + (autopilotKnown ? autopilotOwnerCount : irreversibleDecisionCount);
  const runningTasks = Number(queue.running ?? 0);

  const headline = ownerDecisionCount > 0
    ? `${ownerDecisionCount} 件事需要你确认`
    : systemIssueCount > 0
      ? "灵机正在自动处理异常"
      : stateLabel(runtimeState);

  const autopilotSummary = String(autopilot.summary ?? "").trim();
  const summary = ownerDecisionCount > 0
    ? "能安全自动完成的部分已经先做完，只把权限、数据完整性和不可逆操作留给你。"
    : autopilotKnown && autopilotSummary
      ? autopilotSummary
      : systemIssueCount > 0
        ? `发现 ${systemIssueCount} 类系统问题，灵机会先自己重试、恢复和诊断。除非确认无法自动解决，否则不会打断你。`
        : runningTasks > 0
          ? `${runningTasks} 个任务正在后台处理。扫描、同步、索引和恢复会继续自动进行。`
          : "没有需要你操作的事项。灵机会继续在后台发现来源、同步状态、维护记忆和等待新任务。";

  return (
    <div className="stack overview-page observation-page owner-autopilot-home">
      <section className="overview-hero owner-autopilot-hero">
        <div className="overview-hero-main">
          <span className="desktop-eyebrow">灵机</span>
          <div className="overview-title-line">
            <h2>{headline}</h2>
            <span className={`pill ${ownerDecisionCount > 0 ? "warning" : systemIssueCount > 0 ? "neutral" : "ok"}`}>
              {ownerDecisionCount > 0 ? "等你决定" : systemIssueCount > 0 ? "自动处理中" : "无需操作"}
            </span>
          </div>
          <p>{summary}</p>
        </div>
        <div className="observation-live-state">
          <span className={ownerDecisionCount === 0 && systemIssueCount === 0 ? "status-dot online" : "status-dot"} />
          <div>
            <strong>
              {latestAutomaticAction?.title
                ? `刚自动处理：${String(latestAutomaticAction.title)}`
                : runningTasks > 0
                  ? `${runningTasks} 个后台任务`
                  : "后台持续运行"}
            </strong>
            <small>
              {latestAutomaticAction?.verified === true
                ? "已自动复验"
                : autopilotResource.refreshing
                  ? "正在同步自动维护状态"
                  : "状态自动更新"}
            </small>
          </div>
        </div>
      </section>

      {stale && <Notice kind="warning">部分状态来自旧快照，灵机正在后台重新确认，不需要手动刷新。</Notice>}
      {autopilotResource.error && autopilotResource.data && (
        <Notice kind="warning">自动维护状态暂时同步失败，灵机会继续后台运行并自动重试。</Notice>
      )}

      {authProviders.length > 0 && (
        <section className="assistant-autopilot-passive" aria-label="本机连接状态">
          <span className="desktop-eyebrow">本机连接</span>
          {authProviders.map((provider) => (
            <div className="autopilot-background-issue" key={String(provider.provider)}>
              <strong>{String(provider.provider)}：{authLabel(provider.state)}</strong>
            </div>
          ))}
        </section>
      )}

      <CurrentWorkPanel api={api} active={active} onPendingReviewCount={setPendingReviewCount} />

      {ownerDecisionCount > 0 && (
        <section className="attention-summary attention-summary-warning owner-only-decision-card">
          <div>
            <span className="desktop-eyebrow">只需要你处理这一类事</span>
            <h3>{ownerDecisionCount} 项需要确认</h3>
            <p>这里只放读取真实资料、数据完整性、写入永久记忆或不可逆操作。普通故障、扫描和重试不会混进来。</p>
          </div>
          <button className="button primary" onClick={() => onNavigate("attention")}>去确认</button>
        </section>
      )}

      {systemIssueCount > 0 && (
        <section className="autopilot-background-issue" role="status">
          <div>
            <span className="desktop-eyebrow">后台自动处理</span>
            <strong>正在处理 {systemIssueCount} 类系统异常</strong>
            <small>灵机会先自行诊断、安全修复、复验并保留记录。只有确实需要你时才会上升为“需要确认”。</small>
          </div>
          <button className="text-button" onClick={() => onNavigate("activity")}>查看处理记录</button>
        </section>
      )}

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
