import { useCallback, useMemo } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import type { CodexCurrent } from "./codexWorkspaceTypes";

type AssistantHubSnapshot = {
  import_plan?: {
    sources?: Array<{
      id: string;
      label: string;
      candidates?: Array<{ candidate_id: string; display_name?: string }>;
    }>;
  };
};

type AttentionSnapshot = {
  current: CodexCurrent;
  assistants: AssistantHubSnapshot;
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
    const [current, assistants] = await Promise.all([
      api.get<CodexCurrent>("/api/codex/current", { signal }),
      api.get<AssistantHubSnapshot>("/api/assistant-hub/status", { signal }),
    ]);
    return { current, assistants };
  }, [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 25_000,
    pauseWhenHidden: true,
  });

  const decisionItems = useMemo<AttentionItem[]>(() => {
    const result: AttentionItem[] = [];
    const data = (overview ?? {}) as Record<string, unknown>;
    const memoryRuntime = (data.memory_runtime ?? {}) as Record<string, unknown>;
    const vector = (memoryRuntime.vector ?? data.vector_status ?? {}) as Record<string, unknown>;

    const pendingReview = resource.data
      ? Number(resource.data.current.pending_review_count ?? 0)
      : null;
    if (pendingReview !== null && pendingReview > 0) {
      result.push({
        id: "memory-review",
        title: `${pendingReview} 条候选记忆等待确认`,
        detail: "永久记忆会影响未来回答，只有你能够批准、编辑或拒绝。",
        target: "memory_review",
        severity: "warning",
      });
    }

    const importSources = resource.data?.assistants.import_plan?.sources ?? [];
    const pendingImports = importSources.filter((source) => (source.candidates?.length ?? 0) > 0);
    if (pendingImports.length > 0) {
      result.push({
        id: "assistant-import-authorization",
        title: `${pendingImports.length} 类 AI 历史资料等待读取授权`,
        detail: `${pendingImports.map((source) => source.label).join("、")} 已被发现，但灵机目前只看了文件元数据。回到首页确认后才会读取正文。`,
        target: "overview",
        severity: "warning",
      });
    }

    if (vector.rebuild_required === true) {
      result.push({
        id: "vector-rebuild",
        title: "是否重建向量索引需要确认",
        detail: "系统检测到索引或维度不一致。删除并重建 Collection 属于不可逆维护，灵机不会擅自执行。",
        target: "vector_center",
        severity: "warning",
      });
    }

    return result;
  }, [overview, resource.data]);

  const systemIssues = useMemo<AttentionItem[]>(() => {
    const result: AttentionItem[] = [];
    const data = (overview ?? {}) as Record<string, unknown>;
    const health = (data.health ?? {}) as Record<string, unknown>;
    const queue = ((data.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
    const storageRoot = (data.storage ?? {}) as Record<string, unknown>;
    const storageAlerts = (storageRoot.alerts ?? {}) as Record<string, unknown>;

    const failedJobs = Number(queue.failed ?? 0);
    if (failedJobs > 0) {
      result.push({
        id: "failed-jobs",
        title: `${failedJobs} 个任务已结束自动重试`,
        detail: "错误详情已保留。灵机不会把失败任务伪装成需要你做技术判断；需要时可查看输入或错误原因。",
        target: "jobs",
        severity: "error",
      });
    }

    const errorCount = Number(health.error_count ?? 0);
    if (errorCount > 0) {
      result.push({
        id: "health-errors",
        title: `${errorCount} 个系统错误正在诊断`,
        detail: "后台会继续尝试恢复并保留日志。只有持续无法恢复时才需要进入高级工具。",
        target: "diagnostics",
        severity: "error",
      });
    }

    if (storageAlerts.below_minimum_free === true) {
      result.push({
        id: "low-disk",
        title: "磁盘剩余空间不足",
        detail: "灵机不会为了腾空间自动删除主人资料。可先查看存储占用和安全清理建议。",
        target: "storage",
        severity: "error",
      });
    }

    return result;
  }, [overview]);

  if (!active) return <Empty text="灵机核心连接后会自动汇总真正需要你决定的事项。" />;
  if (resource.loading && !resource.data) return <Empty text="正在检查是否有事项必须由你决定…" />;

  const attentionUnknown = Boolean(resource.error && !resource.data);
  const hasDecisions = decisionItems.length > 0;
  const heroClass = hasDecisions || attentionUnknown
    ? "attention-hero attention-hero-warning"
    : "attention-hero attention-hero-clear";
  const heroTitle = attentionUnknown
    ? "部分决策状态暂时未知"
    : hasDecisions
      ? `${decisionItems.length} 项需要你决定`
      : "暂时不需要你决定";
  const heroDetail = attentionUnknown
    ? "授权和记忆审核状态读取失败，系统正在自动重试；不会把未知状态显示成一切正常。"
    : hasDecisions
      ? "这里只统计权限、永久记忆和不可逆维护。普通故障、重试和诊断不再混进你的决策数量。"
      : systemIssues.length > 0
        ? `当前没有权限或不可逆决策；另有 ${systemIssues.length} 类系统异常已单独整理，灵机会先自行处理。`
        : "后台任务、扫描、重试、索引更新和状态同步会继续自动运行。";

  return (
    <div className="stack observation-page">
      <section className={heroClass}>
        <div>
          <span className="desktop-eyebrow">需要你决定</span>
          <h2>{heroTitle}</h2>
          <p>{heroDetail}</p>
        </div>
        <div className="observation-live-state">
          <span className={!hasDecisions && !attentionUnknown ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{resource.refreshing ? "正在检查" : attentionUnknown ? "等待恢复" : "自动检查中"}</strong>
            <small>每 8 秒更新</small>
          </div>
        </div>
      </section>

      {resource.error && <Notice kind="warning">部分决策来源暂不可用，最近一次有效结果会被保留，系统将自动重试。</Notice>}

      {decisionItems.length ? (
        <div className="attention-list">
          {decisionItems.map((item) => (
            <article className={`attention-card attention-card-${item.severity}`} key={item.id}>
              <div>
                <span className="pill warning">需要确认</span>
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
              </div>
              <button className="button secondary" onClick={() => onNavigate(item.target)}>处理这一项</button>
            </article>
          ))}
        </div>
      ) : attentionUnknown ? (
        <section className="observation-empty-state observation-empty-large">
          <strong>无法确认全部授权和记忆审核状态</strong>
          <p>系统正在重试，恢复后会自动更新。</p>
        </section>
      ) : (
        <section className="observation-empty-state observation-empty-large">
          <strong>你现在不用做任何决定</strong>
          <p>灵机会继续自己工作；只有真正跨过权限或不可逆边界时才会回来找你。</p>
        </section>
      )}

      {systemIssues.length > 0 && (
        <details className="attention-system-details">
          <summary>系统异常与自动处理 · {systemIssues.length}</summary>
          <div className="attention-system-list">
            {systemIssues.map((item) => (
              <article className="attention-system-card" key={item.id}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                </div>
                <button className="text-button" onClick={() => onNavigate(item.target)}>查看详情</button>
              </article>
            ))}
          </div>
        </details>
      )}

      <Notice>
        SHADOW 决策仍是审计历史，不会冒充当前待办。真正需要你确认的事项必须有明确的当前状态和可执行入口。
      </Notice>
    </div>
  );
}
