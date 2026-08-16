import { useCallback, useMemo, useState } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";

type ReviewCandidate = {
  memory_id: string;
  title?: string | null;
  content_preview?: string | null;
  proposal_reason?: string | null;
  confidence?: number | null;
  created_at?: string | null;
};

type ReviewResponse = { items?: ReviewCandidate[]; pagination?: { total?: number | null; has_more?: boolean } };

type ImportCandidate = {
  candidate_id: string;
  display_name?: string | null;
  size_bytes?: number | null;
};

type ImportSource = {
  id: string;
  label: string;
  candidates?: ImportCandidate[];
};

type AssistantHub = { import_plan?: { sources?: ImportSource[] } };

type AttentionSnapshot = { reviews: ReviewResponse | null; assistants: AssistantHub | null };

type OwnerItem =
  | { kind: "memory"; id: string; title: string; detail: string; candidate: ReviewCandidate }
  | { kind: "import"; id: string; title: string; detail: string; source: ImportSource; candidate: ImportCandidate }
  | { kind: "vector"; id: string; title: string; detail: string };

function settledValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

function confidence(value: unknown): string {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "未量化";
}

function fileSize(value: unknown): string {
  const bytes = Number(value ?? 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return "大小未知";
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
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

  const ownerItems = useMemo<OwnerItem[]>(() => {
    const result: OwnerItem[] = [];
    for (const candidate of resource.data?.reviews?.items ?? []) {
      result.push({
        kind: "memory",
        id: `memory:${candidate.memory_id}`,
        title: candidate.title || "候选记忆等待确认",
        detail: candidate.proposal_reason || candidate.content_preview || "只有你确认后，它才会进入永久记忆。",
        candidate,
      });
    }
    for (const source of resource.data?.assistants?.import_plan?.sources ?? []) {
      for (const candidate of source.candidates ?? []) {
        result.push({
          kind: "import",
          id: `import:${candidate.candidate_id}`,
          title: `允许读取 ${source.label} · ${candidate.display_name || "新资料"}`,
          detail: `已发现文件元数据 · ${fileSize(candidate.size_bytes)}。读取正文会跨过隐私边界，所以停下来等你。`,
          source,
          candidate,
        });
      }
    }
    if (vector.rebuild_required === true) {
      result.push({ kind: "vector", id: "vector-rebuild", title: "确认是否重建向量索引", detail: "索引重建属于不可逆维护，灵机不会自动删除并重建 Collection。" });
    }
    return result;
  }, [resource.data, vector.rebuild_required]);

  const sourceUnknown = resource.data?.reviews === null || resource.data?.assistants === null;
  const queue = ((data.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const health = (data.health ?? {}) as Record<string, unknown>;
  const autoHandled = [
    Number(queue.failed ?? 0) > 0 ? `${Number(queue.failed)} 个任务已结束自动重试，原因已保留` : "",
    Number(health.error_count ?? 0) > 0 ? `${Number(health.error_count)} 类运行异常正在后台诊断` : "",
  ].filter(Boolean);

  async function authorizeImport(item: Extract<OwnerItem, { kind: "import" }>) {
    if (busy) return;
    setBusy(item.id);
    setMessage("");
    try {
      const response = await api.post<{ duplicate?: boolean; job_id?: string }>(
        `/api/assistant-hub/import-candidates/${encodeURIComponent(item.candidate.candidate_id)}/authorize`,
        { confirmation: `AUTHORIZE_ASSISTANT_IMPORT_${item.candidate.candidate_id.toUpperCase()}` },
      );
      setMessage(response.duplicate ? "这份资料之前已经授权和处理过，没有重复创建任务。" : "已授权读取。后续排队、去重和整理交给灵机自动完成。");
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
      <section className={`v4-page-intro attention-intro ${ownerItems.length ? "needs-owner" : sourceUnknown ? "unknown" : "clear"}`}>
        <div>
          <span className="v4-kicker">需要我</span>
          <h2>{ownerItems.length ? `${ownerItems.length} 件事必须由你决定` : sourceUnknown ? "部分主人边界状态还没确认" : "现在没有任何事需要你"}</h2>
          <p>{ownerItems.length ? "这里不显示普通故障、重试或技术告警。每个按钮背后都有一个真实对象。" : sourceUnknown ? "系统正在自动重试读取待办来源；未知状态不会被算成“零待办”。" : "扫描、整理、去重、索引和可恢复错误继续由灵机自己处理。"}</p>
        </div>
        <div className="attention-owner-count"><strong>{ownerItems.length}</strong><span>真实待办</span></div>
      </section>

      {message && <Notice kind={message.includes("没有成功") ? "warning" : "info"}>{message}</Notice>}
      {resource.error && <Notice kind="warning">待办来源的最近一次刷新出现问题，灵机正在自动重试。</Notice>}

      {ownerItems.length ? (
        <section className="attention-object-list">
          {ownerItems.map((item) => (
            <article className="attention-object-card" key={item.id}>
              <div className="attention-object-kind">{item.kind === "memory" ? "永久记忆" : item.kind === "import" ? "读取授权" : "不可逆维护"}</div>
              <div className="attention-object-copy"><h3>{item.title}</h3><p>{item.detail}</p>
                {item.kind === "memory" && <small>对象：{item.candidate.memory_id} · 置信度 {confidence(item.candidate.confidence)}</small>}
                {item.kind === "import" && <small>对象：{item.candidate.candidate_id} · 来源 {item.source.label}</small>}
              </div>
              <div className="attention-object-action">
                {item.kind === "memory" && <button className="v4-button primary" onClick={() => onOpenReview(item.candidate.memory_id)}>审核这条记忆</button>}
                {item.kind === "import" && <button className="v4-button primary" disabled={Boolean(busy)} onClick={() => void authorizeImport(item)}>{busy === item.id ? "授权中…" : "允许读取"}</button>}
                {item.kind === "vector" && <button className="v4-button" onClick={() => onNavigate("vector_center")}>查看重建说明</button>}
              </div>
            </article>
          ))}
        </section>
      ) : sourceUnknown ? (
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
