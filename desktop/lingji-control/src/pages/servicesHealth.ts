import type { LingJiApi } from "../api";

export type ServiceRow = {
  key: string;
  label: string;
  plain: string;
  impact: string;
  fix?: string;
  message?: string;
  status: "ok" | "warning" | "error" | "unknown";
  statusText: string;
};

export type VectorizationPanel = {
  vectorizedMessages: number | null;
  embeddingAvailable: boolean | null;
  ollamaService: ServiceRow | null;
};

const SERVICE_EXPLAIN: Record<string, { label: string; plain: string; impact: string; fix?: string }> = {
  data_root_policy: { label: "数据存放", plain: "灵机的记忆数据保存在你指定的位置，不会偷偷写进系统盘。", impact: "" },
  vault: { label: "长期记忆库", plain: "你确认过的长期记忆会保存成笔记文件，永远归你。", impact: "不可用时无法保存长期记忆。" },
  storage: { label: "原始资料区", plain: "导入的聊天记录原件先存在这里，是记忆的证据底稿。", impact: "不可用时无法导入新内容。" },
  logs: { label: "运行日志", plain: "灵机的工作记录，出问题时用来查找原因。", impact: "" },
  backup: { label: "备份", plain: "重要数据的备份目录。", impact: "" },
  disk: { label: "磁盘空间", plain: "电脑剩余可用空间。", impact: "空间不足时无法继续导入。" },
  state_db: { label: "任务数据库", plain: "记录灵机正在做什么、做到哪一步。", impact: "不可用时自动工作会停止。" },
  memory_db: { label: "检索索引", plain: "让记忆能被快速搜到的索引，可以随时重建。", impact: "不可用时搜索变慢或不可用。" },
  ffmpeg: { label: "媒体处理 ffmpeg", plain: "处理音视频的本地工具，转写视频/语音时要用。", impact: "缺失时视频和语音无法转写成文字记忆。" },
  ffprobe: { label: "媒体探针 ffprobe", plain: "读取音视频信息的本地工具（时长、格式等）。", impact: "缺失时媒体分析能力降级，但不影响聊天记录。" },
  ollama: { label: "本地 AI 服务 Ollama", plain: "在本机运行小型 AI 模型的服务，负责“把文字变成机器能理解的意思”（向量化）。", impact: "没运行时灵机只能按关键词搜索，不能按意思搜索。", fix: "安装并启动 Ollama（免费、数据不出本机），然后在里面拉取一个向量化模型（例如 bge-m3）。灵机会自动检测并开始补算。" },
};

function normalizeStatus(value: unknown): ServiceRow["status"] {
  const s = String(value ?? "").toLowerCase();
  if (["ok", "healthy", "pass", "passed"].includes(s)) return "ok";
  if (["warning", "degraded"].includes(s)) return "warning";
  if (["error", "failed", "unavailable"].includes(s)) return "error";
  return "unknown";
}

const STATUS_TEXT: Record<ServiceRow["status"], string> = {
  ok: "正常",
  warning: "需要留意",
  error: "不可用",
  unknown: "状态尚未获得",
};

export function projectServiceRows(health: Record<string, unknown> | null): ServiceRow[] {
  const checks = Array.isArray(health?.checks) ? (health?.checks as Array<Record<string, unknown>>) : [];
  const rows: ServiceRow[] = [];
  for (const check of checks) {
    const key = String(check.name ?? "");
    const explain = SERVICE_EXPLAIN[key];
    if (!explain) continue;
    const status = normalizeStatus(check.status);
    rows.push({
      key,
      ...explain,
      status,
      statusText: STATUS_TEXT[status],
      message: String(check.message ?? "") || undefined,
    });
  }
  return rows;
}

export function projectVectorization(
  overview: Record<string, unknown> | null,
  health: Record<string, unknown> | null,
): VectorizationPanel {
  const embedding = (overview?.embedding_status ?? {}) as Record<string, unknown>;
  const vector = (overview?.vector_status ?? {}) as Record<string, unknown>;
  const checks = Array.isArray(health?.checks) ? (health?.checks as Array<Record<string, unknown>>) : [];
  const ollamaCheck = checks.find((c) => String(c.name) === "ollama");
  const ollamaStatus = ollamaCheck ? normalizeStatus(ollamaCheck.status) : "unknown";
  const embeddingUnavailable = embedding.available === false || String(embedding.state ?? "") === "configuration_required";
  return {
    vectorizedMessages: typeof vector.vectors === "number" ? vector.vectors : null,
    embeddingAvailable: typeof embedding.available === "boolean" ? embedding.available : null,
    ollamaService: ollamaCheck
      ? {
          key: "ollama",
          ...SERVICE_EXPLAIN.ollama,
          status: ollamaStatus,
          statusText: STATUS_TEXT[ollamaStatus],
        }
      : null,
  };
  void embeddingUnavailable;
}

export type ActionRequiredAlert = {
  key: string;
  title: string;
  body: string;
  actionLabel: string;
  navigateTo: "memory_sources" | "attention" | "overview";
};

export function decideActionRequired(input: {
  sources: Array<{ state?: string; kind?: string; display_name?: string; nextAction?: string }>;
  pendingCount: number | null;
  dismissed: string[];
}): ActionRequiredAlert | null {
  const candidates: ActionRequiredAlert[] = [];
  const needsConsent = input.sources.filter((item) => item.state === "consent_required" || item.state === "detected");
  if (needsConsent.length) {
    const names = needsConsent.map((item) => item.display_name || "来源").join("、");
    candidates.push({
      key: `consent:${needsConsent.map((i) => i.kind).join(",")}`,
      title: "有新的记录来源等待你确认",
      body: `灵机在本机发现了 ${names}。确认后灵机会自动扫描和整理这些记录；不确认也不会读取任何内容。`,
      actionLabel: "去确认",
      navigateTo: "memory_sources",
    });
  }
  if ((input.pendingCount ?? 0) > 0) {
    candidates.push({
      key: "pending",
      title: "有事项需要你决定",
      body: `灵机有 ${input.pendingCount} 件事等你确认（比如某条记忆是否保留）。确认后才会继续。`,
      actionLabel: "去处理",
      navigateTo: "attention",
    });
  }
  return candidates.find((item) => !input.dismissed.includes(item.key)) ?? null;
}

export async function fetchHomePanels(api: Pick<LingJiApi, "get">): Promise<{
  health: Record<string, unknown> | null;
  overview: Record<string, unknown> | null;
  importedMessages: number | null;
}> {
  const [health, overview] = await Promise.all([
    api.get<Record<string, unknown>>("/api/health").catch(() => null),
    api.get<Record<string, unknown>>("/api/overview").catch(() => null),
  ]);
  const stats = (overview?.memory_stats ?? {}) as Record<string, unknown>;
  return {
    health,
    overview,
    importedMessages: typeof stats.documents === "number" ? stats.documents : null,
  };
}
