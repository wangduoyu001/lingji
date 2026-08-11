import { useState } from "react";
import AssistantDiscoveryPanel from "../components/AssistantDiscoveryPanel";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Notice } from "../components/ui";
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

  if (!data) return <Empty text="灵机核心连接后会自动准备环境并开始工作。" />;

  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queue = ((d.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const storageRoot = (d.storage ?? {}) as Record<string, unknown>;
  const storageAlerts = (storageRoot.alerts ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? d.vector_status ?? {}) as Record<string, unknown>;
  const runtimeState = memoryRuntime.state ?? health.status;
  const stale = Boolean(memoryRuntime.stale);

  const irreversibleDecisionCount = vector.rebuild_required === true ? 1 : 0;
  const systemIssueCount = [
    Number(health.error_count ?? 0) > 0,
    Number(queue.failed ?? 0) > 0,
    storageAlerts.below_minimum_free === true,
  ].filter(Boolean).length;
  const ownerDecisionCount = importDecisionCount + pendingReviewCount + irreversibleDecisionCount;
  const runningTasks = Number(queue.running ?? 0);

  const headline = ownerDecisionCount > 0
    ? `${ownerDecisionCount} 件事需要你确认`
    : systemIssueCount > 0
      ? "灵机正在自动处理异常"
      : stateLabel(runtimeState);

  const summary = ownerDecisionCount > 0
    ? "能安全自动完成的部分已经先做完，只把权限、永久记忆和不可逆操作留给你。"
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
            <strong>{runningTasks > 0 ? `${runningTasks} 个后台任务` : "后台持续运行"}</strong>
            <small>状态自动更新</small>
          </div>
        </div>
      </section>

      {stale && <Notice kind="warning">部分状态来自旧快照，灵机正在后台重新确认，不需要手动刷新。</Notice>}

      <CurrentWorkPanel api={api} active={active} onPendingReviewCount={setPendingReviewCount} />

      {ownerDecisionCount > 0 && (
        <section className="attention-summary attention-summary-warning owner-only-decision-card">
          <div>
            <span className="desktop-eyebrow">只需要你处理这一类事</span>
            <h3>{ownerDecisionCount} 项需要确认</h3>
            <p>这里只放读取真实资料、写入永久记忆或不可逆操作。普通故障、扫描和重试不会混进来。</p>
          </div>
          <button className="button primary" onClick={() => onNavigate("attention")}>去确认</button>
        </section>
      )}

      {systemIssueCount > 0 && (
        <section className="autopilot-background-issue" role="status">
          <div>
            <span className="desktop-eyebrow">后台自动处理</span>
            <strong>发现 {systemIssueCount} 类系统异常</strong>
            <small>灵机会先自行重试、恢复和保留证据。只有确实需要你时才会上升为“需要确认”。</small>
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
