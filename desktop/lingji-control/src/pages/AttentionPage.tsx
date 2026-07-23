import { useCallback, useMemo } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import type { AutoReviewMetrics } from "./autoReviewTypes";
import type { CodexCurrent } from "./codexWorkspaceTypes";

type AttentionSnapshot = {
  current: CodexCurrent | null;
  metrics: AutoReviewMetrics | null;
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
  const load = useCallback(async (signal: AbortSignal): Promise<AttentionSnapshot> => {
    const [current, metrics] = await Promise.allSettled([
      api.get<CodexCurrent>("/api/codex/current", { signal }),
      api.get<AutoReviewMetrics>("/api/auto-review/metrics", { signal }),
    ]);
    return {
      current: current.status === "fulfilled" ? current.value : null,
      metrics: metrics.status === "fulfilled" ? metrics.value : null,
    };
  }, [api]);

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

    const pendingReview = Number(resource.data?.current?.pending_review_count ?? 0);
    if (pendingReview > 0) {
      result.push({
        id: "memory-review",
        title: `${pendingReview} 条候选记忆等待确认`,
        detail: "只有主人能够批准、编辑或拒绝长期记忆。",
        target: "memory_review",
        severity: "warning",
      });
    }

    const ownerReview = Number(resource.data?.metrics?.actions.requires_owner_review ?? 0);
    const blocked = Number(resource.data?.metrics?.actions.blocked ?? 0);
    if (ownerReview > 0 || blocked > 0) {
      result.push({
        id: "shadow-review",
        title: `${ownerReview} 条 SHADOW 建议需要查看`,
        detail: blocked > 0 ? `其中 ${blocked} 条被安全规则阻止，系统没有执行任何记忆变更。` : "系统只记录建议，没有执行变更。",
        target: "auto_review",
        severity: blocked > 0 ? "error" : "warning",
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

  return (
    <div className="stack observation-page">
      <section className={items.length ? "attention-hero attention-hero-warning" : "attention-hero attention-hero-clear"}>
        <div>
          <span className="desktop-eyebrow">OWNER ATTENTION</span>
          <h2>{items.length ? `${items.length} 项需要你处理` : "暂时不需要你处理"}</h2>
          <p>{items.length ? "这里只显示系统不能自行决定的事项。" : "后台任务、重试、索引更新和状态同步会继续自动运行。"}</p>
        </div>
        <div className="observation-live-state">
          <span className={items.length ? "status-dot" : "status-dot online"} />
          <div>
            <strong>{resource.refreshing ? "正在检查" : "自动检查中"}</strong>
            <small>每 8 秒更新</small>
          </div>
        </div>
      </section>

      {resource.error && <Notice kind="warning">部分待办来源暂不可用，系统会继续自动重试。</Notice>}

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
      ) : (
        <section className="observation-empty-state observation-empty-large">
          <strong>系统会自己继续工作</strong>
          <p>没有记忆审核、失败任务、索引冲突、空间告警或其他必须由主人决定的事项。</p>
        </section>
      )}
    </div>
  );
}
