import { useCallback } from "react";
import { Metric, Notice } from "./ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";

type InspectorSnapshot = {
  workspace?: string | null;
  memory?: Record<string, unknown>;
  vector?: Record<string, unknown>;
  sources?: Record<string, unknown>;
};

type AssistantScanSnapshot = {
  workspace?: string;
  summary?: {
    detected?: number;
    import_ready?: number;
    requires_manual_export?: number;
  };
};

type ConnectorSnapshot = {
  connectors?: Array<{
    configuration_state?: string;
    live_test?: boolean | null;
  }>;
};

type CodexCurrentSnapshot = { pending_review_count?: number };

type ObsidianSnapshot = {
  vault_name?: string | null;
  vault_configured?: boolean;
  vault_path_display?: string | null;
};

type Snapshot = {
  inspector: InspectorSnapshot | null;
  assistants: AssistantScanSnapshot | null;
  connectors: ConnectorSnapshot | null;
  codex: CodexCurrentSnapshot | null;
  obsidian: ObsidianSnapshot | null;
  unavailableCount: number;
};

type Recommendation = {
  title: string;
  detail: string;
  label: string;
  page: PageId;
  requiresOwner: boolean;
};

const display = (value: unknown): string =>
  value === null || value === undefined || value === "" ? "未知" : String(value);

const numberValue = (value: unknown): number | null => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const fulfilled = <T,>(result: PromiseSettledResult<T>): T | null =>
  result.status === "fulfilled" ? result.value : null;

const stateTone = (value: unknown): "good" | "warn" | "bad" | undefined => {
  const state = String(value ?? "").toLowerCase();
  if (["healthy", "ready", "available", "ok", "connected", "configured", "completed"].includes(state)) return "good";
  if (["degraded", "warning", "busy", "configuration_required", "stale", "unavailable", "queued", "running", "retrying"].includes(state)) return "warn";
  if (["failed", "error", "blocked"].includes(state)) return "bad";
  return undefined;
};

const stateLabel = (value: unknown): string => {
  const state = String(value ?? "unknown").toLowerCase();
  return ({
    healthy: "运行正常",
    ready: "已就绪",
    available: "可用",
    configured: "已配置",
    connected: "已连接",
    completed: "已完成",
    queued: "等待处理",
    running: "处理中",
    retrying: "正在重试",
    degraded: "部分能力待处理",
    warning: "需要关注",
    stale: "数据过期",
    failed: "处理失败",
    error: "存在错误",
    unavailable: "暂不可用",
    blocked: "已阻止",
    configuration_required: "需要配置",
  } as Record<string, string>)[state] ?? display(value);
};

const workspaceCopy = (workspace: string | null) => {
  if (workspace === "production") {
    return { label: "正式空间", detail: "灵机正在维护你的正式记忆与知识工作区", tone: "ok" };
  }
  if (workspace === "acceptance") {
    return { label: "验收空间", detail: "与正式数据物理隔离，仅用于测试", tone: "warning" };
  }
  return { label: "工作空间未知", detail: "灵机不会把未知状态冒充为正常", tone: "warning" };
};

function chooseRecommendation(values: {
  unavailableCount: number;
  vaultConfigured: boolean | null;
  configuredClients: number;
  runningJobs: number;
  pendingReview: number;
  vectorState: string;
  embeddingState: string;
}): Recommendation {
  if (values.unavailableCount >= 4) {
    return {
      title: "灵机正在恢复状态来源",
      detail: "多个只读状态来源暂不可用。后台会继续重试，你可以查看诊断过程和失败原因。",
      label: "查看自动诊断",
      page: "diagnostics",
      requiresOwner: false,
    };
  }
  if (values.pendingReview > 0) {
    return {
      title: "有候选记忆等待主人定稿",
      detail: `灵机已完成提取和整理，当前有 ${values.pendingReview} 条候选等待批准或拒绝。`,
      label: "处理待批准候选",
      page: "memory_review",
      requiresOwner: true,
    };
  }
  if (values.vaultConfigured === false) {
    return {
      title: "已发现知识库配置缺口",
      detail: "灵机可以继续运行和扫描；连接正式 Vault 涉及读取真实正文，因此等待主人授权。",
      label: "查看待授权知识库",
      page: "obsidian",
      requiresOwner: true,
    };
  }
  if (values.configuredClients === 0) {
    return {
      title: "灵机正在检查 AI 客户端连接",
      detail: "安装和目录元数据会自动扫描；真正修改客户端配置前才会请求主人确认。",
      label: "查看 AI 连接进度",
      page: "assistant_hub",
      requiresOwner: false,
    };
  }
  if (values.runningJobs > 0) {
    return {
      title: "灵机正在处理导入任务",
      detail: `当前有 ${values.runningJobs} 个任务运行、排队或重试，后台会继续推进。`,
      label: "查看自动处理进度",
      page: "activity",
      requiresOwner: false,
    };
  }
  if (
    !["healthy", "ready", "available"].includes(values.vectorState)
    || !["healthy", "ready", "available"].includes(values.embeddingState)
  ) {
    return {
      title: "灵机正在诊断语义检索",
      detail: "全文检索继续可用；后台会持续检查模型、Qdrant、索引和重建条件。",
      label: "查看修复进度",
      page: "vector_center",
      requiresOwner: false,
    };
  }
  return {
    title: "灵机运行正常，当前没有阻塞",
    detail: "自动扫描、状态刷新、任务维护和故障恢复正在后台运行。",
    label: "查看运行记录",
    page: "activity",
    requiresOwner: false,
  };
}

const jobLabel = (job: Record<string, unknown>): string =>
  String(job.title ?? job.source_type ?? job.adapter_name ?? job.job_id ?? "导入任务");

export default function StartCenterPanel({
  api,
  active,
  overview,
  onNavigate,
}: {
  api: LingJiApi;
  active: boolean;
  overview: Row;
  onNavigate: (page: PageId) => void;
}) {
  const load = useCallback(async (signal: AbortSignal): Promise<Snapshot> => {
    const results = await Promise.allSettled([
      api.get<InspectorSnapshot>("/api/memory/inspector/status", { signal }),
      api.get<AssistantScanSnapshot>("/api/assistant-hub/status", { signal }),
      api.get<ConnectorSnapshot>("/api/assistant-hub/connections", { signal }),
      api.get<CodexCurrentSnapshot>("/api/codex/current", { signal }),
      api.get<ObsidianSnapshot>("/api/obsidian/status", { signal }),
    ]);
    return {
      inspector: fulfilled(results[0] as PromiseSettledResult<InspectorSnapshot>),
      assistants: fulfilled(results[1] as PromiseSettledResult<AssistantScanSnapshot>),
      connectors: fulfilled(results[2] as PromiseSettledResult<ConnectorSnapshot>),
      codex: fulfilled(results[3] as PromiseSettledResult<CodexCurrentSnapshot>),
      obsidian: fulfilled(results[4] as PromiseSettledResult<ObsidianSnapshot>),
      unavailableCount: results.filter((result) => result.status === "rejected").length,
    };
  }, [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 10_000,
    staleAfterMs: 30_000,
    pauseWhenHidden: true,
  });

  const data = overview as Record<string, unknown>;
  const queueRoot = (data.queue ?? {}) as Record<string, unknown>;
  const queue = (queueRoot.stats ?? {}) as Record<string, unknown>;
  const recentJobs = Array.isArray(queueRoot.recent)
    ? (queueRoot.recent as Array<Record<string, unknown>>)
    : [];
  const importJobs = recentJobs
    .filter((job) => /chatgpt|codex|assistant_hub|import/i.test(JSON.stringify(job)))
    .slice(0, 3);
  const memoryRuntime = (data.memory_runtime ?? {}) as Record<string, unknown>;
  const fallbackMemory = (memoryRuntime.memory ?? data.memory_stats ?? {}) as Record<string, unknown>;
  const fallbackVector = (memoryRuntime.vector ?? data.vector_status ?? {}) as Record<string, unknown>;
  const embedding = (memoryRuntime.embedding ?? data.embedding_status ?? {}) as Record<string, unknown>;

  const snapshot = resource.data;
  const memory = (snapshot?.inspector?.memory ?? fallbackMemory) as Record<string, unknown>;
  const vector = (snapshot?.inspector?.vector ?? fallbackVector) as Record<string, unknown>;
  const sources = (snapshot?.inspector?.sources ?? {}) as Record<string, unknown>;
  const workspace = String(
    snapshot?.inspector?.workspace
    ?? snapshot?.assistants?.workspace
    ?? memoryRuntime.workspace
    ?? "",
  ).toLowerCase() || null;
  const workspaceInfo = workspaceCopy(workspace);

  const connectors = snapshot?.connectors?.connectors ?? [];
  const configuredClients = connectors.filter((item) => item.configuration_state === "configured").length;
  const verifiedClients = connectors.filter((item) => item.live_test === true).length;
  const detectedAssistants = numberValue(snapshot?.assistants?.summary?.detected) ?? 0;
  const importReady = (numberValue(snapshot?.assistants?.summary?.import_ready) ?? 0)
    + (numberValue(snapshot?.assistants?.summary?.requires_manual_export) ?? 0);
  const pendingReview = numberValue(snapshot?.codex?.pending_review_count) ?? 0;
  const vaultConfigured = snapshot?.obsidian ? Boolean(snapshot.obsidian.vault_configured) : null;
  const runningJobs = (numberValue(queue.running) ?? 0)
    + (numberValue(queue.pending) ?? 0)
    + (numberValue(queue.retrying) ?? 0);
  const embeddingReady = ["healthy", "ready", "available"].includes(
    String(embedding.state ?? "").toLowerCase(),
  );

  const recommendation = chooseRecommendation({
    unavailableCount: snapshot?.unavailableCount ?? 0,
    vaultConfigured,
    configuredClients,
    runningJobs,
    pendingReview,
    vectorState: String(vector.state ?? "unknown").toLowerCase(),
    embeddingState: String(embedding.state ?? "unknown").toLowerCase(),
  });

  return (
    <>
      {(resource.error || resource.stale || (snapshot?.unavailableCount ?? 0) > 0) && (
        <Notice kind="warning">
          部分观察数据暂不可用或来自旧快照。灵机会继续重试，不会把未知状态显示成一切正常。
        </Notice>
      )}

      <section className="start-center-recommendation">
        <div>
          <span className="desktop-eyebrow">灵机当前处理重点</span>
          <h3>{recommendation.title}</h3>
          <p>{recommendation.detail}</p>
          <small>{recommendation.requiresOwner ? "此步骤涉及授权或永久记忆，需要主人确认。" : "这是查看入口，不影响后台继续运行。"}</small>
        </div>
        <button className={recommendation.requiresOwner ? "button primary" : "button secondary"} onClick={() => onNavigate(recommendation.page)}>
          {recommendation.label}
        </button>
      </section>

      <section className="start-center-section">
        <div className="overview-section-heading">
          <div>
            <span className="desktop-eyebrow">当前工作空间</span>
            <h3>{workspaceInfo.label}</h3>
          </div>
          <span className={`pill ${workspaceInfo.tone}`}>{workspaceInfo.detail}</span>
        </div>
        <div className="start-center-memory-grid" aria-label="全量记忆总览">
          <Metric
            title="正式 Vault"
            value={snapshot?.obsidian?.vault_name || (vaultConfigured ? "已连接" : vaultConfigured === false ? "等待授权" : "未知")}
            detail={snapshot?.obsidian?.vault_path_display || "Obsidian Vault + Git 是永久知识权威"}
            tone={vaultConfigured === true ? "good" : vaultConfigured === false ? "warn" : undefined}
          />
          <Metric title="来源" value={display(sources.sources)} detail="自动识别的导入或采集来源" />
          <Metric title="对话" value={display(sources.conversations)} detail="结构化会话记录" />
          <Metric title="消息" value={display(sources.messages)} detail="可追溯消息记录" />
          <Metric title="永久知识" value={display(memory.documents)} detail="Vault 中已建立索引的文档" />
          <Metric title="核心记忆" value={display(memory.core_memories)} detail="主人批准的长期事实" />
          <Metric
            title="向量索引"
            value={display(vector.vectors)}
            detail={`${stateLabel(vector.state)} · 维度 ${display(vector.dimension)}`}
            tone={vector.rebuild_required ? "bad" : stateTone(vector.state)}
          />
        </div>
      </section>

      <section className="start-center-section">
        <div className="overview-section-heading">
          <div><span className="desktop-eyebrow">灵机自动发现</span><h3>来源与 AI 客户端摘要</h3></div>
          <button className="button secondary" onClick={() => onNavigate("assistant_hub")}>
            查看连接与授权
          </button>
        </div>
        <div className="start-center-connection-grid">
          <Metric title="检测到 AI" value={display(detectedAssistants)} detail="自动只读扫描，不读取对话正文" />
          <Metric title="等待授权来源" value={display(importReady)} detail="发现后停在读取正文之前" />
          <Metric title="已配置客户端" value={display(configuredClients)} detail="LingJi 管理或确认的连接" />
          <Metric
            title="真实连接通过"
            value={display(verifiedClients)}
            detail="客户端真实调用已验证"
            tone={verifiedClients > 0 ? "good" : undefined}
          />
        </div>
      </section>

      <section className="start-center-section">
        <div className="overview-section-heading">
          <div><span className="desktop-eyebrow">自动处理记录</span><h3>最近提交到灵机的历史资料</h3></div>
          <button className="button secondary" onClick={() => onNavigate("activity")}>查看全部进度</button>
        </div>
        {importJobs.length ? (
          <div className="start-center-recent-list">
            {importJobs.map((job, index) => {
              const tone = stateTone(job.status);
              return (
                <article key={String(job.job_id ?? index)}>
                  <div>
                    <strong>{jobLabel(job)}</strong>
                    <small>{display(job.created_at ?? job.updated_at ?? job.started_at)}</small>
                  </div>
                  <span className={`pill ${tone === "bad" ? "error" : tone === "good" ? "ok" : "warning"}`}>
                    {stateLabel(job.status)}
                  </span>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="observation-empty-state">
            <strong>当前没有导入任务</strong>
            <p>灵机会继续自动扫描来源元数据；发现可读取资料后，会在真正打开正文前请求授权。</p>
          </div>
        )}
      </section>

      <section className="start-center-section">
        <div className="overview-section-heading">
          <div><span className="desktop-eyebrow">系统与已知问题</span><h3>自动维护状态</h3></div>
          <small>只展示有验收证据或实时状态支持的结论</small>
        </div>
        <div className="start-center-issue-grid">
          <KnownIssue title="PowerShell、CMD 与黑窗口">安装版使用 Windows GUI 子系统和隐藏子进程。</KnownIssue>
          <KnownIssue title="Runtime 与 Windows 重启恢复">打包 Runtime 生命周期和自动恢复已有验收记录。</KnownIssue>
          <KnownIssue title="非 C 盘 DataRoot 隔离">Desktop会核验Runtime实际根，不接管身份不一致的外部进程。</KnownIssue>
          <KnownIssue title="覆盖安装与卸载数据保护">安装目录与主人数据分离，不清理正式数据。</KnownIssue>
          <article className={`start-center-issue ${embeddingReady ? "start-center-issue-fixed" : "start-center-issue-open"}`}>
            <span className={`pill ${embeddingReady ? "ok" : "warning"}`}>{embeddingReady ? "当前正常" : "后台诊断中"}</span>
            <strong>Embedding 与语义检索</strong>
            <p>{embeddingReady
              ? "Embedding 已激活，语义检索状态由后端确认。"
              : "灵机已识别语义检索阻塞；向量中心会显示配置模型、实际模型、Qdrant状态、最近错误和修复进度。全文检索继续可用。"}</p>
          </article>
        </div>
      </section>
    </>
  );
}

function KnownIssue({ title, children }: { title: string; children: string }) {
  return (
    <article className="start-center-issue start-center-issue-fixed">
      <span className="pill ok">自动维护</span>
      <strong>{title}</strong>
      <p>{children}</p>
    </article>
  );
}
