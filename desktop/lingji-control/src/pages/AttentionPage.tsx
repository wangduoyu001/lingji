import { useCallback, useMemo, useState } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import {
  buildOwnerAttentionItems,
  ownerAttentionSummary,
  ownerSourcesUnknown,
  type AssistantHub,
  type ImportAttentionItem,
  type ReviewResponse,
} from "../ownerWorkbenchModel";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import type { CaptureSubmissionResponse } from "./captureCenterTypes";

type AttentionSnapshot = { reviews: ReviewResponse | null; assistants: AssistantHub | null };

function settledValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

function confidence(value: unknown): string {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "未量化";
}

function authorizationMessage(response: CaptureSubmissionResponse): string {
  const captureId = response.capture_id?.trim();
  const jobId = response.job_id?.trim();
  if (response.duplicate) {
    return captureId
      ? `这份资料之前已经授权并进入同一工作链。资料 ${captureId}${jobId ? ` · 工作 ${jobId}` : ""}，没有重复创建。`
      : "这份资料之前已经授权和处理过，没有重复创建任务。";
  }
  if (captureId && jobId) return `已授权读取。资料 ${captureId} · 工作 ${jobId} 已进入自动处理队列。`;
  if (captureId) return `已授权读取。资料 ${captureId} 已创建，但尚未拿到可追踪 WorkItem，界面不会宣称已经处理。`;
  return "授权请求已接受，但没有返回可追踪资料编号；界面不会宣称已经处理。";
}

export default function AttentionPage({
  api,
  active,
  overview,
  onNavigate,
  onOpenReview,
}: {
  api: LingJiApi;
  active: boolean;
  overview: Row | null;
  onNavigate: (page: PageId) => void;
  onOpenReview: (memoryId: string) => void;
}) {
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async (signal: AbortSignal): Promise<AttentionSnapshot> => {
    const results = await Promise.allSettled([
      api.get<ReviewResponse>("/api/memory/review/candidates?limit=30&offset=0", { signal }),
      api.get<AssistantHub>("/api/assistant-hub/status", { signal }),
    ]);
    return { reviews: settledValue(results[0]), assistants: settledValue(results[1]) };
  }, [api]);

  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 8_000, staleAfterMs: 24_000, pauseWhenHidden: true });

  const data = (overview ?? {}) as Record<string, unknown>;
  const memoryRuntime = (data.memory_runtime ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? data.vector_status ?? {}) as Record<string, unknown>;
  const reviewItems = resource.data?.reviews?.items ?? [];
  const importSources = resource.data?.assistants?.import_plan?.sources ?? [];
  const sourceUnknown = ownerSourcesUnknown({
    reviewsLoaded: resource.data?.reviews !== null,
    assistantsLoaded: resource.data?.assistants !== null,
  });
  const ownerItems = useMemo(
    () => buildOwnerAttentionItems({
      reviewItems,
      importSources,
      vectorRebuildRequired: vector.rebuild_required === true,
    }),
    [importSources, reviewItems, vector.rebuild_required],
  );
  const attention = ownerAttentionSummary({ items: ownerItems, sourceUnknown, activeWorkCount: 0 });

  const queue = ((data.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const health = (data.health ?? {}) as Record<string, unknown>;
  const autoHandled = [
    Number(queue.failed ?? 0) > 0 ? `${Number(queue.failed)} 个任务已结束自动重试，原因已保留` : "",
    Number(health.error_count ?? 0) > 0 ? `${Number(health.error_count)} 类运行异常正在后台诊断` : "",
  ].filter(Boolean);

  async function authorizeImport(item: ImportAttentionItem) {
    if (busy) return;
    setBusy(item.id);
    setMessage("");
    try {
      const response = await api.post<CaptureSubmissionResponse>(
        `/api/assistant-hub/import-candidates/${encodeURIComponent(item.candidateId)}/authorize`,
        { confirmation: `AUTHORIZE_ASSISTANT_IMPORT_${item.candidateId.toUpperCase()}` },
      );
      setMessage(authorizationMessage(response));
      await resource.refresh();
    } catch {
      setMessage("这次授权没有成功，系统没有读取正文，也没有假装已经处理。");
    } finally {
      setBusy("");
    }
  }

  if (!active) return <Empty text="灵机核心连接后，只会在真正需要你的地方出现在这里。" />;
  if (resource.loading && !resource.data) return <Empty text="正在确认是否有真实事项需要你…" />;

  return (
    <div className="workbench-v4 attention-v4">
      <section className={`v4-page-intro attention-intro ${attention.state === "owner" ? "needs-owner" : attention.state === "unknown" ? "unknown" : "clear"}`}>
        <div>
          <span className="v4-kicker">需要我</span>
          <h2>{attention.title}</h2>
          <p>{ownerItems.length ? "这里不显示普通故障、重试或技术告警。每个按钮背后都有一个真实对象。" : attention.detail}</p>
        </div>
        <div className="attention-owner-count"><strong>{ownerItems.length}</strong><span>真实待办</span></div>
      </section>

      {message && <Notice kind={message.includes("没有成功") || message.includes("没有返回") || message.includes("尚未拿到") ? "warning" : "info"}>{message}</Notice>}
      {resource.error && <Notice kind="warning">待办来源的最近一次刷新出现问题，灵机正在自动重试。</Notice>}

      {ownerItems.length ? (
        <section className="attention-object-list">
          {ownerItems.map((item) => (
            <article className="attention-object-card" key={item.id}>
              <div className="attention-object-kind">{item.kind === "memory" ? "永久记忆" : item.kind === "import" ? "读取授权" : "不可逆维护"}</div>
              <div className="attention-object-copy"><h3>{item.title}</h3><p>{item.detail}</p>
                {item.kind === "memory" && <small>对象：{item.objectId} · 置信度 {confidence(item.candidate.confidence)}</small>}
                {item.kind === "import" && <small>对象：{item.objectId} · 来源 {item.source.label}</small>}
              </div>
              <div className="attention-object-action">
                {item.kind === "memory" && <button className="v4-button primary" onClick={() => onOpenReview(item.memoryId)}>审核这条记忆</button>}
                {item.kind === "import" && <button className="v4-button primary" disabled={Boolean(busy)} onClick={() => void authorizeImport(item)}>{busy === item.id ? "授权中…" : "允许读取"}</button>}
                {item.kind === "vector" && <button className="v4-button" onClick={() => onNavigate(item.target)}>查看重建说明</button>}
              </div>
            </article>
          ))}
        </section>
      ) : attention.state === "unknown" ? (
        <div className="v4-empty-state large"><strong>还不能确认全部待办来源</strong><p>灵机会继续重试。恢复之前不会给你空按钮，也不会声称“一切正常”。</p></div>
      ) : (
        <div className="v4-empty-state large"><strong>你现在可以不用管灵机</strong><p>只有授权、永久记忆冲突、不可逆操作或真正需要主人判断的事情才会重新出现在这里。</p></div>
      )}

      <section className="attention-policy-strip">
        <div><span className="v4-kicker">灵机自己处理</span><h3>{autoHandled.length ? `${autoHandled.length} 类后台问题没有打扰你` : "当前没有需要升级给你的技术问题"}</h3><p>{autoHandled.join("；") || "可恢复问题会自动重试，可降级能力会优先降级，不把运维工作冒充成主人待办。"}</p></div>
        <button className="v4-link" onClick={() => onNavigate("diagnostics")}>高级诊断</button>
      </section>
    </div>
  );
}
