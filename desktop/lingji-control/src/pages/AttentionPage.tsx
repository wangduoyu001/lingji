import { useCallback, useMemo } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import type { CodexCurrent } from "./codexWorkspaceTypes";

type AttentionSnapshot = {
  current: CodexCurrent;
};

type AttentionItem = {
  id: string;
  title: string;
  detail: string;
  target: PageId;
  severity: "warning" | "error";
};

export default function AttentionPage({
  api,
  active,
  overview,
  onNavigate,
}: {
  api: LingJiApi;
  active: boolean;
  overview: Row | null;
  onNavigate: (page: PageId) => void;
}) {
  const load = useCallback(async (signal: AbortSignal): Promise<AttentionSnapshot> => ({
    current: await api.get<CodexCurrent>("/api/codex/current", { signal }),
  }), [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 25_000,
    pauseWhenHidden: true,
  });

  const items = useMemo<AttentionItem[]>(() => {
    const result: AttentionItem[] = [];
    const data = (overview ?? {}) as Record<string, unknown>;
    const health = (data.health ?? {}) as Record<string, unknown>;
    const queue = ((data.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
    const memoryRuntime = (data.memory_runtime ?? {}) as Record<string, unknown>;
    const vector = (memoryRuntime.vector ?? data.vector_status ?? {}) as Record<string, unknown>;
    const storageRoot = (data.storage ?? {}) as Record<string, unknown>;
    const storageAlerts = (storageRoot.alerts ?? {}) as Record<string, unknown>;

    const pendingReview = resource.data
      ? Number(resource.data.current.pending_review_count ?? 0)
      : null;
    if (pendingReview !== null && pendingReview > 0) {
      result.push({
        id: "memory-review",
        title: `${pendingReview} 条候选记忆等待确认`,
        detail: "只有主人能够批准、编辑或拒绝长期记忆。",
        target: "memory_review",
        severity: "warning",
      });
    }

    const failedJobs = Number(queue.failed ?? 0);
    if (failedJobs > 0) {
      result.push({
        id: "failed-jobs",
        title: `${failedJobs} 个任务处理失败`,
        detail: "自动重试已经结束，需要查看错误原因或调整输入。",
        target: "jobs",
        severity: "error",
      });
    }

    const errorCount = Number(health.error_count ?? 0);
    if (errorCount > 0) {
      result.push({
        id: "health-errors",
        title: `${errorCount} 个系统错误需要检查`,
        detail: "查看最近日志和健康检查，确认是否需要人工处理。",
        target: "logs",
        severity: "error",
      });
    }

    if (vector.rebuild_required === true) {
      result.push({
        id: "vector-rebuild",
        title: "向量索引需要处理",
        detail: "系统检测到索引或维度不一致，不会自动删除或重建 Collection。",
        target: "vector_center",
        severity: "error",
      });
    }

    if (storageAlerts.below_minimum_free === true) {
      result.push({
        id: "low-disk",
        title: "磁盘剩余空间不足",
        detail: "灵机不会自动删除主人数据，请检查存储和冷归档。",
        target: "storage",
        severity: "error",
      });
    }

    return result;
  }, [overview, resource.data]);

  if (!active) return <Empty text="灵机核心连接后会自动汇总需要主人处理的事项。" />;
  if (resource.loading && !resource.data) return <Empty text="正在检查是否有事项需要主人处理…" />;

  const attentionUnknown = Boolean(resource.error && !resource.data);
  const hasAttention = items.length > 0;
  const heroClass = hasAttention || attentionUnknown
    ? "attention-hero attention-hero-warning"
    : "attention-hero attention-hero-clear";
  const heroTitle = attentionUnknown
    ? "部分待办状态暂时未知"
    : hasAttention
      ? `${items.length} 项需要你处理`
      : "暂时不需要你处理";
  const heroDetail = attentionUnknown
    ? "记忆审核状态读取失败，系统正在自动重试；不会把未知状态显示成一切正常。"
    : hasAttention
      ? "这里只显示系统不能自行决定、并且能确认仍未解决的事项。"
      : "后台任务、重试、索引更新和状态同步会继续自动运行。";

  return (
    <div className="stack observation-page">
      <section className={heroClass}>
        <div>
          <span className="desktop-eyebrow">OWNER ATTENTION</span>
          <h2>{heroTitle}</h2>
          <p>{heroDetail}</p>
        </div>
        <div className="observation-live-state">
          <span className={!hasAttention && !attentionUnknown ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{resource.refreshing ? "正在检查" : attentionUnknown ? "等待恢复" : "自动检查中"}</strong>
            <small>每 8 秒更新</small>
          </div>
        </div>
      </section>

      {resource.error && <Notice kind="warning">部分待办来源暂不可用，最近一次有效结果会被保留，系统将自动重试。</Notice>}

      {items.length ? (
        <div className="attention-list">
          {items.map((item) => (
            <article className={`attention-card attention-card-${item.severity}`} key={item.id}>
              <div>
                <span className={`pill ${item.severity}`}>{item.severity === "error" ? "需要处理" : "需要确认"}</span>
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
              </div>
              <button className="button secondary" onClick={() => onNavigate(item.target)}>查看详情</button>
            </article>
          ))}
        </div>
      ) : attentionUnknown ? (
        <section className="observation-empty-state observation-empty-large">
          <strong>无法确认记忆审核待办</strong>
          <p>其他已知异常仍会显示；待办来源恢复后，页面会自动更新。</p>
        </section>
      ) : (
        <section className="observation-empty-state observation-empty-large">
          <strong>系统会自己继续工作</strong>
          <p>没有待审核记忆、失败任务、索引冲突、空间告警或其他能够确认仍需主人决定的事项。</p>
        </section>
      )}

      <Notice>
        SHADOW 决策目前是审计历史，不具备“未读/已处理”状态，因此不会被冒充为当前待办；需要时可在高级诊断中查看。
      </Notice>
    </div>
  );
}
